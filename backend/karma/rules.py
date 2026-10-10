"""Karma scoring, persistence, Redis leaderboards, and live updates."""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from .models import KarmaEvent
from .signals_bus import register_karma_event

logger = logging.getLogger(__name__)


SCORES: dict[str, int] = {
    'item_resolved': 10,
    'peer_help': 4,
    'welcome': 5,
    'clarification_upvoted': 2,
    'mentorship_completed': 12,
    'dm_item_ontime': 6,
}

PEER_HELP_DAILY_LIMIT = 3
KARMA_GLOBAL_KEY = 'karma:global'
KARMA_MONTHLY_KEY_PREFIX = 'karma:monthly:'
KARMA_PENDING_KEY_PREFIX = 'karma:pending:'
KARMA_PUSH_LOCK_PREFIX = 'karma:push-lock:'
KARMA_PUSH_WINDOW_SECONDS = 10


def score_for_event(kind: str) -> int:
    """Return the configured score for an event kind."""

    try:
        return SCORES[kind]
    except KeyError as error:
        raise ValueError(f'Unknown Karma event kind: {kind}') from error


def get_karma_redis() -> redis.Redis:
    """Return the Redis database used for Karma sorted sets."""

    return redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=6379,
        db=0,
        decode_responses=True,
    )


def _monthly_key(at):
    return f'{KARMA_MONTHLY_KEY_PREFIX}{at.strftime("%Y-%m")}'


def _peer_help_is_allowed(user_id: int, metadata: dict[str, Any], at) -> bool:
    """Allow at most three rewards per user/thread/day.

    ``helped_user_id`` is included when available so repeated help between
    the same pair is limited independently from another participant in the
    same thread. Older callers that only provide ``thread_id`` still receive
    the safe per-user/thread limit.
    """

    thread_id = metadata.get('thread_id')
    if not thread_id:
        return True

    start_of_day = at - timedelta(
        hours=at.hour,
        minutes=at.minute,
        seconds=at.second,
        microseconds=at.microsecond,
    )
    events = KarmaEvent.objects.filter(
        user_id=user_id,
        kind='peer_help',
        created_at__gte=start_of_day,
        metadata__thread_id=str(thread_id),
    )
    helped_user_id = metadata.get('helped_user_id')
    if helped_user_id is not None:
        events = events.filter(metadata__helped_user_id=str(helped_user_id))
    return events.count() < PEER_HELP_DAILY_LIMIT


def _as_int(value: Any) -> int:
    return int(float(value or 0))


def _publish_karma_update(
    *,
    user_id: int,
    kind: str,
    delta: int,
    new_total: int,
    monthly_total: int,
    badges_unlocked: list[str],
) -> bool:
    """Publish one coalesced update per user during the push window.

    Scores and audit rows are never throttled. Only live UI messages are
    coalesced in Redis. Events arriving inside the window accumulate in a
    pending counter and are included in the next live update for that user.
    """

    client = get_karma_redis()
    pending_key = f'{KARMA_PENDING_KEY_PREFIX}{user_id}'
    lock_key = f'{KARMA_PUSH_LOCK_PREFIX}{user_id}'
    pending_delta = _as_int(client.incrby(pending_key, delta))
    client.expire(pending_key, KARMA_PUSH_WINDOW_SECONDS * 2)

    if not client.set(lock_key, '1', nx=True, ex=KARMA_PUSH_WINDOW_SECONDS):
        return False

    aggregated_delta = _as_int(client.getdel(pending_key)) or pending_delta
    payload = {
        'kind': 'karma_update',
        'user_id': user_id,
        'delta': aggregated_delta,
        'new_total': new_total,
        'monthly_total': monthly_total,
        'event_kind': kind,
        'badges_unlocked': badges_unlocked,
    }
    try:
        async_to_sync(get_channel_layer().group_send)(
            'online_status',
            {'type': 'relay_event', 'payload': payload},
        )
    except Exception:  # pragma: no cover - channel infrastructure failure
        logger.warning('Unable to publish Karma update.', exc_info=True)
        return False
    return True


def apply_karma(
    *,
    user_id: int,
    kind: str,
    room_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    source_key: str | None = None,
) -> dict[str, Any]:
    """Award Karma, persist an audit row, update Redis, and publish an event."""

    score = score_for_event(kind)
    event_metadata = dict(metadata or {})
    if 'thread_id' in event_metadata and event_metadata['thread_id'] is not None:
        event_metadata['thread_id'] = str(event_metadata['thread_id'])
    if 'helped_user_id' in event_metadata and event_metadata['helped_user_id'] is not None:
        event_metadata['helped_user_id'] = str(event_metadata['helped_user_id'])
    at = timezone.now()

    with transaction.atomic():
        if source_key:
            existing_event = KarmaEvent.objects.filter(source_key=source_key).first()
            if existing_event:
                return {
                    'event_id': str(existing_event.id),
                    'user_id': existing_event.user_id,
                    'kind': existing_event.kind,
                    'delta': 0,
                    'awarded': False,
                    'reason': 'already_awarded',
                }

        if kind == 'peer_help' and not _peer_help_is_allowed(user_id, event_metadata, at):
            return {
                'user_id': user_id,
                'kind': kind,
                'delta': 0,
                'awarded': False,
                'reason': 'daily_limit_reached',
            }

        event = KarmaEvent.objects.create(
            user_id=user_id,
            kind=kind,
            score=score,
            source_key=source_key,
            room_id=room_id,
            metadata=event_metadata,
        )

    client = get_karma_redis()
    monthly_key = _monthly_key(at)
    new_total = _as_int(client.zincrby(KARMA_GLOBAL_KEY, score, str(user_id)))
    monthly_total = _as_int(client.zincrby(monthly_key, score, str(user_id)))
    from .badges import check_badges
    badges_unlocked = check_badges(user_id)
    published = _publish_karma_update(
        user_id=user_id,
        kind=kind,
        delta=score,
        new_total=new_total,
        monthly_total=monthly_total,
        badges_unlocked=badges_unlocked,
    )

    return {
        'event_id': str(event.id),
        'user_id': user_id,
        'kind': kind,
        'delta': score,
        'new_total': new_total,
        'monthly_total': monthly_total,
        'badges_unlocked': badges_unlocked,
        'awarded': True,
        'published': published,
    }


def _handler_for(kind: str):
    def handler(**context):
        return apply_karma(kind=kind, **context)

    return handler


for _event_kind in SCORES:
    register_karma_event(_event_kind)(_handler_for(_event_kind))

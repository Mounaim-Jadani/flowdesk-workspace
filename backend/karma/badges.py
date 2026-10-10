"""Idempotent Karma badge rules."""

from django.db.models import Count
from django.utils import timezone

from .models import Badge, KarmaEvent


def check_badges(user_id: int) -> list[str]:
    """Award the simple event-count badges and return newly unlocked kinds."""

    definitions = (
        (
            'problem_solver',
            KarmaEvent.objects.filter(
                user_id=user_id,
                kind='item_resolved',
                metadata__room_type='group',
            ).count(),
            10,
        ),
        (
            'reliable_partner',
            KarmaEvent.objects.filter(
                user_id=user_id,
                kind='dm_item_ontime',
                metadata__room_type='direct',
            ).count(),
            5,
        ),
        (
            'mentor',
            KarmaEvent.objects.filter(user_id=user_id, kind='mentorship_completed').count(),
            5,
        ),
        (
            'pillar',
            KarmaEvent.objects.filter(user_id=user_id, kind='peer_help').dates('created_at', 'day').count(),
            60,
        ),
    )

    unlocked: list[str] = []
    for kind, count, threshold in definitions:
        if count >= threshold:
            _, created = Badge.objects.get_or_create(user_id=user_id, kind=kind, period_key=None)
            if created:
                unlocked.append(kind)
    return unlocked


def award_monthly_top_contributors() -> list[tuple[int, str]]:
    """Persist top-three monthly badges and return newly awarded badges."""
    from django.contrib.auth import get_user_model
    from .rules import KARMA_MONTHLY_KEY_PREFIX, get_karma_redis

    period_key = timezone.now().strftime('%Y-%m')
    entries = get_karma_redis().zrevrange(f'{KARMA_MONTHLY_KEY_PREFIX}{period_key}', 0, 2, withscores=True)
    # Redis can retain scores for users removed from the database. Never let a
    # stale leaderboard entry break the public leaderboard endpoint through a
    # foreign-key error while awarding badges.
    candidate_ids = [int(user_id) for user_id, score in entries if float(score) > 0]
    valid_user_ids = set(
        get_user_model().objects.filter(id__in=candidate_ids).values_list('id', flat=True)
    )
    awarded = []
    for user_id, score in entries:
        user_id = int(user_id)
        if float(score) <= 0 or user_id not in valid_user_ids:
            continue
        _, created = Badge.objects.get_or_create(
            user_id=user_id, kind='top_contributor', period_key=period_key,
        )
        if created:
            awarded.append((user_id, period_key))
    return awarded

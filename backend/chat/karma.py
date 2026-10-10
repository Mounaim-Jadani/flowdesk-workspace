"""Karma integrations for messages and group participation."""

import re
from datetime import timedelta

from django.utils import timezone

from karma.signals_bus import emit_karma


WELCOME_PATTERN = re.compile(r'\b(bienvenue|welcome)\b', re.IGNORECASE)


def award_message_karma(message_id):
    """Award peer-help and welcome events caused by one stored message."""

    from .models import Message

    message = Message.objects.select_related('room', 'sender', 'reply_to', 'reply_to__sender').get(id=message_id)
    if message.room.room_type != 'group' or message.sender_id is None:
        return []

    results = []
    parent = message.reply_to
    if (
        parent
        and parent.sender_id
        and parent.sender_id != message.sender_id
        and not re.search(rf'@{re.escape(message.sender.username)}\b', parent.content, re.IGNORECASE)
    ):
        results.append(emit_karma(
            'peer_help',
            user_id=message.sender_id,
            room_id=str(message.room_id),
            metadata={
                'thread_id': str(parent.id),
                'helped_user_id': str(parent.sender_id),
                'room_type': 'group',
            },
            source_key=f'peer_help:{message.id}',
        ))

    if WELCOME_PATTERN.search(message.content):
        recent_participant = message.room.room_participants.filter(
            joined_at__gte=timezone.now() - timedelta(minutes=5),
        ).exclude(user_id=message.sender_id).first()
        if recent_participant and re.search(
            rf'@{re.escape(recent_participant.user.username)}\b',
            message.content,
            re.IGNORECASE,
        ):
            results.append(emit_karma(
                'welcome',
                user_id=message.sender_id,
                room_id=str(message.room_id),
                metadata={
                    'room_type': 'group',
                    'welcomed_user_id': str(recent_participant.user_id),
                },
                source_key=f'welcome:{message.room_id}:{recent_participant.user_id}:{recent_participant.joined_at.isoformat()}',
            ))

    return results

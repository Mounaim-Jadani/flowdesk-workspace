"""Karma integrations for Action Items."""

from django.utils import timezone

from karma.signals_bus import emit_karma


def award_completed_item(item_id):
    """Award the appropriate completion event once for an Action Item."""

    from .models import ActionItem

    item = ActionItem.objects.select_related('room', 'assignee').get(id=item_id)
    if item.status != 'done' or item.assignee_id is None:
        return None

    room_type = item.room.room_type
    metadata = {
        'source_item_id': str(item.id),
        'room_type': room_type,
    }
    if room_type == 'direct':
        if not item.due_at or not item.completed_at or item.completed_at > item.due_at:
            return None
        return emit_karma(
            'dm_item_ontime',
            user_id=item.assignee_id,
            room_id=str(item.room_id),
            metadata=metadata,
            source_key=f'dm_item_ontime:{item.id}',
        )

    result = emit_karma(
        'item_resolved',
        user_id=item.assignee_id,
        room_id=str(item.room_id),
        metadata=metadata,
        source_key=f'item_resolved:{item.id}',
    )
    if item.reassigned_from_id and result and result.get('awarded'):
        emit_karma(
            'mentorship_completed',
            user_id=item.reassigned_from_id,
            room_id=str(item.room_id),
            metadata={'room_type': 'group', 'source_item_id': str(item.id), 'mentee_id': item.assignee_id},
            source_key=f'mentorship_completed:{item.id}',
        )
    return result

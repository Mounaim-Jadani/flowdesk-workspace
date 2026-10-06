"""Publish due messages independently of any connected browser."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from chat.models import Message
from chat.serializers import MessageSerializer


class Command(BaseCommand):
    help = 'Deliver scheduled messages whose visible_from timestamp has passed.'

    def handle(self, *args, **options):
        channel_layer = get_channel_layer()
        delivered = 0
        # Lock messages so overlapping worker invocations do not publish twice.
        with transaction.atomic():
            messages = Message.objects.select_for_update(
                skip_locked=True, of=('self',)
            ).filter(
                visible_from__lte=timezone.now(), scheduled_dispatched_at__isnull=True,
            ).select_related('room', 'sender')
            for message in messages:
                if not message.is_deleted:
                    payload = dict(MessageSerializer(message).data)
                    # The timestamp is an internal delivery gate. Once the
                    # worker publishes the message, clients must treat it as
                    # visible immediately.
                    payload['visible_from'] = None
                    async_to_sync(channel_layer.group_send)(
                        f'chat_{message.room_id}', {'type': 'chat_message', 'message': payload},
                    )
                    for user_id in message.room.participants.exclude(id=message.sender_id).values_list('id', flat=True):
                        async_to_sync(channel_layer.group_send)(
                            f'user_{user_id}', {'type': 'new_message_alert', 'message': payload},
                        )
                    delivered += 1
                message.scheduled_dispatched_at = timezone.now()
                message.save(update_fields=['scheduled_dispatched_at'])
        self.stdout.write(f'Delivered {delivered} scheduled message(s).')

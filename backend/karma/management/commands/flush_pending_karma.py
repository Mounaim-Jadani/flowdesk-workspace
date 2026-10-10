from django.core.management.base import BaseCommand

from karma.rules import (
    KARMA_GLOBAL_KEY,
    KARMA_MONTHLY_KEY_PREFIX,
    KARMA_PENDING_KEY_PREFIX,
    KARMA_PUSH_LOCK_PREFIX,
    _as_int,
    _monthly_key,
    get_karma_redis,
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone


class Command(BaseCommand):
    help = 'Flush Karma live updates accumulated during the notification throttle window.'

    def handle(self, *args, **options):
        client = get_karma_redis()
        month_key = _monthly_key(timezone.now())
        sent = 0
        for raw_key in client.scan_iter(match=f'{KARMA_PENDING_KEY_PREFIX}*'):
            user_id = str(raw_key).removeprefix(KARMA_PENDING_KEY_PREFIX)
            lock_key = f'{KARMA_PUSH_LOCK_PREFIX}{user_id}'
            if client.exists(lock_key):
                continue
            delta = _as_int(client.getdel(raw_key))
            if not delta:
                continue
            new_total = _as_int(client.zscore(KARMA_GLOBAL_KEY, user_id))
            monthly_total = _as_int(client.zscore(month_key, user_id))
            async_to_sync(get_channel_layer().group_send)(
                'online_status',
                {'type': 'relay_event', 'payload': {
                    'kind': 'karma_update',
                    'user_id': int(user_id),
                    'delta': delta,
                    'new_total': new_total,
                    'monthly_total': monthly_total,
                    'event_kind': 'batched',
                    'badges_unlocked': [],
                }},
            )
            client.set(lock_key, '1', ex=10)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f'Flushed pending Karma updates: {sent}'))

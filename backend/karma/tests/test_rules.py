from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from chat.models import ChatRoom
from karma.models import KarmaEvent
from karma.rules import (
    KARMA_GLOBAL_KEY,
    KARMA_MONTHLY_KEY_PREFIX,
    SCORES,
    apply_karma,
    get_karma_redis,
    score_for_event,
)
from karma.signals_bus import emit_karma


class KarmaRulesTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='karma-user@example.com',
            username='karma-user',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            email='karma-other@example.com',
            username='karma-other',
            password='test-password',
        )
        self.room = ChatRoom.objects.create(room_type='group', created_by=self.user)
        self.redis = get_karma_redis()
        self.redis.delete(
            KARMA_GLOBAL_KEY,
            f'{KARMA_MONTHLY_KEY_PREFIX}{timezone.now():%Y-%m}',
            f'karma:pending:{self.user.id}',
            f'karma:push-lock:{self.user.id}',
        )

    def tearDown(self):
        self.redis.delete(
            KARMA_GLOBAL_KEY,
            f'{KARMA_MONTHLY_KEY_PREFIX}{timezone.now():%Y-%m}',
            f'karma:pending:{self.user.id}',
            f'karma:push-lock:{self.user.id}',
        )

    def channel_layer_patches(self):
        return (
            patch('karma.rules.get_channel_layer'),
            patch('karma.rules.async_to_sync'),
        )

    def test_score_table_contains_only_the_six_defined_event_values(self):
        self.assertEqual(SCORES, {
            'item_resolved': 10,
            'peer_help': 4,
            'welcome': 5,
            'clarification_upvoted': 2,
            'mentorship_completed': 12,
            'dm_item_ontime': 6,
        })
        for kind, expected_score in SCORES.items():
            self.assertEqual(score_for_event(kind), expected_score)

    def test_unknown_event_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            score_for_event('message_sent')

    @patch('karma.rules.get_channel_layer')
    @patch('karma.rules.async_to_sync')
    def test_apply_karma_persists_event_updates_both_leaderboards_and_publishes(self, async_to_sync_mock, get_layer_mock):
        send_mock = async_to_sync_mock.return_value

        result = apply_karma(
            user_id=self.user.id,
            kind='item_resolved',
            room_id=str(self.room.id),
            metadata={'source_item_id': 'item-1'},
        )

        self.assertTrue(result['awarded'])
        self.assertEqual(result['delta'], 10)
        self.assertEqual(result['new_total'], 10)
        self.assertEqual(result['monthly_total'], 10)
        self.assertTrue(result['published'])

        event = KarmaEvent.objects.get(id=result['event_id'])
        self.assertEqual(event.user_id, self.user.id)
        self.assertEqual(event.room_id, self.room.id)
        self.assertEqual(event.kind, 'item_resolved')
        self.assertEqual(event.score, 10)
        self.assertEqual(event.metadata['source_item_id'], 'item-1')
        self.assertEqual(self.redis.zscore(KARMA_GLOBAL_KEY, str(self.user.id)), 10.0)

        month_key = f'{KARMA_MONTHLY_KEY_PREFIX}{timezone.now():%Y-%m}'
        self.assertEqual(self.redis.zscore(month_key, str(self.user.id)), 10.0)
        get_layer_mock.assert_called_once()
        send_mock.assert_called_once()
        group_name, payload = send_mock.call_args.args
        self.assertEqual(group_name, 'online_status')
        self.assertEqual(payload['type'], 'relay_event')
        self.assertEqual(payload['payload']['kind'], 'karma_update')
        self.assertEqual(payload['payload']['delta'], 10)

    @patch('karma.rules.get_channel_layer')
    @patch('karma.rules.async_to_sync')
    def test_emit_karma_uses_the_registered_scoring_handler(self, async_to_sync_mock, get_layer_mock):
        result = emit_karma(
            'welcome',
            user_id=self.user.id,
            room_id=str(self.room.id),
        )

        self.assertTrue(result['awarded'])
        self.assertEqual(result['delta'], 5)
        self.assertEqual(KarmaEvent.objects.get().kind, 'welcome')

    @patch('karma.rules.get_channel_layer')
    @patch('karma.rules.async_to_sync')
    def test_peer_help_is_limited_to_three_rewards_per_thread_and_day(self, async_to_sync_mock, get_layer_mock):
        metadata = {'thread_id': 'thread-1', 'helped_user_id': self.other_user.id}

        results = [
            apply_karma(
                user_id=self.user.id,
                kind='peer_help',
                room_id=str(self.room.id),
                metadata=metadata,
            )
            for _ in range(4)
        ]

        self.assertEqual([result['delta'] for result in results], [4, 4, 4, 0])
        self.assertEqual(KarmaEvent.objects.filter(kind='peer_help').count(), 3)
        self.assertEqual(self.redis.zscore(KARMA_GLOBAL_KEY, str(self.user.id)), 12.0)
        self.assertEqual(results[-1]['reason'], 'daily_limit_reached')

    @patch('karma.rules.get_channel_layer')
    @patch('karma.rules.async_to_sync')
    def test_throttled_live_updates_accumulate_pending_delta(self, async_to_sync_mock, get_layer_mock):
        first = apply_karma(user_id=self.user.id, kind='item_resolved')
        second = apply_karma(user_id=self.user.id, kind='item_resolved')

        self.assertTrue(first['published'])
        self.assertFalse(second['published'])
        self.assertEqual(self.redis.get(f'karma:pending:{self.user.id}'), '10')
        self.assertEqual(async_to_sync_mock.call_count, 1)

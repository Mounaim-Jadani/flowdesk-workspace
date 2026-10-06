from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, Message, RoomParticipant
from checklist.models import ActionItem
from digest.models import RoomDigest
from digest.views import DigestConsumeView, DigestRoomView
from digest.generator import SUMMARY_PROMPT_VERSION


class DigestViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.alice = user_model.objects.create_user(
            email='digest-alice@example.com', username='digest-alice', password='test-password'
        )
        self.bob = user_model.objects.create_user(
            email='digest-bob@example.com', username='digest-bob', password='test-password'
        )
        self.room = ChatRoom.objects.create(room_type='direct', created_by=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.bob)
        self.factory = APIRequestFactory()

    def request(self):
        request = self.factory.get('/api/digest/rooms/{}/'.format(self.room.id))
        force_authenticate(request, user=self.bob)
        return request

    def test_new_messages_invalidate_cached_digest(self):
        old_until = timezone.now() - timedelta(hours=1)
        RoomDigest.objects.create(
            room=self.room,
            user=self.bob,
            since=old_until - timedelta(days=1),
            until=old_until,
            summary='Old summary',
            stats={
                'summary_prompt_version': SUMMARY_PROMPT_VERSION,
                'summary_model': 'test-model',
                'summary_language': 'french',
            },
        )
        participant = self.room.room_participants.get(user=self.bob)
        participant.last_read_at = old_until
        participant.save(update_fields=['last_read_at'])
        for _ in range(8):
            Message.objects.create(room=self.room, sender=self.alice, content='New message')

        with patch('digest.views.build_digest', return_value={
            'summary': 'New summary', 'key_points': [], 'mentions': [],
            'stats': {'summary_prompt_version': SUMMARY_PROMPT_VERSION, 'summary_model': 'test-model'},
        }) as build_digest:
            response = DigestRoomView.as_view()(self.request(), room_id=self.room.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary'], 'New summary')
        build_digest.assert_called_once()

    def test_consume_marks_the_latest_digest_as_consumed(self):
        digest = RoomDigest.objects.create(
            room=self.room,
            user=self.bob,
            since=timezone.now() - timedelta(days=1),
            until=timezone.now(),
            summary='Summary',
        )
        request = self.factory.post('/api/digest/rooms/{}/consume/'.format(self.room.id))
        force_authenticate(request, user=self.bob)

        response = DigestConsumeView.as_view()(request, room_id=self.room.id)

        self.assertEqual(response.status_code, 200)
        digest.refresh_from_db()
        self.assertIsNotNone(digest.consumed_at)

    def test_open_items_count_only_includes_current_user_open_items(self):
        for index in range(8):
            Message.objects.create(room=self.room, sender=self.alice, content=f'Unread {index}')

        ActionItem.objects.create(
            room=self.room,
            assignee=self.bob,
            created_by=self.alice,
            description='Bob open action',
        )
        ActionItem.objects.create(
            room=self.room,
            assignee=self.alice,
            created_by=self.alice,
            description='Alice open action',
        )
        ActionItem.objects.create(
            room=self.room,
            assignee=self.bob,
            created_by=self.alice,
            description='Bob completed action',
            status='done',
        )

        with patch('digest.views.build_digest', return_value={
            'summary': 'Summary', 'key_points': [], 'mentions': [], 'stats': {},
        }):
            response = DigestRoomView.as_view()(self.request(), room_id=self.room.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['stats']['open_items'], 1)

    def test_cached_digest_refreshes_open_items_count(self):
        RoomDigest.objects.create(
            room=self.room,
            user=self.bob,
            since=timezone.now() - timedelta(days=1),
            until=timezone.now(),
            summary='Cached summary',
            stats={
                'summary_prompt_version': SUMMARY_PROMPT_VERSION,
                'summary_model': 'test-model',
                'summary_language': 'french',
                'open_items': 99,
            },
        )
        ActionItem.objects.create(
            room=self.room,
            assignee=self.bob,
            created_by=self.alice,
            description='Current open action',
        )

        response = DigestRoomView.as_view()(self.request(), room_id=self.room.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['stats']['open_items'], 1)

    def test_room_without_pending_digest_returns_no_content_below_threshold(self):
        response = DigestRoomView.as_view()(self.request(), room_id=self.room.id)

        self.assertEqual(response.status_code, 204)

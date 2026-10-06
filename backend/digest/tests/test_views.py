from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, Message, RoomParticipant
from digest.models import RoomDigest
from digest.views import DigestRoomView
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

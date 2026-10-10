from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, RoomParticipant
from karma.models import KarmaEvent
from karma.views import LeaderboardView, MyKarmaView


class KarmaApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='karma-api@example.com', username='karma-api', password='test-password'
        )
        KarmaEvent.objects.create(
            user=self.user,
            kind='item_resolved',
            score=10,
            source_key='api-event-1',
            metadata={'room_type': 'group'},
        )
        self.factory = APIRequestFactory()

    def test_my_karma_uses_group_rank_when_room_is_requested(self):
        bob = get_user_model().objects.create_user(
            email='karma-api-bob@example.com', username='karma-api-bob', password='test-password'
        )
        room = ChatRoom.objects.create(room_type='group', created_by=self.user)
        RoomParticipant.objects.create(room=room, user=self.user)
        RoomParticipant.objects.create(room=room, user=bob)
        KarmaEvent.objects.create(
            user=self.user,
            room=room,
            kind='peer_help',
            score=6,
            source_key='api-room-event-1',
        )
        KarmaEvent.objects.create(
            user=bob,
            room=room,
            kind='item_resolved',
            score=16,
            source_key='api-room-event-2',
        )

        response = MyKarmaView.as_view()(self.request('get', f'/api/karma/me/?room_id={room.id}'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rank'], 2)

    def request(self, method, path):
        request = getattr(self.factory, method)(path)
        force_authenticate(request, user=self.user)
        return request

    def test_my_karma_returns_score_badges_and_recent_events(self):
        response = MyKarmaView.as_view()(self.request('get', '/api/karma/me/'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 10)
        self.assertEqual(response.data['recent_events'][0]['kind'], 'item_resolved')

    def test_leaderboard_endpoint_is_available(self):
        response = LeaderboardView.as_view()(self.request('get', '/api/karma/leaderboard/?scope=month'))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

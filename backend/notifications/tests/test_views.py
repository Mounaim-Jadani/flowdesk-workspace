from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, RoomParticipant
from notifications.models import Notification
from notifications.views import list_notifications, mark_notification_read


class NotificationViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='notification@example.com', username='notification-user', password='test-password'
        )
        self.room = ChatRoom.objects.create(room_type='direct', created_by=self.user)
        RoomParticipant.objects.create(room=self.room, user=self.user)
        self.factory = APIRequestFactory()

    def request(self, method, path, data=None):
        request = getattr(self.factory, method)(path, data or {}, format='json')
        force_authenticate(request, user=self.user)
        return request

    def test_notifications_can_be_loaded_and_marked_read(self):
        item = Notification.objects.create(
            recipient=self.user, room=self.room, kind='assignment', payload={'room_id': str(self.room.id)}
        )
        response = list_notifications(self.request('get', '/api/notifications/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], str(item.id))
        read_response = mark_notification_read(
            self.request('post', '/api/notifications/read/'), notification_id=item.id
        )
        self.assertEqual(read_response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_read)

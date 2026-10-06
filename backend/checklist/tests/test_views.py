from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, RoomParticipant
from checklist.models import ActionItem
from checklist.views import mark_item_done, patch_item


class ChecklistViewTests(TransactionTestCase):
    def setUp(self):
        user_model = get_user_model()
        self.alice = user_model.objects.create_user(
            email='alice-checklist@example.com', username='alice-checklist', password='test-password'
        )
        self.bob = user_model.objects.create_user(
            email='bob-checklist@example.com', username='bob-checklist', password='test-password'
        )
        self.room = ChatRoom.objects.create(room_type='group', created_by=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.bob)
        self.factory = APIRequestFactory()

    def request(self, method, data, user):
        request = getattr(self.factory, method)('/api/checklist/items/', data, format='json')
        force_authenticate(request, user=user)
        return request

    @patch('checklist.views.get_channel_layer')
    def test_non_member_cannot_be_assignee(self, get_layer):
        outsider = get_user_model().objects.create_user(
            email='outsider-checklist@example.com', username='outsider-checklist', password='test-password'
        )
        request = self.request('post', {
            'room_id': str(self.room.id),
            'description': 'Task',
            'assignee_id': outsider.id,
        }, self.alice)
        from checklist.views import create_item
        response = create_item(request)
        self.assertEqual(response.status_code, 400)
        get_layer.assert_not_called()

    @patch('checklist.views.get_channel_layer')
    def test_assignee_can_complete_and_room_receives_update(self, get_layer):
        get_layer.return_value.group_send = AsyncMock()
        item = ActionItem.objects.create(
            room=self.room, created_by=self.alice, assignee=self.bob, description='Task'
        )
        response = mark_item_done(self.request('post', {}, self.bob), item_id=item.id)
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, 'done')
        event = get_layer.return_value.group_send.call_args.args[1]
        self.assertEqual(event['type'], 'relay_event')

    def test_unrelated_room_message_cannot_be_edited_over_websocket(self):
        from chat.consumers import ChatConsumer
        from chat.models import Message
        other_room = ChatRoom.objects.create(room_type='direct', created_by=self.alice)
        message = Message.objects.create(room=other_room, sender=self.alice, content='Private')
        consumer = ChatConsumer()
        consumer.room_id = str(self.room.id)
        consumer.user = self.alice
        result = async_to_sync(consumer.edit_message)(str(message.id), 'Changed')
        self.assertIsNone(result)

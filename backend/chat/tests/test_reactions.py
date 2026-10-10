from unittest.mock import AsyncMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from chat.models import ChatRoom, Message, Reaction, RoomParticipant
from chat.views import MessageReactionView


class ReactionViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.alice = user_model.objects.create_user(
            email='reaction-alice@example.com', username='reaction-alice', password='test-password'
        )
        self.bob = user_model.objects.create_user(
            email='reaction-bob@example.com', username='reaction-bob', password='test-password'
        )
        self.room = ChatRoom.objects.create(room_type='group', created_by=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.bob)
        self.message = Message.objects.create(room=self.room, sender=self.alice, content='Helpful answer')
        self.factory = APIRequestFactory()

    def request(self, method, user, data=None):
        request = getattr(self.factory, method)(f'/api/chat/rooms/{self.room.id}/messages/{self.message.id}/reactions/', data or {}, format='json')
        force_authenticate(request, user=user)
        return request

    @patch('chat.views.get_channel_layer')
    def test_user_can_add_and_remove_thumb_reaction(self, get_layer):
        get_layer.return_value.group_send = AsyncMock()
        add_response = MessageReactionView.as_view()(self.request('post', self.bob), room_id=self.room.id, message_id=self.message.id)
        self.assertEqual(add_response.status_code, 201)
        self.assertTrue(Reaction.objects.filter(message=self.message, user=self.bob, emoji='👍').exists())

        delete_response = MessageReactionView.as_view()(self.request('delete', self.bob), room_id=self.room.id, message_id=self.message.id)
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Reaction.objects.filter(message=self.message, user=self.bob, emoji='👍').exists())

    @patch('chat.views.get_channel_layer')
    def test_multiple_supported_reactions_are_accepted(self, get_layer):
        get_layer.return_value.group_send = AsyncMock()
        response = MessageReactionView.as_view()(self.request('post', self.bob, {'emoji': '❤️'}), room_id=self.room.id, message_id=self.message.id)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Reaction.objects.filter(message=self.message, user=self.bob, emoji='❤️').exists())

        second_response = MessageReactionView.as_view()(self.request('post', self.bob, {'emoji': '😂'}), room_id=self.room.id, message_id=self.message.id)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(Reaction.objects.filter(message=self.message, user=self.bob).count(), 2)

    def test_unsupported_reaction_is_rejected(self):
        response = MessageReactionView.as_view()(self.request('post', self.bob, {'emoji': '🚀'}), room_id=self.room.id, message_id=self.message.id)
        self.assertEqual(response.status_code, 400)

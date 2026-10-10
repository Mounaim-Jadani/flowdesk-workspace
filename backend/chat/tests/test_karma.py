from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from chat.karma import award_message_karma
from chat.models import ChatRoom, Message, RoomParticipant


class MessageKarmaIntegrationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.alice = user_model.objects.create_user(
            email='chat-karma-alice@example.com', username='chat-karma-alice', password='test-password'
        )
        self.bob = user_model.objects.create_user(
            email='chat-karma-bob@example.com', username='chat-karma-bob', password='test-password'
        )
        self.room = ChatRoom.objects.create(room_type='group', created_by=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.alice)
        RoomParticipant.objects.create(room=self.room, user=self.bob)

    @patch('karma.rules.apply_karma', return_value={'awarded': True, 'delta': 5})
    def test_welcome_message_rewards_existing_member_for_recent_new_member(self, apply):
        message = Message.objects.create(
            room=self.room,
            sender=self.alice,
            content='Bienvenue @chat-karma-bob !',
        )

        award_message_karma(message.id)

        apply.assert_called_once()
        self.assertEqual(apply.call_args.kwargs['kind'], 'welcome')
        self.assertEqual(apply.call_args.kwargs['user_id'], self.alice.id)

    @patch('karma.rules.apply_karma', return_value={'awarded': True, 'delta': 4})
    def test_reply_to_message_that_mentions_author_does_not_reward_peer_help(self, apply):
        parent = Message.objects.create(
            room=self.room,
            sender=self.alice,
            content='@chat-karma-bob peux-tu regarder cela ?',
        )
        reply = Message.objects.create(
            room=self.room,
            sender=self.bob,
            content='Oui, je regarde.',
            reply_to=parent,
        )

        award_message_karma(reply.id)

        apply.assert_not_called()

"""
WebSocket consumers for real-time chat functionality.
Handles messaging, typing indicators, and online status.
"""
import json
import logging
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from checklist.engine import detect_commitment
from checklist.deadlines import resolve_deadline

from .models import ChatRoom, Message, RoomParticipant
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat rooms.
    Handles real-time messaging, typing indicators, and read receipts.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Reject if not authenticated
        if self.user.is_anonymous:
            logger.warning(f"Rejected anonymous WebSocket connection to room {self.room_id}")
            await self.close()
            return

        # Verify user is a participant
        if not await self.is_room_participant():
            logger.warning(f"User {self.user.id} not in room {self.room_id}")
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Notify room of user joining
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

        logger.info(f"User {self.user.username} connected to room {self.room_id}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name') and not self.user.is_anonymous:
            # Clear typing status
            await self.set_typing_status(False)

            # Notify room of user leaving
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'user_id': self.user.id,
                    'username': self.user.username,
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            logger.info(f"User {self.user.username} disconnected from room {self.room_id}")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            handlers = {
                'message': self.handle_message,
                'typing': self.handle_typing,
                'read': self.handle_read,
                'edit': self.handle_edit,
                'delete': self.handle_delete,
                'checklist_toggle': self.handle_checklist_toggle,
            }

            from .constants import MESSAGE_TYPE_TO_CAPABILITY
            cap = MESSAGE_TYPE_TO_CAPABILITY.get(message_type)
            if cap:
                room_capabilities = await self.get_room_capabilities()
                if cap not in room_capabilities:
                    logger.debug(f"Capability {cap} disabled for room {self.room_id}")
                    return  # rejet silencieux

            handler = handlers.get(message_type)
            if handler is None:
                await self.send(json.dumps({'type': 'error', 'detail': 'Unknown message type'}))
                return

            await handler(data)

        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def handle_message(self, data):
        """Handle new message."""
        content = data.get('content', '').strip()
        reply_to = data.get('reply_to')

        if not content:
            return

        # Save message to database
        visible_from = None
        if data.get('visible_from'):
            try:
                visible_from = parse_datetime(data['visible_from'])
                if visible_from is None or timezone.is_naive(visible_from):
                    raise ValueError('An ISO timestamp with timezone is required.')
            except (TypeError, ValueError):
                await self.send(json.dumps({'type': 'error', 'detail': 'Invalid scheduled time.'}))
                return
            if visible_from <= timezone.now():
                visible_from = None
            elif await self.get_room_type() != 'direct':
                await self.send(json.dumps({'type': 'error', 'detail': 'Scheduling is only supported in direct messages.'}))
                return
        message = await self.save_message(content, reply_to, visible_from)

        if message:
            serialized_message = await self.serialize_message(message)
            if message.visible_from and message.visible_from > timezone.now():
                # Acknowledge only to the sender. The worker publishes at delivery time.
                await self.send(json.dumps({'type': 'message', 'message': serialized_message}))
                return
            # Broadcast to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': serialized_message,
                }
            )

            # Broadcast to all participants globally (for sidebar updates)
            participant_ids = await self.get_room_participant_ids()
            for p_id in participant_ids:
                if p_id != self.user.id:
                    await self.channel_layer.group_send(
                        f'user_{p_id}',
                        {
                            'type': 'new_message_alert',
                            'message': serialized_message,
                        }
                    )

            room_capabilities = await self.get_room_capabilities()
            if 'checklist' in room_capabilities and message.content:
                detection = detect_commitment(message.content)
                if detection and detection['confidence'] >= 0.6:
                    due_at = (
                        resolve_deadline(detection['deadline_raw'], timezone.now())
                        if detection.get('deadline_raw') else None
                    )
                    due_at_iso = due_at.isoformat() if due_at else None
                    assignee_data = await self._resolve_assignee(detection)
                    
                    await self.send(text_data=json.dumps({
                        'type': 'commitment_detected',
                        'room_id': str(self.room_id),
                        'message_id': str(message.id),
                        'preview': message.content[:120],
                        'suggested_description': message.content[:280],
                        'suggested_assignee': assignee_data,
                        'suggested_due_at': due_at_iso,
                    }))

    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)

        await self.set_typing_status(is_typing)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_read(self, data):
        """Handle read receipt."""
        await self.mark_as_read()

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'user_id': self.user.id,
                'username': self.user.username,
                'read_at': timezone.now().isoformat(),
            }
        )

    async def handle_edit(self, data):
        """Handle message edit."""
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()

        if not message_id or not new_content:
            return

        message = await self.edit_message(message_id, new_content)

        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message': await self.serialize_message(message),
                }
            )

    async def handle_delete(self, data):
        """Handle message deletion."""
        message_id = data.get('message_id')

        if not message_id:
            return

        success = await self.delete_message(message_id)

        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'user_id': self.user.id,
                }
            )

    async def handle_checklist_toggle(self, data):
        """Handle checklist toggle."""
        item_id = data.get('item_id')
        done = data.get('done')
        
        if not item_id or done is None:
            return
            
        item = await self.toggle_action_item(item_id, done)
        if item:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'checklist_event',
                    'payload': {
                        'kind': 'item_toggled',
                        'item_id': str(item.id),
                        'done': done
                    }
                }
            )

    # Channel layer event handlers

    async def chat_message(self, event):
        """Send message to WebSocket."""
        if not self.can_receive_message(event['message']):
            return
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send to the user who is typing
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'read',
            'user_id': event['user_id'],
            'username': event['username'],
            'read_at': event['read_at'],
        }))

    async def message_edited(self, event):
        """Send edited message to WebSocket."""
        if not self.can_receive_message(event['message']):
            return
        await self.send(text_data=json.dumps({
            'type': 'edit',
            'message': event['message'],
        }))

    async def message_deleted(self, event):
        """Send deletion notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'delete',
            'message_id': event['message_id'],
        }))

    async def user_join(self, event):
        """Notify of user joining."""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_join',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def user_leave(self, event):
        """Notify of user leaving."""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_leave',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def checklist_event(self, event):
        """Send checklist event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'checklist',
            'payload': event['payload']
        }))

    async def relay_event(self, event):
        """Relay REST-originated events to room WebSocket clients."""
        payload = event.get('payload', {})
        if payload.get('type') == 'checklist_event':
            await self.send(text_data=json.dumps({
                'type': 'checklist',
                'payload': {
                    key: value for key, value in payload.items() if key != 'type'
                },
            }))
        else:
            await self.send(text_data=json.dumps(payload))

    # Database operations

    def can_receive_message(self, message):
        visible_from = message.get('visible_from')
        return (
            not visible_from or parse_datetime(visible_from) <= timezone.now() or
            message.get('sender', {}).get('id') == self.user.id
        )

    @database_sync_to_async
    def get_room_type(self):
        return ChatRoom.objects.get(id=self.room_id).room_type

    @database_sync_to_async
    def is_room_participant(self):
        """Check if user is a participant in the room."""
        return RoomParticipant.objects.filter(
            room_id=self.room_id,
            user=self.user
        ).exists()

    @database_sync_to_async
    def get_room_capabilities(self):
        """Get capabilities for the room."""
        room = ChatRoom.objects.get(id=self.room_id)
        return room.capabilities

    @database_sync_to_async
    def get_room_participant_ids(self):
        """Get all participant IDs for the room."""
        room = ChatRoom.objects.get(id=self.room_id)
        return list(room.participants.values_list('id', flat=True))

    @database_sync_to_async
    def save_message(self, content, reply_to=None, visible_from=None):
        """Save a new message to database."""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            if reply_to and not room.messages.visible_to(self.user).filter(pk=reply_to).exists():
                return None
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                reply_to_id=reply_to,
                visible_from=visible_from,
            )
            room.save()  # Update room timestamp
            return message
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for JSON response."""
        return {
            'id': str(message.id),
            'room': str(message.room_id),
            'sender': {
                'id': message.sender.id,
                'username': message.sender.username,
                'display_name': message.sender.get_display_name(),
                'avatar_url': message.sender.avatar.url if message.sender.avatar else None,
                'is_online': message.sender.is_online,
            },
            'content': message.content,
            'message_type': message.message_type,
            'reply_to': str(message.reply_to_id) if message.reply_to_id else None,
            'is_edited': message.is_edited,
            'is_deleted': message.is_deleted,
            'created_at': message.created_at.isoformat(),
            'visible_from': message.visible_from.isoformat() if message.visible_from else None,
        }

    @database_sync_to_async
    def set_typing_status(self, is_typing):
        """Update user's typing status."""
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            participant.set_typing(is_typing)
        except RoomParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_as_read(self):
        """Mark messages as read for user."""
        try:
            participant = RoomParticipant.objects.get(
                room_id=self.room_id,
                user=self.user
            )
            participant.mark_as_read()
        except RoomParticipant.DoesNotExist:
            pass

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit a message."""
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.user,
                room_id=self.room_id,
                is_deleted=False
            )
            message.edit(new_content)
            return message
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def _resolve_assignee(self, detection):
        """Resolve the assignee based on business rules."""
        room = ChatRoom.objects.get(id=self.room_id)
        if room.room_type == 'direct':
            other_user = room.participants.exclude(id=self.user.id).first()
            if other_user:
                return {'id': str(other_user.id), 'username': other_user.username}
        elif room.room_type == 'group':
            mentions = detection.get('mentioned', [])
            if mentions:
                username_mentioned = mentions[0]
                mentioned_user = room.participants.filter(username__iexact=username_mentioned).first()
                if mentioned_user:
                    return {'id': str(mentioned_user.id), 'username': mentioned_user.username}
                else:
                    return None
            else:
                return {'id': str(self.user.id), 'username': self.user.username}
        return {'id': str(self.user.id), 'username': self.user.username}

    @database_sync_to_async
    def delete_message(self, message_id):
        """Soft delete a message."""
        try:
            message = Message.objects.get(
                id=message_id,
                sender=self.user,
                room_id=self.room_id,
                is_deleted=False
            )
            message.soft_delete()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def toggle_action_item(self, item_id, done):
        """Toggle an action item's status."""
        from checklist.models import ActionItem
        try:
            item = ActionItem.objects.get(id=item_id, room_id=self.room_id)
            if self.user != item.assignee and self.user != item.created_by:
                return None
            
            if done:
                item.status = 'done'
                item.completed_at = timezone.now()
            else:
                item.status = 'open'
                item.completed_at = None
                
            item.save()
            return item
        except ActionItem.DoesNotExist:
            return None


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for tracking online/offline status.
    Users connect to this to broadcast their online status.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        self.status_group = 'online_status'
        self.user_channel = f'user_{self.user.id}'

        # Join status group and user personal group
        await self.channel_layer.group_add(self.status_group, self.channel_name)
        await self.channel_layer.group_add(self.user_channel, self.channel_name)

        await self.accept()

        # Set user online
        await self.set_online_status(True)

        session = await self.get_user_deep_work()
        deep_work_data = {
            'active': True,
            'ends_at': session.ends_at.isoformat()
        } if session else None

        # Broadcast online status
        await self.channel_layer.group_send(
            self.status_group,
            {
                'type': 'status_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_online': True,
                'deep_work': deep_work_data,
            }
        )

        logger.info(f"User {self.user.username} is now online")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if not self.user.is_anonymous:
            # Set user offline
            await self.set_online_status(False)

            # Broadcast offline status
            await self.channel_layer.group_send(
                self.status_group,
                {
                    'type': 'status_update',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': False,
                    'deep_work': None,
                }
            )

            # Leave status group and personal group
            await self.channel_layer.group_discard(self.status_group, self.channel_name)
            await self.channel_layer.group_discard(self.user_channel, self.channel_name)

            logger.info(f"User {self.user.username} is now offline")

    async def receive(self, text_data):
        """Handle incoming messages (heartbeat)."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'heartbeat':
                await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))
        except json.JSONDecodeError:
            pass

    async def status_update(self, event):
        """Send status update to WebSocket."""
        payload = {
            'type': 'status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online'],
        }
        if 'deep_work' in event:
            payload['deep_work'] = event['deep_work']

        await self.send(text_data=json.dumps(payload))

    async def new_message_alert(self, event):
        """Receive global new message alert."""
        await self.send(text_data=json.dumps({
            'type': 'new_message_alert',
            'message': event['message'],
        }))

    # Handler de relais générique : renvoie le payload tel quel au socket
    async def relay_event(self, event):
        logger.info(f"Relaying event to user {self.user.id}: {event}")
        await self.send(text_data=json.dumps(event['payload']))

    @database_sync_to_async
    def set_online_status(self, is_online):
        """Update user's online status in database."""
        if is_online:
            self.user.set_online()
        else:
            self.user.set_offline()

    @database_sync_to_async
    def get_user_deep_work(self):
        from presence.utils import get_active_deep_work
        return get_active_deep_work(self.user)

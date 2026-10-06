"""
REST API views for chat functionality.
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max
from django.shortcuts import get_object_or_404

from .models import ChatRoom, RoomParticipant, Message
from .serializers import (
    ChatRoomSerializer,
    ChatRoomCreateSerializer,
    ChatRoomDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
)


class ChatRoomListView(generics.ListCreateAPIView):
    """List all chat rooms for current user or create a new room."""
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ChatRoomCreateSerializer
        return ChatRoomSerializer

    def get_queryset(self):
        return ChatRoom.objects.filter(
            participants=self.request.user,
            is_active=True
        ).annotate(
            last_activity=Max('messages__created_at')
        ).order_by('-last_activity', '-updated_at').prefetch_related(
            'participants', 'room_participants', 'messages'
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        return Response(
            ChatRoomSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific chat room."""
    permission_classes = (IsAuthenticated,)
    serializer_class = ChatRoomDetailSerializer

    def get_queryset(self):
        return ChatRoom.objects.filter(
            participants=self.request.user,
            is_active=True
        ).prefetch_related('participants', 'messages')

    def get_object(self):
        room = get_object_or_404(self.get_queryset(), id=self.kwargs['room_id'])
        # Mark as read when viewing
        participant = room.room_participants.filter(user=self.request.user).first()
        if participant:
            participant.mark_as_read()
        return room

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        participant = room.room_participants.filter(user=request.user).first()

        if participant and participant.role == 'owner':
            room.is_active = False
            room.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # Non-owners can only leave
            if participant:
                participant.delete()
            return Response({'message': 'Left the room.'}, status=status.HTTP_200_OK)


class MessageListView(generics.ListCreateAPIView):
    """List messages in a room or send a new message."""
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(
            ChatRoom.objects.filter(participants=self.request.user),
            id=room_id
        )
        return Message.objects.filter(room=room).visible_to(self.request.user).select_related('sender', 'reply_to')

    def create(self, request, *args, **kwargs):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(
            ChatRoom.objects.filter(participants=request.user),
            id=room_id
        )

        serializer = self.get_serializer(data={**request.data, 'room': str(room.id)})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user, room=room)

        # Update room's updated_at
        room.save()

        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, edit, or delete a specific message."""
    permission_classes = (IsAuthenticated,)
    serializer_class = MessageSerializer

    def get_object(self):
        message = get_object_or_404(
            Message.objects.visible_to(self.request.user).select_related('sender', 'room'),
            id=self.kwargs['message_id'],
            room_id=self.kwargs['room_id']
        )
        # Verify user is in the room
        if not message.room.participants.filter(id=self.request.user.id).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You are not a member of this room.')
        return message

    def update(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages.'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_content = request.data.get('content')
        if new_content:
            message.edit(new_content)
        return Response(MessageSerializer(message, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages.'},
                status=status.HTTP_403_FORBIDDEN
            )
        message.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DirectMessageView(APIView):
    """Create or get existing direct message room with a user."""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user_id == request.user.id:
            return Response(
                {'error': 'Cannot create DM with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            other_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check for existing DM
        existing_room = ChatRoom.objects.filter(
            room_type='direct',
            participants=request.user
        ).filter(
            participants=other_user
        ).first()

        if existing_room:
            return Response(
                ChatRoomSerializer(existing_room, context={'request': request}).data
            )

        # Create new DM room
        room = ChatRoom.objects.create(room_type='direct', created_by=request.user)
        RoomParticipant.objects.create(room=room, user=request.user, role='member')
        RoomParticipant.objects.create(room=room, user=other_user, role='member')

        return Response(
            ChatRoomSerializer(room, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MarkAsReadView(APIView):
    """Mark all messages in a room as read."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, room_id):
        room = get_object_or_404(
            ChatRoom.objects.filter(participants=request.user),
            id=room_id
        )
        participant = room.room_participants.filter(user=request.user).first()
        if participant:
            participant.mark_as_read()
        return Response({'message': 'Marked as read'})


class TypingStatusView(APIView):
    """Update typing status (backup for WebSocket)."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, room_id):
        room = get_object_or_404(
            ChatRoom.objects.filter(participants=request.user),
            id=room_id
        )
        participant = room.room_participants.filter(user=request.user).first()
        if participant:
            is_typing = request.data.get('is_typing', False)
            participant.set_typing(is_typing)
        return Response({'is_typing': is_typing})

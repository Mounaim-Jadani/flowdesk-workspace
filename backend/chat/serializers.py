"""
Serializers for chat functionality.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatRoom, RoomParticipant, Message, MessageRead
from accounts.serializers import UserMinimalSerializer

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages."""
    sender = UserMinimalSerializer(read_only=True)
    reply_to_preview = serializers.SerializerMethodField()
    is_own_message = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            'id', 'room', 'sender', 'content', 'message_type', 'attachment',
            'reply_to', 'reply_to_preview', 'is_edited', 'edited_at',
            'is_deleted', 'created_at', 'visible_from', 'is_own_message'
        )
        read_only_fields = ('id', 'sender', 'is_edited', 'edited_at', 'is_deleted', 'created_at')

    def get_reply_to_preview(self, obj):
        if obj.reply_to:
            request = self.context.get('request')
            user = request.user if request else None
            if not Message.objects.visible_to(user).filter(pk=obj.reply_to_id).exists():
                return None
            return {
                'id': str(obj.reply_to.id),
                'content': obj.reply_to.content[:100],
                'sender': obj.reply_to.sender.username if obj.reply_to.sender else 'Unknown'
            }
        return None

    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender_id == request.user.id
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages."""

    class Meta:
        model = Message
        fields = ('room', 'content', 'message_type', 'attachment', 'reply_to')

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message content cannot be empty.')
        return value.strip()


class RoomParticipantSerializer(serializers.ModelSerializer):
    """Serializer for room participants."""
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = RoomParticipant
        fields = ('user', 'role', 'joined_at', 'is_typing', 'is_muted')


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat rooms."""
    participants_info = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    display_avatar = serializers.SerializerMethodField()
    capabilities = serializers.ReadOnlyField()

    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'room_type', 'description', 'avatar',
            'participants_info', 'last_message', 'unread_count',
            'display_name', 'display_avatar', 'is_active',
            'created_at', 'updated_at', 'capabilities'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_participants_info(self, obj):
        participants = obj.room_participants.select_related('user').all()[:10]
        return RoomParticipantSerializer(participants, many=True).data

    def get_last_message(self, obj):
        request = self.context.get('request')
        message = obj.messages.visible_to(request.user if request else None).first()
        if message:
            return {
                'id': str(message.id),
                'content': message.content[:100] if not message.is_deleted else 'Message deleted',
                'sender': message.sender.username if message.sender else 'System',
                'created_at': message.created_at.isoformat(),
                'message_type': message.message_type
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0

    def get_display_name(self, obj):
        request = self.context.get('request')
        if obj.room_type == 'direct' and request and request.user:
            other = obj.get_other_participant(request.user)
            if other:
                return other.get_display_name()
        return obj.name or f"Group ({obj.participants.count()})"

    def get_display_avatar(self, obj):
        request = self.context.get('request')
        if obj.room_type == 'direct' and request and request.user:
            other = obj.get_other_participant(request.user)
            if other and other.avatar:
                return other.avatar.url
        if obj.avatar:
            return obj.avatar.url
        return None


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat rooms."""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = ChatRoom
        fields = ('name', 'room_type', 'description', 'participant_ids')

    def validate_participant_ids(self, value):
        if not value:
            raise serializers.ValidationError('At least one participant is required.')
        return value

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        user = self.context['request'].user

        # For direct messages, check if room already exists
        if validated_data.get('room_type') == 'direct' and len(participant_ids) == 1:
            other_user_id = participant_ids[0]
            existing_room = ChatRoom.objects.filter(
                room_type='direct',
                participants=user
            ).filter(
                participants=other_user_id
            ).first()

            if existing_room:
                return existing_room

        room = ChatRoom.objects.create(created_by=user, **validated_data)

        # Add creator as owner
        RoomParticipant.objects.create(room=room, user=user, role='owner')

        # Add other participants
        for participant_id in participant_ids:
            if participant_id != user.id:
                try:
                    participant = User.objects.get(id=participant_id)
                    RoomParticipant.objects.create(room=room, user=participant, role='member')
                except User.DoesNotExist:
                    pass

        return room


class ChatRoomDetailSerializer(ChatRoomSerializer):
    """Detailed serializer for single chat room view."""
    messages = serializers.SerializerMethodField()

    class Meta(ChatRoomSerializer.Meta):
        fields = ChatRoomSerializer.Meta.fields + ('messages',)

    def get_messages(self, obj):
        request = self.context.get('request')
        messages = obj.messages.visible_to(request.user if request else None).filter(is_deleted=False).select_related('sender')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data

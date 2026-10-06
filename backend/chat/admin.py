"""
Admin configuration for chat app.
"""
from django.contrib import admin
from .models import ChatRoom, RoomParticipant, Message, MessageRead


class RoomParticipantInline(admin.TabularInline):
    model = RoomParticipant
    extra = 0
    readonly_fields = ('joined_at', 'last_read_at')


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'room_type', 'is_active', 'created_by', 'created_at')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    inlines = [RoomParticipantInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'sender', 'short_content', 'message_type', 'is_deleted', 'created_at')
    list_filter = ('message_type', 'is_deleted', 'is_edited', 'created_at')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('created_at', 'edited_at')

    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Content'


@admin.register(RoomParticipant)
class RoomParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'role', 'is_typing', 'joined_at')
    list_filter = ('role', 'is_muted', 'joined_at')
    search_fields = ('user__username', 'room__name')


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'read_at')
    list_filter = ('read_at',)

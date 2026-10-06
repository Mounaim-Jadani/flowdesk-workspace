"""
URL patterns for chat app.
"""
from django.urls import path
from .views import (
    ChatRoomListView,
    ChatRoomDetailView,
    MessageListView,
    MessageDetailView,
    DirectMessageView,
    MarkAsReadView,
    TypingStatusView,
)

urlpatterns = [
    # Rooms
    path('rooms/', ChatRoomListView.as_view(), name='room_list'),
    path('rooms/<uuid:room_id>/', ChatRoomDetailView.as_view(), name='room_detail'),

    # Messages
    path('rooms/<uuid:room_id>/messages/', MessageListView.as_view(), name='message_list'),
    path('rooms/<uuid:room_id>/messages/<uuid:message_id>/', MessageDetailView.as_view(), name='message_detail'),

    # Actions
    path('direct/', DirectMessageView.as_view(), name='direct_message'),
    path('rooms/<uuid:room_id>/read/', MarkAsReadView.as_view(), name='mark_as_read'),
    path('rooms/<uuid:room_id>/typing/', TypingStatusView.as_view(), name='typing_status'),
]

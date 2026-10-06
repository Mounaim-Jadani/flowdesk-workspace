from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Notification


def serialize_notification(item):
    return {
        'id': str(item.id),
        'room_id': str(item.room_id) if item.room_id else None,
        'kind': item.kind,
        'payload': item.payload,
        'channel': item.channel,
        'is_read': item.is_read,
        'created_at': item.created_at.isoformat(),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    items = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    return Response([serialize_notification(item) for item in items])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    updated = Notification.objects.filter(
        id=notification_id, recipient=request.user, is_read=False,
    ).update(is_read=True)
    if not updated:
        return Response({'detail': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'status': 'read'})

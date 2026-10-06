import json
from django.http import JsonResponse
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from chat.models import ChatRoom, RoomParticipant
from .models import ActionItem
from .serializers import serialize_item
from notifications.services import notify

def check_room_permission(user, room_id):
    """Check if the user is a participant of the room."""
    return RoomParticipant.objects.filter(room_id=room_id, user=user).exists()

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_item(request):
    try:
        data = request.data
        room_id = data.get('room_id')
        description = data.get('description')
        
        if not room_id or not description:
            return JsonResponse({'error': 'Missing room_id or description'}, status=400)
            
        if not check_room_permission(request.user, room_id):
            return JsonResponse({'error': 'Forbidden'}, status=403)
            
        room = ChatRoom.objects.get(id=room_id)

        assignee_id = data.get('assignee_id') or None
        if assignee_id and not RoomParticipant.objects.filter(room=room, user_id=assignee_id).exists():
            return JsonResponse({'error': 'Assignee must be a member of the room.'}, status=400)

        source_message_id = data.get('message_id') or None
        if source_message_id and not room.messages.filter(id=source_message_id).exists():
            return JsonResponse({'error': 'Source message does not belong to the room.'}, status=400)
        
        item = ActionItem(
            room=room,
            created_by=request.user,
            description=description,
            source_message_id=source_message_id,
            assignee_id=assignee_id,
            due_at=data.get('due_at') or None,
        )
        item.save()
        
        serialized = serialize_item(item)
        
        # Broadcast via channel_layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{room.id}',
            {
                'type': 'checklist_event',
                'payload': {
                    'kind': 'item_created',
                    'item': serialized
                }
            }
        )
        
        # Notify if assignee is someone else
        if item.assignee and item.assignee != request.user:
            notify(
                recipient_id=item.assignee.id,
                kind='assignment',
                room=room,
                payload={
                    'item_id': str(item.id),
                    'description': item.description,
                    'actor_username': request.user.username,
                    'room_id': str(room.id)
                },
                respect_deep_work=True
            )
            
        return JsonResponse(serialized, status=201)
        
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_items(request, room_id):
    if not check_room_permission(request.user, room_id):
        return JsonResponse({'error': 'Forbidden'}, status=403)
        
    status_filter = request.GET.get('status')
    items = ActionItem.objects.filter(room_id=room_id)
    if status_filter:
        items = items.filter(status=status_filter)
        
    items = items.order_by('-created_at')
    return JsonResponse([serialize_item(item) for item in items], safe=False)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def patch_item(request, item_id):
    try:
        item = ActionItem.objects.get(id=item_id)
        
        if not check_room_permission(request.user, item.room_id):
            return JsonResponse({'error': 'Forbidden'}, status=403)

        if request.user != item.created_by and request.user != item.assignee:
            return JsonResponse({'error': 'Forbidden'}, status=403)
            
        data = request.data
        
        if 'description' in data:
            item.description = data['description']
        if 'due_at' in data:
            item.due_at = data['due_at']
            
        item.save()
        
        serialized = serialize_item(item)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{item.room_id}',
            {
                'type': 'relay_event',
                'payload': {
                    'type': 'checklist_event',
                    'kind': 'item_updated',
                    'item': serialized
                }
            }
        )
        
        return JsonResponse(serialized)
    except ActionItem.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_item_done(request, item_id):
    try:
        item = ActionItem.objects.get(id=item_id)
        
        if not check_room_permission(request.user, item.room_id):
            return JsonResponse({'error': 'Forbidden'}, status=403)

        if request.user != item.created_by and request.user != item.assignee:
            return JsonResponse({'error': 'Forbidden'}, status=403)
            
        item.status = 'done'
        item.completed_at = timezone.now()
        item.save()
        
        serialized = serialize_item(item)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{item.room_id}',
            {
                'type': 'relay_event',
                'payload': {
                    'type': 'checklist_event',
                    'kind': 'item_updated',
                    'item': serialized
                }
            }
        )
        
        return JsonResponse(serialized)
    except ActionItem.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def dismiss_item(request, item_id):
    try:
        item = ActionItem.objects.get(id=item_id)
        
        if not check_room_permission(request.user, item.room_id):
            return JsonResponse({'error': 'Forbidden'}, status=403)

        if request.user != item.created_by and request.user != item.assignee:
            return JsonResponse({'error': 'Forbidden'}, status=403)
            
        item.status = 'dismissed'
        item.save()
        
        serialized = serialize_item(item)
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{item.room_id}',
            {
                'type': 'relay_event',
                'payload': {
                    'type': 'checklist_event',
                    'kind': 'item_updated',
                    'item': serialized
                }
            }
        )
        
        return JsonResponse(serialized)
    except ActionItem.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

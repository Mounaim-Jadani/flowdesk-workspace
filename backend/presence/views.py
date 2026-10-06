from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.timezone import now
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import DeepWorkSession
from .utils import get_active_deep_work

class StartDeepWorkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        duration_minutes = request.data.get('duration_minutes')
        
        if duration_minutes not in [60, 120, 240, 0]:
            return Response({'error': 'Invalid duration.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already active
        existing_session = get_active_deep_work(request.user)
        if existing_session:
            return Response({'error': 'A deep work session is already active.'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate ends_at
        if duration_minutes == 0:
            ends_at = now() + timedelta(hours=24)
        else:
            ends_at = now() + timedelta(minutes=duration_minutes)

        session = DeepWorkSession.objects.create(
            user=request.user,
            ends_at=ends_at
        )

        # Broadcast via websocket
        async_to_sync(get_channel_layer().group_send)(
            'online_status',
            {
                'type': 'relay_event',
                'payload': {
                    'kind': 'deep_work',
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'active': True,
                    'ends_at': session.ends_at.isoformat()
                }
            }
        )

        return Response({'message': 'Deep work session started.', 'ends_at': session.ends_at.isoformat()}, status=status.HTTP_201_CREATED)


class StopDeepWorkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = get_active_deep_work(request.user)
        
        if not session:
            return Response({'error': 'No active deep work session found.'}, status=status.HTTP_400_BAD_REQUEST)

        session.ended_early = True
        session.is_completed = True
        session.save()

        # Broadcast via websocket
        async_to_sync(get_channel_layer().group_send)(
            'online_status',
            {
                'type': 'relay_event',
                'payload': {
                    'kind': 'deep_work',
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'active': False,
                    'ends_at': None
                }
            }
        )

        return Response({'message': 'Deep work session stopped.'}, status=status.HTTP_200_OK)

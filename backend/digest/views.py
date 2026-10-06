from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import django.utils.dateparse
from chat.models import ChatRoom, Message
from checklist.models import ActionItem
from digest.models import RoomDigest
from digest.generator import build_digest, SUMMARY_PROMPT_VERSION
from django.shortcuts import get_object_or_404
from django.db.models.functions import Coalesce


def _open_items_count(room, user):
    return ActionItem.objects.filter(
        room=room,
        assignee=user,
        status='open',
    ).count()

class DigestRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        force = request.query_params.get('force') == 'true'
        
        recent_digest = RoomDigest.objects.filter(
            room=room, 
            user=request.user, 
            consumed_at__isnull=True,
            generated_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-generated_at').first()
        
        lang_pref = request.query_params.get('lang_pref')
        cached_language = (recent_digest.stats or {}).get('summary_language') if recent_digest else None
        cached_model = (recent_digest.stats or {}).get('summary_model') if recent_digest else None
        cached_prompt_version = (recent_digest.stats or {}).get('summary_prompt_version') if recent_digest else None
        latest_unread_message = Message.objects.filter(room=room).exclude(
            sender=request.user
        ).visible_to(request.user).order_by('-created_at').first()
        digest_is_current = bool(
            recent_digest and (
                not latest_unread_message or latest_unread_message.created_at <= recent_digest.until
            )
        )
        if recent_digest and not force and digest_is_current and cached_prompt_version == SUMMARY_PROMPT_VERSION and cached_model not in {None, 'local-heuristic'} and (not lang_pref or cached_language == lang_pref):
            cached_stats = dict(recent_digest.stats or {})
            cached_stats['open_items'] = _open_items_count(room, request.user)
            return Response({
                'id': recent_digest.id,
                'since': recent_digest.since,
                'until': recent_digest.until,
                'summary': recent_digest.summary,
                'key_points': recent_digest.key_points,
                'mentions': recent_digest.mentions,
                'stats': cached_stats,
                'summary_language': (recent_digest.stats or {}).get('summary_language'),
            })
            
        if recent_digest:
            since = recent_digest.since
        else:
            unread_count = room.get_unread_count(request.user)
            min_unread = getattr(settings, 'DIGEST_MIN_UNREAD', 8)
            if unread_count < min_unread:
                return Response(status=status.HTTP_204_NO_CONTENT)
                
            since_param = request.query_params.get('since')
            if since_param:
                since = django.utils.dateparse.parse_datetime(since_param)
            else:
                participant = room.room_participants.filter(user=request.user).first()
                if participant and participant.last_read_at:
                    since = participant.last_read_at
                else:
                    since = timezone.now() - timedelta(days=7)
                    
        until = timezone.now()
            
        messages = Message.objects.filter(room=room).exclude(sender=request.user).visible_to(request.user).annotate(
            available_at=Coalesce('visible_from', 'created_at')
        ).filter(available_at__gte=since, available_at__lte=until).order_by('available_at')
        
        messages_dicts = []
        for m in messages:
            messages_dicts.append({
                'id': str(m.id),
                'content': m.content,
                'created_at': m.available_at.isoformat(),
                'sender_username': m.sender.username if m.sender else '',
                'reply_to_id': str(m.reply_to_id) if hasattr(m, 'reply_to_id') and m.reply_to_id else None,
                'is_urgent': getattr(m, 'is_urgent', False)
            })
            
        me_dict = {'username': request.user.username}
        digest_data = build_digest(
            messages_dicts,
            me_dict,
            since,
            until,
            lang_pref=lang_pref,
            use_ai=True,
            chat_type=room.room_type,
        )
        digest_data.setdefault('stats', {})['open_items'] = _open_items_count(room, request.user)
        
        room_digest, created = RoomDigest.objects.update_or_create(
            room=room,
            user=request.user,
            since=since,
            defaults={
                'until': until,
                'summary': digest_data.get('summary', ''),
                'key_points': digest_data.get('key_points', []),
                'mentions': digest_data.get('mentions', []),
                'stats': digest_data.get('stats', {})
            }
        )
        
        return Response({
            'id': room_digest.id,
            'since': room_digest.since,
            'until': room_digest.until,
            'summary': room_digest.summary,
            'key_points': room_digest.key_points,
            'mentions': room_digest.mentions,
            'stats': room_digest.stats,
            'summary_language': (room_digest.stats or {}).get('summary_language'),
        })


class DigestConsumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
        digest = RoomDigest.objects.filter(room=room, user=request.user, consumed_at__isnull=True).order_by('-generated_at').first()
        if digest:
            digest.consumed_at = timezone.now()
            digest.save()
            return Response({'status': 'consumed'})
        return Response({'status': 'no unconsumed digest found'}, status=status.HTTP_404_NOT_FOUND)

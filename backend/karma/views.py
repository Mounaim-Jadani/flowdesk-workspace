from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import ChatRoom
from .badges import award_monthly_top_contributors
from .models import Badge, KarmaEvent
from .rules import KARMA_GLOBAL_KEY, KARMA_MONTHLY_KEY_PREFIX, get_karma_redis

User = get_user_model()


def badge_data(user_id):
    return list(Badge.objects.filter(user_id=user_id).values('kind', 'period_key', 'awarded_at'))


def event_data(event):
    return {
        'id': str(event.id),
        'kind': event.kind,
        'score': event.score,
        'room_id': str(event.room_id) if event.room_id else None,
        'metadata': event.metadata,
        'created_at': event.created_at,
    }


class MyKarmaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        client = get_karma_redis()
        month_key = f'{KARMA_MONTHLY_KEY_PREFIX}{timezone.now():%Y-%m}'
        total = int(float(client.zscore(KARMA_GLOBAL_KEY, str(request.user.id)) or 0))
        monthly = int(float(client.zscore(month_key, str(request.user.id)) or 0))
        if total == 0:
            total = KarmaEvent.objects.filter(user=request.user).aggregate(total=Sum('score'))['total'] or 0
        if monthly == 0:
            monthly = KarmaEvent.objects.filter(user=request.user, created_at__year=timezone.now().year, created_at__month=timezone.now().month).aggregate(total=Sum('score'))['total'] or 0
        room_id = request.query_params.get('room_id')
        if room_id:
            room = get_object_or_404(ChatRoom.objects.filter(participants=request.user), id=room_id)
            room_scores = (
                KarmaEvent.objects.filter(room=room)
                .values('user_id')
                .annotate(score=Sum('score'))
                .order_by('-score', 'user__username')
            )
            rank = next(
                (index + 1 for index, row in enumerate(room_scores) if row['user_id'] == request.user.id),
                None,
            )
        else:
            rank = client.zrevrank(month_key, str(request.user.id))
            rank = rank + 1 if rank is not None else None
        return Response({
            'total': total,
            'monthly': monthly,
            'rank': rank,
            'badges': badge_data(request.user.id),
            'recent_events': [event_data(event) for event in KarmaEvent.objects.filter(user=request.user)[:20]],
        })


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        award_monthly_top_contributors()
        scope = request.query_params.get('scope', 'month')
        room_id = request.query_params.get('room_id')
        if room_id:
            room = get_object_or_404(ChatRoom.objects.filter(participants=request.user), id=room_id)
            rows = (
                KarmaEvent.objects.filter(room=room)
                .values('user_id', 'user__username')
                .annotate(score=Sum('score'))
                .order_by('-score', 'user__username')[:10]
            )
            return Response([{
                'user_id': row['user_id'], 'username': row['user__username'], 'score': row['score'],
                'badges': [badge['kind'] for badge in badge_data(row['user_id'])],
            } for row in rows])

        key = KARMA_GLOBAL_KEY if scope == 'global' else f'{KARMA_MONTHLY_KEY_PREFIX}{timezone.now():%Y-%m}'
        entries = get_karma_redis().zrevrange(key, 0, 9, withscores=True)
        user_ids = [int(user_id) for user_id, _ in entries]
        users = {user.id: user for user in User.objects.filter(id__in=user_ids)}
        return Response([{
            'user_id': user_id,
            'username': users[user_id].username,
            'score': int(float(score)),
            'badges': [badge['kind'] for badge in badge_data(user_id)],
        } for user_id, score in entries if user_id and int(user_id) in users])

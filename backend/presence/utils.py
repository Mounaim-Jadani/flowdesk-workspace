from django.utils.timezone import now
from .models import DeepWorkSession

def get_active_deep_work(user):
    return DeepWorkSession.objects.filter(
        user=user, 
        ends_at__gt=now(), 
        ended_early=False
    ).first()

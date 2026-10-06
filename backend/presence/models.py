from django.db import models
from django.conf import settings

class DeepWorkSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='deep_work_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField()
    ended_early = models.BooleanField(default=False)
    notifications_deferred = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)

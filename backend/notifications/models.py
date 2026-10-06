import uuid
from django.db import models
from django.conf import settings

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    room = models.ForeignKey('chat.ChatRoom', on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=32)   # 'mention', 'assignment', 'decision', etc.
    payload = models.JSONField(default=dict)
    channel = models.CharField(max_length=16, default='push', choices=[('push','push'),('batch','batch'),('silent','silent')])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', '-created_at'])]

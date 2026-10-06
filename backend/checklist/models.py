import uuid
from django.db import models
from django.conf import settings

class ActionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('chat.ChatRoom', on_delete=models.CASCADE,
        related_name='action_items')
    source_message = models.ForeignKey('chat.Message', on_delete=models.CASCADE,
        related_name='action_items', null=True, blank=True)
    description = models.CharField(max_length=280)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='assigned_items', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_items')
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16,
        choices=[('open','open'),('done','done'),('dismissed','dismissed')],
        default='open')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room', 'status']),
            models.Index(fields=['assignee', 'status'])
        ]

from django.db import models
from django.conf import settings

class RoomDigest(models.Model):
    room = models.ForeignKey('chat.ChatRoom', on_delete=models.CASCADE, related_name='digests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='digests')
    since = models.DateTimeField()   # début de la fenêtre
    until = models.DateTimeField()
    summary = models.TextField(default='', blank=True)  # Résumé narratif généré par l'IA
    key_points = models.JSONField(default=list)
    mentions = models.JSONField(default=list)
    stats = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('room', 'user', 'since')]  # Garantit 1 digest par fenêtre par user

import uuid

from django.conf import settings
from django.db import models


class KarmaEvent(models.Model):
    """Durable audit entry for every awarded Karma event."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='karma_events',
    )
    kind = models.CharField(max_length=32)
    score = models.PositiveIntegerField()
    source_key = models.CharField(max_length=200, unique=True, null=True, blank=True)
    room = models.ForeignKey(
        'chat.ChatRoom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='karma_events',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['kind', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.kind} (+{self.score})'


class Badge(models.Model):
    """An idempotently awarded Karma badge."""

    BADGE_KINDS = (
        ('problem_solver', 'Résolveur de problèmes'),
        ('reliable_partner', 'Partenaire fiable'),
        ('mentor', 'Mentor'),
        ('pillar', 'Pilier de l’équipe'),
        ('top_contributor', 'Top Contributeur'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='karma_badges',
    )
    kind = models.CharField(max_length=32, choices=BADGE_KINDS)
    period_key = models.CharField(max_length=16, null=True, blank=True)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-awarded_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'kind', 'period_key'], name='unique_karma_badge_per_user_period'),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.kind}'

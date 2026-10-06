import time
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.db import transaction
from presence.models import DeepWorkSession
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class Command(BaseCommand):
    help = 'Expires Deep Work sessions that have passed their ends_at time'

    def handle(self, *args, **options):
        # Chercher toutes les sessions Deep Work expirées non complétées
        expired_sessions = DeepWorkSession.objects.filter(
            ends_at__lt=now(),
            is_completed=False,
        )

        count = expired_sessions.count()
        if count > 0:
            channel_layer = get_channel_layer()
            for session in expired_sessions:
                # On utilise transaction.atomic() pour garantir l'update
                with transaction.atomic():
                    # Mettre à jour l'état de la session
                    session.is_completed = True
                    session.save(update_fields=['is_completed'])
                    
                    # On diffuse l'événement à tout le monde
                    async_to_sync(channel_layer.group_send)(
                        'online_status',
                        {
                            'type': 'relay_event',
                            'payload': {
                                'kind': 'deep_work_ended',
                                'user_id': session.user.id
                            }
                        }
                    )
            
            self.stdout.write(self.style.SUCCESS(f'Successfully expired {count} Deep Work session(s)'))

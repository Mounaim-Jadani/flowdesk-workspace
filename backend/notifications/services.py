from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import F
from presence.utils import get_active_deep_work
from .models import Notification

def notify(recipient_id, room, kind, payload, default_channel='push', respect_deep_work=True):
    # 1. Écrit en base
    notif = Notification.objects.create(recipient_id=recipient_id, room=room, kind=kind, payload=payload, channel=default_channel)
    
    # Logique du compteur (EPIC 3 - 3.1.7)
    # Placée JUSTE AVANT le websocket group_send comme demandé
    if respect_deep_work:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(id=recipient_id).first()
        if user:
            session = get_active_deep_work(user)
            if session:
                # Utilisation de F() pour incrémenter atomiquement
                session.notifications_deferred = F('notifications_deferred') + 1
                session.save(update_fields=['notifications_deferred'])

    # 2. Pousse via le canal personnel
    # Le serveur ne bloque JAMAIS la livraison. Le routeur frontend masque le toast si besoin.
    async_to_sync(get_channel_layer().group_send)(
        f'user_{recipient_id}',
        {'type': 'relay_event', 'payload': {'kind': 'notification', 'notification_kind': kind, 'id': str(notif.id), 'payload': payload}}
    )
    return notif

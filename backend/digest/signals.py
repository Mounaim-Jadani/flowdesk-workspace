import threading
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


# @receiver(post_save, sender='chat.Message')
def precompute_digest_on_message(sender, instance, created, **kwargs):
    """
    DÉSACTIVÉ : Le client a préféré revenir à la méthode "à la demande" 
    pour éviter les erreurs de quota (Rate Limit) de l'API Gemini.
    """
    return
    
    room = instance.room
    min_unread = getattr(settings, 'DIGEST_MIN_UNREAD', 8)
    
    # Vérifier chaque participant de la room
    from chat.models import RoomParticipant
    participants = RoomParticipant.objects.filter(room=room).exclude(user=instance.sender)
    
    for participant in participants:
        unread_count = room.get_unread_count(participant.user)
        if unread_count > min_unread:
            # Lancer la génération en arrière-plan (thread)
            t = threading.Thread(
                target=_generate_digest_background,
                args=(room.id, participant.user.id),
                daemon=True
            )
            t.start()


def _generate_digest_background(room_id, user_id):
    """Génère le digest en arrière-plan et le stocke en base."""
    from django.core.cache import cache
    
    # 1. Vérifier si une génération est déjà en cours ou en cooldown (anti-spam API)
    cache_key = f"digest_generating_{room_id}_{user_id}"
    error_cooldown_key = f"digest_error_cooldown_{room_id}_{user_id}"
    
    if cache.get(cache_key) or cache.get(error_cooldown_key):
        return
        
    # Verrouiller pour max 60 secondes
    cache.set(cache_key, True, timeout=60)
    
    try:
        from django.contrib.auth import get_user_model
        from chat.models import ChatRoom, Message, RoomParticipant
        from digest.models import RoomDigest
        from digest.generator import build_digest
        from django.utils import timezone
        from datetime import timedelta

        User = get_user_model()
        user = User.objects.get(id=user_id)
        room = ChatRoom.objects.get(id=room_id)
        
        participant = RoomParticipant.objects.get(room=room, user=user)
        since = participant.last_read_at or (timezone.now() - timedelta(days=7))
        until = timezone.now()
        
        # Vérifier s'il y a déjà un digest récent non consommé
        existing = RoomDigest.objects.filter(
            room=room, user=user,
            consumed_at__isnull=True,
            generated_at__gte=timezone.now() - timedelta(hours=24)
        ).first()
        
        if existing and existing.summary and existing.summary != "Résumé non disponible. L'IA n'a pas pu être contactée.":
            return  # Déjà un bon résumé en cache
        
        messages = Message.objects.filter(
            room=room, created_at__gte=since, created_at__lte=until
        ).order_by('created_at')
        
        messages_dicts = [{
            'id': str(m.id),
            'content': m.content,
            'created_at': m.created_at.isoformat(),
            'sender_username': m.sender.username if m.sender else '',
        } for m in messages]
        
        me_dict = {'username': user.username}
        digest_data = build_digest(messages_dicts, me_dict, since, until)
        
        RoomDigest.objects.update_or_create(
            room=room, user=user, since=since,
            defaults={
                'until': until,
                'summary': digest_data.get('summary', ''),
                'key_points': digest_data.get('key_points', []),
                'mentions': digest_data.get('mentions', []),
                'stats': digest_data.get('stats', {}),
            }
        )
    except Exception as e:
        print(f"[digest signal] Erreur pré-génération: {e}")
        # En cas d'erreur (ex: quota dépassé), on met en pause les appels pendant 60 secondes
        cache.set(error_cooldown_key, True, timeout=60)
    finally:
        # Libérer le verrou principal
        cache.delete(cache_key)

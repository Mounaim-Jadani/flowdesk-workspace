import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from chat.models import ChatRoom, RoomParticipant, Message
from digest.models import RoomDigest

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with initial development data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flood',
            action='store_true',
            help='Add a deterministic batch of messages for Catch-Me-Up testing.',
        )
        parser.add_argument(
            '--flood-count',
            type=int,
            default=42,
            help='Number of Catch-Me-Up flood messages to ensure (default: 42).',
        )
        parser.add_argument(
            '--private-catchup',
            action='store_true',
            help='Create eight unread French messages from Alice to Bob in their private chat.',
        )

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting seed process...')

        # 1. Create Users
        users_data = ['alice', 'bob', 'marie', 'karim']
        users = {}
        for username in users_data:
            user, created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
            if created:
                user.set_password('devpass123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
            users[username] = user

        # 2. Create Group Room
        group_room_name = "Équipe Produit"
        group_room, created = ChatRoom.objects.get_or_create(
            name=group_room_name,
            room_type='group',
            defaults={'description': "Room pour l'équipe produit", 'created_by': users['alice']}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created group room: {group_room_name}'))
            # Add all users to group room
            for username, user in users.items():
                RoomParticipant.objects.get_or_create(
                    room=group_room,
                    user=user,
                    defaults={'role': 'owner' if username == 'alice' else 'member'}
                )
            
            # Create messages in group room
            Message.objects.create(
                room=group_room,
                sender=users['alice'],
                content="Bonjour l'équipe ! Bienvenue sur notre nouveau chat.",
                message_type='text'
            )
            Message.objects.create(
                room=group_room,
                sender=users['bob'],
                content="Salut Alice, merci !",
                message_type='text'
            )
        else:
            self.stdout.write(f'Group room {group_room_name} already exists')

        if kwargs.get('flood'):
            flood_count = max(1, kwargs.get('flood_count', 42))
            marker = '[seed flood]'
            existing_flood_count = Message.objects.filter(
                room=group_room,
                content__startswith=marker,
            ).count()
            users_cycle = [users['alice'], users['bob'], users['marie'], users['karim']]
            for index in range(existing_flood_count, flood_count):
                sender = users_cycle[index % len(users_cycle)]
                Message.objects.create(
                    room=group_room,
                    sender=sender,
                    content=f'{marker} Message {index + 1}: point de suivi du projet.',
                    message_type='text',
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Catch-Me-Up flood ready: {max(existing_flood_count, flood_count)} messages.'
                )
            )

        # 3. Create Direct Message Room
        dm_room = ChatRoom.objects.filter(
            room_type='direct',
            room_participants__user=users['alice']
        ).filter(
            room_participants__user=users['bob']
        ).first()

        if not dm_room:
            dm_room = ChatRoom.objects.create(
                room_type='direct',
                created_by=users['alice']
            )
            RoomParticipant.objects.create(room=dm_room, user=users['alice'], role='member')
            RoomParticipant.objects.create(room=dm_room, user=users['bob'], role='member')
            self.stdout.write(self.style.SUCCESS('Created DM room between alice and bob'))

            # Create messages in DM
            Message.objects.create(
                room=dm_room,
                sender=users['alice'],
                content="Salut Bob, tu as pu regarder le dernier ticket ?",
                message_type='text'
            )
            Message.objects.create(
                room=dm_room,
                sender=users['bob'],
                content="Oui, je m'en occupe cet après-midi.",
                message_type='text'
            )
        else:
            self.stdout.write('DM room between alice and bob already exists')

        if kwargs.get('private_catchup'):
            private_messages = [
                "Je prépare mon mariage pour le mois de juin.",
                "Je veux organiser la cérémonie à Casablanca.",
                "La salle peut accueillir environ 120 invités.",
                "La salle doit encore confirmer sa disponibilité.",
                "Je dois vérifier le budget avec ma famille.",
                "Je dois aussi choisir le traiteur et le photographe.",
                "Je veux préparer les invitations cette semaine.",
                "La prochaine étape est de confirmer la salle et le budget avant vendredi.",
            ]
            bob_participant = RoomParticipant.objects.get(room=dm_room, user=users['bob'])
            # Reset only this deterministic scenario, then place Bob's read
            # cursor immediately before its eight newly-created messages.
            Message.objects.filter(
                room=dm_room, sender=users['alice'], content__in=private_messages
            ).delete()
            RoomDigest.objects.filter(room=dm_room, user=users['bob']).delete()
            bob_participant.last_read_at = timezone.now()
            bob_participant.save(update_fields=['last_read_at'])
            for content in private_messages:
                Message.objects.create(room=dm_room, sender=users['alice'], content=content, message_type='text')
            self.stdout.write(self.style.SUCCESS('Private Catch-Me-Up ready: 8 unread messages from alice to bob.'))

        self.stdout.write(self.style.SUCCESS('Seed process completed!'))

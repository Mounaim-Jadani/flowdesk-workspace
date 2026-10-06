from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Worker pour la pré-agrégation de digests en tâche de fond.'

    def handle(self, *args, **kwargs):
        # TODO v2
        # Si le budget serveur est serré, la génération à la demande (API)
        # suffit pour la démo car les requêtes sont indexées et
        # la fenêtre typique est < 500 messages.
        self.stdout.write(self.style.SUCCESS("Worker running... (TODO v2)"))

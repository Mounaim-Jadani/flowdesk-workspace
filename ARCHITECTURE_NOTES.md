### a) Types d'événements WS gérés dans le dictionnaire `handlers` du `ChatConsumer`
- `message`
- `typing`
- `read`
- `edit`
- `delete`

### b) Types d'événements traités dans la fonction `handleMessage()` du `wsService` (frontend)
- `message`
- `typing`
- `edit`
- `delete`
- `user_join`
- `user_leave`
- `read`

### c) Liste exacte et complète des champs pour les modèles de base

**Modèle `ChatRoom`**
- `id` (UUIDField, clé primaire)
- `name` (CharField)
- `room_type` (CharField)
- `description` (TextField)
- `avatar` (ImageField)
- `participants` (ManyToManyField vers User)
- `is_active` (BooleanField)
- `created_by` (ForeignKey vers User)
- `created_at` (DateTimeField)
- `updated_at` (DateTimeField)

**Modèle `RoomParticipant`**
- `id` (AutoField / BigAutoField, clé primaire implicite)
- `room` (ForeignKey vers ChatRoom)
- `user` (ForeignKey vers User)
- `role` (CharField)
- `joined_at` (DateTimeField)
- `last_read_at` (DateTimeField)
- `is_muted` (BooleanField)
- `is_typing` (BooleanField)
- `typing_started_at` (DateTimeField)

**Modèle `Message`**
- `id` (UUIDField, clé primaire)
- `room` (ForeignKey vers ChatRoom)
- `sender` (ForeignKey vers User)
- `content` (TextField)
- `message_type` (CharField)
- `attachment` (FileField)
- `reply_to` (ForeignKey vers Message)
- `is_edited` (BooleanField)
- `edited_at` (DateTimeField)
- `is_deleted` (BooleanField)
- `created_at` (DateTimeField)

audit OK, pas de bug

### d) Gestion de la présence et Deep Work
- Le store `onlineUsers` a été extrait de `chatStore.ts` pour être géré exclusivement par `presenceStore.ts`.
- Raison : Éviter une double source de vérité. `presenceStore.ts` devient l'unique point de référence pour le statut de présence global, incluant l'état de connexion (`online`) et l'état de concentration (`deepWork`).

### e) Filtre de notifications (Couche de politesse)
- Le fichier `notificationRouter.ts` agit comme une couche d'interception entre la réception des événements WS (dans `websocket.ts` et `App.tsx`) et l'affichage des alertes visuelles (`toast`).
- Règle métier : Si l'utilisateur est en mode Deep Work et reçoit un message/notification d'une room non-active, l'alerte visuelle (toast) est bloquée (`deferred`). Cependant, l'incrémentation du compteur "non-lu" (pastille rouge dans la Sidebar via `chatStore`) s'effectue TOUJOURS.

### f) Fin de session Deep Work (Worker)
- Le service Docker `presence_worker` tourne en arrière-plan et exécute `expire_deep_work` ainsi que `deliver_scheduled_messages` toutes les 5 secondes.
- Ce worker bascule `is_completed=True` pour les sessions expirées, déclenche `deep_work_ended` sur le groupe global `online_status` et publie les messages programmés arrivés à échéance.

### g) État EPIC 5.1.5 — Catch-Me-Up
- Le digest est déclenché lors de l'ouverture d'une room par `chatStore.setActiveRoom()` lorsque le compteur de messages non lus dépasse le seuil backend.
- Le rendu est assuré par `frontend/src/components/chat/CatchUpBanner.tsx`, sous l'en-tête de conversation et derrière la capacité `catch_me_up`.
- Le bandeau est replié par défaut, peut afficher jusqu'à six points clés et quatre mentions, et utilise `data-message-id` avec `messageNavigation.ts` pour centrer le message source dans le fil.
- Le texte de synthèse s'adapte aux rooms directes et aux groupes. Les statistiques facultatives (`decisions_count`, `open_items`) sont rendues uniquement lorsqu'elles sont fournies.
- La sous-tâche 5.1.6 (interopérabilité avec les Action Items) n'est pas commencée : l'affichage de `open_items` existe, mais aucune navigation automatique vers la checklist n'est encore branchée.

### h) Corrections appliquées après audit avant 5.1.5
- La configuration charge `.env` avec `python-dotenv` avant la sélection des settings ; les variables injectées par Docker restent prioritaires.
- PostgreSQL utilise `DJANGO_SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` et `DB_PORT` depuis l'environnement. Les secrets ne sont pas exposés au frontend.
- Le champ `Message.visible_from` permet de programmer un message dans un DM pendant le Deep Work du destinataire. Le backend filtre les messages REST futurs et le frontend les garde en attente jusqu'à l'heure prévue.
- Une notification d'assignation pose un marqueur de session ; le bandeau checklist d'un DM s'ouvre automatiquement après navigation vers la room. Dans un groupe, le panneau Actions est déjà rendu dans la fenêtre.
- Les captures baseline WebSocket et la validation manuelle multi-fenêtres sont volontairement ignorées selon la décision projet ; elles ne bloquent pas l'avancement.

### i) Catch-Me-Up IA et actions de groupe
- Catch-Me-Up se déclenche automatiquement à partir de 8 messages non lus, avant le marquage de la room comme lue.
- Le backend utilise Groq uniquement depuis `backend/.env`, avec détection de la langue des messages par défaut et choix utilisateur persistant dans le navigateur (`flowdesk-digest-language`). Le routage utilise `allam-2-7b` puis `qwen/qwen3.8-27b` pour arabe/darija ; pour français/anglais, il utilise les quatre modèles `openai/gpt-oss-120b`, `allam-2-7b`, `openai/gpt-oss-20b`, puis `qwen/qwen3.8-27b` comme dernier fallback.
- Le prompt IA demande une synthèse globale par sujets en 2 à 4 phrases, jamais un résumé message par message, puis sépare les points importants. Un fallback local global est utilisé si l'API est indisponible.
- Le panneau Actions des groupes possède maintenant le bouton `+ Ajouter` pour créer une action, choisir un membre et une échéance. Les demandes comme `Bob, peux-tu vérifier l'API avant demain ?` et les engagements à la première personne sont détectés automatiquement.
- Le format Catch-Me-Up `speaker-voice-v3` respecte le point de vue des expéditeurs : en DM, aucun nom n'est ajouté et le résumé reste en `Je/Tu/Nous` ; en groupe, chaque ligne commence par `Nom :` et conserve les directives directes. Les sorties narratives en discours indirect sont rejetées avant affichage.
- La commande `seed_dev --private-catchup` recrée un scénario déterministe avec exactement 8 messages français non lus d'Alice vers Bob et supprime son ancien digest pour forcer une nouvelle génération.
- Les notifications persistées disposent des endpoints `GET /api/notifications/` et `POST /api/notifications/{id}/read/`; le frontend les recharge après connexion et les marque lues côté serveur.
- Les corrections de stabilisation avant 5.1.5 sécurisent l'édition/suppression WebSocket par room, valident l'appartenance des assignés, synchronisent les updates checklist REST via `relay_event`, protègent les engagements sans échéance et invalident un digest quand de nouveaux messages non lus sont arrivés.

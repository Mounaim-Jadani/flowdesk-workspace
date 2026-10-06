# Real-Time Chat Application

![Fork enrichi — FlowDesk](https://img.shields.io/badge/Fork_enrichi-FlowDesk-blue)

A production-ready, full-stack real-time chat application built with Django, Django Channels, React, and TypeScript.

## Features

- **Real-time messaging** - Instant message delivery using WebSockets
- **JWT Authentication** - Secure authentication with access and refresh tokens
- **Typing indicators** - See when others are typing in real-time
- **Online/Offline status** - Track user presence
- **Message history** - Persistent message storage with pagination
- **Direct messages** - One-on-one conversations
- **Group chats** - Multi-user chat rooms
- **Read receipts** - Know when messages are read
- **Message editing/deletion** - Edit or delete your messages
- **Reply to messages** - Quote and reply to specific messages
- **Responsive design** - Works on desktop and mobile

## Tech Stack

### Backend
- **Django 5.0** - Web framework
- **Django Channels** - WebSocket support
- **Django REST Framework** - REST API
- **Simple JWT** - JWT authentication
- **PostgreSQL** - Primary database
- **Redis** - WebSocket channel layer & caching
- **Daphne** - ASGI server

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Zustand** - State management
- **React Hook Form** - Form handling
- **Zod** - Schema validation

### DevOps
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy
- **GitHub Actions** - CI/CD (optional)

## Project Structure

```
Real-Time-Chat-App/
├── backend/
│   ├── accounts/           # User authentication & profiles
│   ├── chat/               # Chat functionality & WebSockets
│   ├── chat_project/       # Django project settings
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # API client & services
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── stores/         # Zustand stores
│   │   ├── services/       # WebSocket service
│   │   └── types/          # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── nginx/                  # Nginx configuration
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- Redis (for local development)

### Using Docker (Recommended)

1. **Clone the repository**
```bash
git clone <repository-url>
cd Real-Time-Chat-App
```

2. **Create environment file**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start the application**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/

### Local Development

#### Backend Setup

1. **Create virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Run migrations**
```bash
python manage.py migrate
```

5. **Create superuser**
```bash
python manage.py createsuperuser
```

6. **Start Redis** (required for WebSockets)
```bash
redis-server
```

7. **Load development data** (optional)
```bash
python manage.py seed_dev
# Add 42 messages to the demo group for Catch-Me-Up validation:
python manage.py seed_dev --flood
# Prepare exactly 8 unread private Catch-Me-Up messages from Alice to Bob:
python manage.py seed_dev --private-catchup
```

8. **Run development server**
```bash
python manage.py runserver
# or with Daphne for WebSockets:
daphne -b 0.0.0.0 -p 8000 chat_project.asgi:application
```

#### Frontend Setup

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Set up environment**
```bash
cp .env.example .env
```

3. **Start development server**
```bash
npm run dev
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login user |
| POST | `/api/auth/logout/` | Logout user |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/profile/` | Get user profile |
| PATCH | `/api/auth/profile/` | Update profile |
| POST | `/api/auth/password/change/` | Change password |
| GET | `/api/auth/users/` | Search users |
| GET | `/api/auth/users/online/` | Get online users |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/rooms/` | List chat rooms |
| POST | `/api/chat/rooms/` | Create chat room |
| GET | `/api/chat/rooms/{id}/` | Get room details |
| DELETE | `/api/chat/rooms/{id}/` | Leave/delete room |
| GET | `/api/chat/rooms/{id}/messages/` | Get messages |
| POST | `/api/chat/rooms/{id}/messages/` | Send message |
| PATCH | `/api/chat/rooms/{id}/messages/{mid}/` | Edit message |
| DELETE | `/api/chat/rooms/{id}/messages/{mid}/` | Delete message |
| POST | `/api/chat/direct/` | Create direct message |
| POST | `/api/chat/rooms/{id}/read/` | Mark as read |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | Load the current user's notifications |
| POST | `/api/notifications/{id}/read/` | Mark a notification as read |

## WebSocket Events

### Client to Server
```javascript
// Send message
{ type: 'message', content: 'Hello!', reply_to: null }

// Typing indicator
{ type: 'typing', is_typing: true }

// Mark as read
{ type: 'read' }

// Edit message
{ type: 'edit', message_id: 'uuid', content: 'Updated content' }

// Delete message
{ type: 'delete', message_id: 'uuid' }
```

### Server to Client
```javascript
// New message
{ type: 'message', message: { id, sender, content, created_at, ... } }

// Typing indicator
{ type: 'typing', user_id: 1, username: 'john', is_typing: true }

// Read receipt
{ type: 'read', user_id: 1, username: 'john', read_at: 'ISO-date' }

// Message edited
{ type: 'edit', message: { id, content, is_edited: true, ... } }

// Message deleted
{ type: 'delete', message_id: 'uuid' }

// User status
{ type: 'status', user_id: 1, username: 'john', is_online: true }
```

## Environment Variables

### Backend
| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_ENV` | Environment (development/production) | development |
| `DJANGO_SECRET_KEY` | Secret key for Django | - |
| `DB_NAME` | PostgreSQL database name | chat_db |
| `DB_USER` | PostgreSQL username | chat_user |
| `DB_PASSWORD` | PostgreSQL password | - |
| `DB_HOST` | PostgreSQL host | localhost |
| `REDIS_HOST` | Redis host | localhost |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | localhost |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | - |

### Frontend
| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | /api |
| `VITE_WS_HOST` | WebSocket host | localhost:8000 |

## Production Deployment

### Using Docker Compose with Nginx

```bash
# Start all services including Nginx
docker-compose --profile production up -d
```

### Security Checklist
- [ ] Set strong `DJANGO_SECRET_KEY`
- [ ] Use strong database passwords
- [ ] Enable HTTPS with SSL certificates
- [ ] Set appropriate `ALLOWED_HOSTS`
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy

## Implemented product modules
- Deep Work with deferred notifications
- Action Items and group checklist
- Catch-Me-Up summaries from 8 unread messages
- Groq multilingual summaries with model fallback

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Type Checking
```bash
cd frontend
npm run type-check
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue in the repository.

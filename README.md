# MetaFrazo - Video Translation & Text Removal Platform

A professional SaaS platform for AI-powered video translation featuring lip-sync dubbing and text removal. Built with FastAPI, React, and integrated with Sync.so and GhostCut APIs.

**Live Demo**: https://frontend-production-b02b.up.railway.app

## Features

### Video Processing
- **Video Editor**: Lip-sync audio dubbing + text/watermark removal
- **Pro Video Editor**: Advanced segment-based lip-sync with timeline control
- **Text Removal**: AI-powered detection and removal of subtitles, watermarks, and overlays
- **Multi-language Support**: Audio translation with natural lip synchronization

### Platform Features
- **User Authentication**: JWT-based login with secure token refresh
- **Credit System**: Usage-based billing with subscription tiers
- **Job Management**: Track processing history, download results, manage jobs
- **Real-time Updates**: WebSocket integration for live progress tracking
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React Frontend │───▶│  FastAPI Backend │───▶│  Celery Workers │
│  (Material-UI)  │    │   (REST API)     │    │  (Background)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                    ┌─────────┴─────────┐              │
                    ▼                   ▼              ▼
             ┌───────────┐       ┌───────────┐  ┌─────────────┐
             │ PostgreSQL│       │   Redis   │  │External APIs│
             │ (Database)│       │ (Cache/MQ)│  │Sync.so/GhostCut│
             └───────────┘       └───────────┘  └─────────────┘
                                                       │
                                                       ▼
                                                ┌───────────┐
                                                │  AWS S3   │
                                                │ (Storage) │
                                                └───────────┘
```

## Tech Stack

### Backend
- **FastAPI 0.104.1** - Modern async Python web framework
- **SQLAlchemy 2.0** - Database ORM with PostgreSQL
- **Celery 5.3** - Distributed task queue for background processing
- **Redis 7** - Caching and message broker
- **JWT Authentication** - Secure token-based auth with refresh tokens
- **Pydantic** - Data validation and settings management

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type-safe development
- **Material-UI 5** - Component library
- **React Query** - Server state management
- **React Router 6** - Client-side routing
- **Zustand** - State management
- **Socket.IO** - Real-time communication

### Infrastructure
- **Railway** - Cloud deployment platform
- **PostgreSQL 15** - Primary database
- **Redis 7** - Cache and Celery broker
- **AWS S3** - Video file storage
- **Docker** - Containerization

### External APIs
- **Sync.so** - AI lip-sync audio dubbing
- **GhostCut/Zhaoli** - Text detection and removal

## Project Structure

```
├── backend/
│   ├── api/
│   │   ├── routes/           # API endpoint modules
│   │   │   ├── auth/         # Authentication endpoints
│   │   │   ├── jobs/         # Job management
│   │   │   ├── video_editors/# Video processing APIs
│   │   │   └── upload/       # File upload handling
│   │   ├── main.py           # FastAPI application
│   │   └── websocket.py      # WebSocket handlers
│   ├── auth/                 # Authentication logic
│   ├── models/               # SQLAlchemy models
│   ├── services/             # Business logic services
│   ├── workers/              # Celery task definitions
│   ├── config.py             # Configuration management
│   └── requirements.txt      # Python dependencies
├── frontend/
│   └── src/
│       ├── components/       # Reusable UI components
│       │   └── Layout/       # Sidebar, navigation
│       ├── pages/            # Route components
│       │   ├── dashboard/    # Dashboard page
│       │   ├── jobs/         # Job history page
│       │   ├── video/        # Video editor pages
│       │   └── Auth/         # Login/register
│       ├── contexts/         # React contexts
│       ├── services/         # API client
│       └── App.tsx           # Main router
├── database/
│   └── schema.sql            # PostgreSQL schema
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Local development
├── Dockerfile.*              # Container definitions
└── docs/                     # Documentation
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/auth/logout` | User logout |

### Video Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/video-editors/sync-process` | Normal video editor processing |
| POST | `/api/v1/video-editors/pro-sync-process` | Pro video editor processing |
| POST | `/api/v1/jobs/direct-process` | Direct GhostCut text removal |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobs/my` | Get user's jobs |
| GET | `/api/v1/jobs/{job_id}` | Get job details |
| DELETE | `/api/v1/jobs/{job_id}` | Delete job |
| POST | `/api/v1/jobs/{job_id}/cancel` | Cancel processing job |

## Deployment

### Railway (Production)

The application is deployed on Railway with the following services:

| Service | Description |
|---------|-------------|
| frontend | React app served via Nginx |
| backend | FastAPI application |
| worker | Celery background worker |
| beat | Celery scheduler |
| PostgreSQL | Database (Railway addon) |
| Redis | Cache/broker (Railway addon) |

**Deploy commands:**
```bash
# Deploy frontend
railway up --service frontend --detach

# Deploy backend
railway up --service backend --detach

# View logs
railway logs --service backend
railway logs --service worker
```

### Docker (Local Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://:password@host:6379/0

# JWT
SECRET_KEY=your-secret-key

# External APIs
SYNC_API_KEY=your-sync-api-key
GHOSTCUT_API_KEY=your-ghostcut-api-key
GHOSTCUT_APP_SECRET=your-app-secret
GHOSTCUT_UID=your-uid

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-2

# Frontend
CORS_ORIGINS=https://your-frontend-url.com
```

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
psql -d your_database -f ../database/schema.sql

# Start backend
uvicorn api.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Worker Setup
```bash
cd backend

# Start Celery worker
celery -A workers.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A workers.celery_app beat --loglevel=info
```

## Subscription Plans

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Credits/month | 100 | 1,000 | 5,000 |
| Max file size | 100MB | 500MB | 2GB |
| Video length | 5 min | 30 min | Unlimited |
| API access | No | Yes | Yes |
| Priority processing | No | No | Yes |

## Security

- JWT authentication with access/refresh tokens
- Password hashing with bcrypt
- CORS protection with configurable origins
- Rate limiting on API endpoints
- File type and size validation
- SQL injection protection via ORM

## Open Source Notice

This project is open-sourced under the Apache License 2.0. You are free to use, modify, and distribute this software in compliance with the license terms. See the [LICENSE](LICENSE) file for the full license text.

## License

Copyright 2024 MetaFrazo

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Support

For support and questions, please contact the development team.

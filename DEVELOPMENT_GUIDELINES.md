# Rules to Follow for Any Project (Extremely Important!!!)

## Communication

- Always think and communicate in English.

## Documentation

- When writing `.md` documentation, always use English.
- Store official documentation in the `docs/` directory of the project.
- Store discussion and review documents such as plans and proposals in the `discuss/` directory of the project.

## Code Architecture

- Mandatory coding guidelines include the following principles:
  1. For dynamic languages such as Python, JavaScript, and TypeScript, each code file should ideally not exceed 300 lines.
  2. For static languages such as Java, Go, and Rust, each code file should ideally not exceed 400 lines.
  3. Each folder should ideally contain no more than 8 files. If more are needed, organize them into multiple subfolders.
- In addition to these hard constraints, always strive for elegant architecture design and avoid the following "code smells" that can erode code quality:
  1. **Rigidity**: The system is hard to change; even small modifications trigger a cascade of changes.
  2. **Redundancy**: The same logic is duplicated in multiple places, making maintenance difficult and causing inconsistencies.
  3. **Circular Dependency**: Two or more modules are interdependent in a tangled way, creating an unbreakable "dead knot" that hinders testing and reuse.
  4. **Fragility**: A change in one part of the code causes unexpected breakage in unrelated parts of the system.
  5. **Obscurity**: Code intent is unclear, and structure is messy, making it hard for readers to understand its functionality and design.
  6. **Data Clump**: Several data items always appear together in method parameters, indicating they should be grouped into a single object.
  7. **Needless Complexity**: Using an overcomplicated solution for a simple problem, making the system bloated and hard to understand.
- **Very Important!!** Whether writing your own code or reading/reviewing others' code, strictly follow the above constraints and always strive for elegant architecture design.
- **Very Important!!** Whenever you identify any of the above "code smells," immediately ask the user if optimization is needed and provide reasonable suggestions.

## Run & Debug

- All Run & Debug scripts must be maintained in the `scripts/` directory of the project.
- For all Run & Debug operations, always use `.sh` scripts in the `scripts/` directory to start and stop the project. Never run `npm`, `pnpm`, `uv`, `python`, etc., directly.
- If a `.sh` script fails, whether due to issues in the script itself or in other code, fix the issue urgently and still use `.sh` scripts for starting and stopping the project.
- Before running or debugging, configure a logger with file output for all projects, and output logs to the `logs/` directory.

## Python

- Define all data structures with strong typing whenever possible. If you must use an unstructured `dict`, first pause and get user approval.
- Always use `.venv` as the Python virtual environment directory name.
- You must use `uv` instead of `pip`, `poetry`, `conda`, `python3`, or `python` for dependency management, building, and debugging.
- Keep the project root directory clean, containing only necessary files.
- Keep `main.py` concise, containing only essential code.

## React / Next.js / TypeScript / JavaScript

- **Next.js** must use version `v15.4`; do not use `v15.3`, `v14`, or earlier.
- **React** must use version `v19`; do not use `v18` or earlier.
- **Tailwind CSS** must use version `v4`; do not use `v3` or earlier.
- Do not use the CommonJS module system.
- Prefer TypeScript whenever possible. Only use JavaScript when the build tool does not fully support TypeScript (e.g., WeChat Mini Program main project).
- Define all data structures with strong typing whenever possible. If you must use `any` or unstructured `json`, first pause and get user approval.

---

# Video Text Inpainting Service - Claude Development Guide

## Project Overview

This is a **Video Text Inpainting Service** - a professional SaaS platform for AI-powered video text removal using advanced inpainting technology. The application automatically detects and removes text, subtitles, and watermarks from videos using external APIs like Ghostcut/Zhaoli.

### Business Model
- **SaaS Platform**: Multi-tenant with user authentication and subscription tiers
- **Credit-based Billing**: Free (100 credits), Pro (1,000 credits), Enterprise (5,000 credits)
- **API Access**: RESTful API for developers on Pro+ plans

## Architecture Overview

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Client  │    │  FastAPI Backend │    │ Celery Workers  │
│   (Material-UI) │───▶│   (Auth & API)   │───▶│ (Video Proc.)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                      ┌─────────────────┐    ┌─────────────────┐
                      │   PostgreSQL    │    │ External APIs   │
                      │   (Database)    │    │ (Ghostcut/AWS)  │
                      └─────────────────┘    └─────────────────┘
                              │
                              ▼
                      ┌─────────────────┐
                      │      Redis      │
                      │  (Cache & MQ)   │
                      └─────────────────┘
```

### Technology Stack

#### Backend (Python)
- **FastAPI 0.104.1**: Modern async web framework
- **SQLAlchemy 2.0.23**: Database ORM with PostgreSQL
- **Celery 5.3.4**: Distributed task queue for background processing
- **Redis 5.0.1**: Caching and message broker
- **JWT Authentication**: Access and refresh tokens
- **Video Processing**: OpenCV, MoviePy, PIL, EasyOCR
- **AWS Integration**: S3 storage, Translate service

#### Frontend (React/TypeScript)
- **React 19**: UI framework (must use v19, not v18 or earlier)
- **TypeScript**: Type-safe development (preferred over JavaScript)
- **Material-UI**: Professional component library
- **React Query**: Server state management
- **Socket.IO Client**: Real-time updates
- **React Router**: Client-side routing
- **Note**: If using Next.js, must use v15.4; if using Tailwind CSS, must use v4

#### Infrastructure
- **Docker**: Multi-container orchestration
- **PostgreSQL 15**: Primary database
- **Redis 7**: Cache and message broker
- **Nginx**: Reverse proxy (production)

## Project Structure

```
Test1-frazo/
├── backend/                 # FastAPI application
│   ├── api/
│   │   ├── routes/         # API endpoints (auth, jobs, admin, etc.)
│   │   ├── websocket.py    # WebSocket handlers
│   │   └── main.py         # FastAPI application entry
│   ├── auth/               # JWT authentication & authorization
│   ├── models/             # SQLAlchemy database models
│   ├── workers/            # Celery tasks for video processing
│   └── config.py           # Configuration management
├── frontend/               # React TypeScript application
│   └── src/
│       ├── pages/          # Route components
│       ├── components/     # Reusable UI components
│       ├── contexts/       # React contexts (Auth, WebSocket)
│       ├── hooks/          # Custom React hooks
│       └── services/       # API client services
├── database/
│   └── schema.sql          # PostgreSQL database schema
├── static/videos/          # Video file storage
├── logs/                   # Application logs
├── docker-compose.yml      # Container orchestration
├── video_processing.py     # Core video processing logic
└── scripts/                # Run & debug scripts (to be created)
```

## Development Environment Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker & Docker Compose**

### Environment Configuration

Create `.env` file in project root:
```bash
# Database
DATABASE_URL=postgresql://vti_user:vti_password_123@localhost:5432/video_text_inpainting

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# External APIs
GHOSTCUT_API_KEY=your-api-key
GHOSTCUT_API_URL=https://api.ghostcut.com
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# File Storage
UPLOAD_PATH=/app/uploads
MAX_UPLOAD_SIZE=2147483648

# Environment
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:80
```

## Run & Debug Commands

### Using Docker (Recommended)
```bash
# Start all services
./scripts/start.sh

# Stop all services
./scripts/stop.sh

# View logs
./scripts/logs.sh

# Restart specific service
./scripts/restart.sh backend
```

### Development Mode (Individual Services)
```bash
# Backend
./scripts/start-backend.sh

# Frontend
./scripts/start-frontend.sh

# Celery Worker
./scripts/start-worker.sh

# Database setup
./scripts/setup-db.sh
```

### Testing
```bash
# Backend tests
./scripts/test-backend.sh

# Frontend tests
./scripts/test-frontend.sh

# Integration tests
./scripts/test-integration.sh
```

## Code Specifications

### Python Backend Standards
1. **File Size Limit**: Maximum 300 lines per file
2. **Type Hints**: Use throughout, avoid `Any` or unstructured `dict`
3. **Dependency Management**: Use `uv` instead of pip, poetry, conda, python3, or python
4. **Virtual Environment**: Always use `.venv` directory
5. **Error Handling**: Comprehensive exception handling with logging
6. **API Design**: Follow REST principles, use Pydantic models
7. **Database**: Use SQLAlchemy ORM, no raw SQL queries
8. **Project Structure**: Keep project root directory clean, containing only necessary files
9. **Main Module**: Keep `main.py` concise, containing only essential code

### Frontend Standards
1. **File Size Limit**: Maximum 300 lines per TypeScript file
2. **Type Safety**: Strong TypeScript typing, avoid `any`
3. **Components**: Functional components with hooks
4. **State Management**: React Query for server state, Context for global state
5. **Styling**: Material-UI components with consistent theming
6. **Error Handling**: Error boundaries and user-friendly error messages
7. **React Version**: Must use React v19 (not v18 or earlier)
8. **Module System**: Do not use CommonJS module system
9. **TypeScript Preference**: Prefer TypeScript over JavaScript unless build tool limitations

### Directory Organization
1. **Maximum 8 files per folder** - create subfolders if needed
2. **Feature-based organization** for frontend components
3. **Domain-driven structure** for backend modules

### Code Quality Guidelines
Avoid these code smells:
- **Rigidity**: Hard to change code
- **Redundancy**: Duplicated logic
- **Circular Dependencies**: Tangled module dependencies
- **Fragility**: Changes break unrelated parts
- **Obscurity**: Unclear code intent
- **Data Clumps**: Related data not grouped
- **Needless Complexity**: Over-engineered solutions

## API Documentation

### Core Endpoints
- **Authentication**: `/api/v1/auth/*`
- **Jobs**: `/api/v1/jobs/*`
- **Files**: `/api/v1/files/*`
- **Admin**: `/api/v1/admin/*`
- **Chunked Upload**: `/api/v1/chunked-upload/*`

### WebSocket Events
- Job progress updates
- Real-time notifications
- System status updates

## Video Processing Workflow

1. **Upload**: Chunked or direct upload
2. **Validation**: File type, size, user credits
3. **Queue**: Celery background task
4. **Processing**: External API integration
5. **Progress**: Real-time WebSocket updates
6. **Completion**: Download link generation
7. **Cleanup**: File retention management

## Database Schema

### Core Tables
- **users**: User accounts and authentication
- **jobs**: Video processing jobs
- **files**: File metadata and storage info
- **subscriptions**: User subscription plans
- **credits**: Credit usage tracking

## Security Considerations

- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based access control
- **File Validation**: Type and size checks
- **Rate Limiting**: API endpoint protection
- **CORS**: Configured origins
- **Input Sanitization**: Prevent injection attacks

## Monitoring & Logging

- **Application Logs**: Structured logging to `logs/` directory
- **Health Checks**: All services have health endpoints
- **Metrics**: Prometheus-compatible metrics
- **Celery Monitoring**: Flower dashboard at :5555
- **Error Tracking**: Comprehensive error logging

## Deployment

### Development
```bash
docker-compose up -d
```

### Production
- Use environment-specific configurations
- Enable HTTPS and security headers
- Configure load balancing for scalability
- Set up monitoring and alerting

## External Integrations

### Ghostcut/Zhaoli API
- Text detection and inpainting
- Task status monitoring
- Result retrieval

### AWS Services
- **S3**: Video file storage
- **Translate**: Multi-language support
- **IAM**: Secure credential management

## Development Workflow

1. **Feature Development**: Branch-based development
2. **Code Review**: PR-based reviews
3. **Testing**: Unit, integration, and E2E tests
4. **Deployment**: Automated CI/CD pipeline
5. **Monitoring**: Real-time system monitoring

## Troubleshooting

### Common Issues
- **Database Connection**: Check PostgreSQL service
- **Redis Connection**: Verify Redis server status
- **File Upload**: Check disk space and permissions
- **Processing Failures**: Review Celery worker logs
- **API Errors**: Check external service availability

### Log Locations
- **Backend**: `logs/backend.log`
- **Worker**: `logs/worker.log`
- **Database**: Container logs
- **Redis**: Container logs

---

**Important Notes:**
- Always use scripts in `scripts/` directory for run/debug operations
- Maintain type safety throughout the codebase
- Follow the established architecture patterns
- Keep files under size limits and folders organized
- Log all operations to files in `logs/` directory
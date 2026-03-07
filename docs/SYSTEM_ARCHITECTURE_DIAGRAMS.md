# Video Text Inpainting Service - System Architecture Diagrams

## Overview

This document contains comprehensive Mermaid diagrams that visualize the complete architecture, workflows, and component relationships of the Video Text Inpainting Service. These diagrams are designed to help developers understand the codebase structure and system interactions.

---

## 1. Complete System Architecture

```mermaid
---
title: Video Text Inpainting Service - Complete System Architecture
---

graph TB
    %% User Interface Layer
    subgraph "Frontend - React 19 + TypeScript"
        UI[User Interface]
        
        subgraph "Core Pages"
            VEP[VideoEditorPage]
            DP[DashboardPage]
            LP[LoginPage]
            SP[SettingsPage]
        end
        
        subgraph "Components"
            VU[VideoUpload]
            SVE[SimpleVideoEditor]
            JSC[JobStatusCard]
            EB[ErrorBoundary]
        end
        
        subgraph "Services"
            API[API Client]
            GCA[GhostCut API Client]
            WS[WebSocket Client]
        end
        
        UI --> VEP
        UI --> DP
        VEP --> VU
        VEP --> SVE
        VEP --> JSC
        API --> GCA
        EB -.-> VEP
    end

    %% Backend Services Layer
    subgraph "Backend - FastAPI + SQLAlchemy"
        subgraph "API Routes"
            AUTH["/api/v1/auth"]
            USERS["/api/v1/users"]
            FILES["/api/v1/files"]
            JOBS["/api/v1/jobs"]
            GC["/api/v1/ghostcut"]
            ADMIN["/api/v1/admin"]
        end
        
        subgraph "Core Services"
            JWT[JWT Handler]
            DB[Database Models]
            CFG[Configuration]
        end
        
        subgraph "WebSocket"
            WSH[WebSocket Handler]
            JU[Job Updates]
        end
    end

    %% Worker Layer
    subgraph "Celery Workers"
        CA[Celery App]
        GT[GhostCut Tasks]
        VT[Video Tasks]
        
        CA --> GT
        CA --> VT
    end

    %% External Services Layer
    subgraph "External APIs"
        GCAPI[GhostCut/Zhaoli API]
        AWS[AWS Services]
        S3[S3 Storage]
    end

    %% Data Layer
    subgraph "Data Storage"
        PG[(PostgreSQL 15)]
        RD[(Redis 7)]
        FS[File Storage]
    end

    %% Infrastructure Layer
    subgraph "Docker Infrastructure"
        NGINX[Nginx Reverse Proxy]
        DC[Docker Compose]
        FLOWER[Flower Monitor]
    end

    %% Connections
    UI -->|HTTP/WS| NGINX
    NGINX --> AUTH
    NGINX --> FILES
    NGINX --> GC
    
    AUTH --> JWT
    FILES --> DB
    GC --> GT
    JOBS --> DB
    
    GT -->|API Calls| GCAPI
    VT --> FS
    
    DB --> PG
    CA --> RD
    WSH --> RD
    
    WS -->|Real-time Updates| WSH
    JU --> WS
    
    FLOWER --> CA

    %% Styling
    classDef frontend fill:#e1f5fe
    classDef backend fill:#f3e5f5
    classDef worker fill:#fff3e0
    classDef external fill:#ffebee
    classDef data fill:#e8f5e8
    classDef infra fill:#fafafa

    class UI,VEP,DP,LP,SP,VU,SVE,JSC,EB,API,GCA,WS frontend
    class AUTH,USERS,FILES,JOBS,GC,ADMIN,JWT,DB,CFG,WSH,JU backend
    class CA,GT,VT worker
    class GCAPI,AWS,S3 external
    class PG,RD,FS data
    class NGINX,DC,FLOWER infra
```

---

## 2. Video Processing Workflow

```mermaid
---
title: Video Processing Workflow - Complete User Journey
---

sequenceDiagram
    participant U as User
    participant FE as React Frontend
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant C as Celery Worker
    participant GC as GhostCut API
    participant WS as WebSocket
    participant FS as File Storage

    Note over U,FS: 1. Authentication & Setup
    U->>FE: Login/Register
    FE->>API: POST /auth/login
    API->>DB: Validate credentials
    DB-->>API: User data + credits
    API-->>FE: JWT tokens
    
    Note over U,FS: 2. Video Upload & Annotation
    U->>FE: Upload video file
    FE->>API: POST /files/upload (chunked)
    API->>FS: Store video file
    API->>DB: Save file metadata
    API-->>FE: File URL & ID
    
    U->>FE: Create annotations (rectangles)
    Note over FE: SimpleVideoEditor with canvas drawing
    FE->>FE: Store annotations locally
    
    Note over U,FS: 3. Job Submission
    U->>FE: Submit for processing
    FE->>API: POST /ghostcut/render
    API->>DB: Validate user credits
    API->>DB: Create VideoJob record
    API->>C: Queue Celery task
    API-->>FE: Job ID & status
    
    Note over U,FS: 4. Background Processing
    C->>DB: Update job status to PROCESSING
    C->>WS: Send progress update
    WS-->>FE: Real-time job status
    
    C->>GC: Submit video + annotations
    GC-->>C: GhostCut job ID
    
    loop Polling Status
        C->>GC: GET job status
        GC-->>C: Progress update
        C->>WS: Send progress
        WS-->>FE: Update UI
    end
    
    Note over U,FS: 5. Processing Complete
    GC-->>C: Processing complete + output URL
    C->>C: Download processed video
    C->>FS: Save output file
    C->>DB: Create output file record
    C->>DB: Deduct user credits
    C->>DB: Update job to COMPLETED
    C->>WS: Send completion update
    WS-->>FE: Final status update
    
    Note over U,FS: 6. Download Result
    FE->>U: Show download button
    U->>API: GET /files/{id}/download
    API->>FS: Retrieve processed video
    API-->>U: Video file download
```

---

## 3. Database Schema & Relationships

```mermaid
---
title: Database Schema & Relationships
---

erDiagram
    USERS {
        uuid id PK
        string email UK
        string username UK
        string password_hash
        boolean is_active
        boolean is_admin
        int credits_balance
        datetime created_at
        datetime updated_at
    }
    
    VIDEO_JOBS {
        uuid id PK
        uuid user_id FK
        string original_filename
        string display_name
        enum status
        jsonb processing_config
        int progress_percentage
        string progress_message
        string error_message
        int estimated_credits
        int actual_credits_used
        string celery_task_id
        string external_job_id
        uuid output_file_id FK
        datetime queued_at
        datetime started_at
        datetime completed_at
        datetime created_at
    }
    
    FILES {
        uuid id PK
        uuid user_id FK
        string filename
        enum file_type
        bigint file_size
        string storage_path
        string mime_type
        boolean is_public
        datetime created_at
        datetime updated_at
    }
    
    CREDIT_TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        int amount
        int balance_after
        string description
        uuid job_id FK
        datetime created_at
    }
    
    SUBSCRIPTIONS {
        uuid id PK
        uuid user_id FK
        enum plan_type
        datetime start_date
        datetime end_date
        boolean is_active
        datetime created_at
    }

    USERS ||--o{ VIDEO_JOBS : creates
    USERS ||--o{ FILES : owns
    USERS ||--o{ CREDIT_TRANSACTIONS : has
    USERS ||--o{ SUBSCRIPTIONS : subscribes
    VIDEO_JOBS ||--o| FILES : produces
    VIDEO_JOBS ||--o{ CREDIT_TRANSACTIONS : consumes
```

---

## 4. API Endpoint Structure

```mermaid
---
title: API Endpoint Structure
---

graph LR
    subgraph "Authentication Endpoints"
        A1[POST /auth/login]
        A2[POST /auth/register]
        A3[POST /auth/refresh]
        A4[POST /auth/logout]
    end
    
    subgraph "User Management"
        U1[GET /users/me]
        U2[PUT /users/me]
        U3[GET /users/credits]
    end
    
    subgraph "File Operations"
        F1[POST /files/upload]
        F2[GET /files/{id}]
        F3[GET /files/{id}/download]
        F4[DELETE /files/{id}]
        F5[POST /chunked-upload/start]
        F6[POST /chunked-upload/chunk]
        F7[POST /chunked-upload/complete]
    end
    
    subgraph "Job Management"
        J1[GET /jobs]
        J2[GET /jobs/{id}]
        J3[POST /jobs/{id}/cancel]
        J4[DELETE /jobs/{id}]
    end
    
    subgraph "GhostCut Processing"
        G1[POST /ghostcut/render]
        G2[GET /ghostcut/jobs/{id}]
        G3[POST /ghostcut/jobs/{id}/cancel]
        G4[GET /ghostcut/jobs]
    end
    
    subgraph "Admin Operations"
        AD1[GET /admin/users]
        AD2[GET /admin/jobs]
        AD3[GET /admin/system-stats]
    end

    %% Flow connections
    A1 --> U1
    F1 --> G1
    G1 --> J2
    J2 --> F3
```

---

## 5. Real-time Communication Flow

```mermaid
---
title: Real-time Communication Flow
---

graph TD
    subgraph "WebSocket Events"
        WS[WebSocket Connection]
        
        subgraph "Client Events"
            CE1[connection]
            CE2[join_room]
            CE3[leave_room]
        end
        
        subgraph "Server Events"
            SE1[job_update]
            SE2[job_complete]
            SE3[job_error]
            SE4[system_notification]
        end
    end
    
    subgraph "Event Flow"
        USER[User Browser]
        BACKEND[FastAPI Backend]
        WORKER[Celery Worker]
        REDIS[Redis PubSub]
    end
    
    USER -->|Connect| WS
    WS -->|Authenticate| BACKEND
    BACKEND -->|Join user room| REDIS
    
    WORKER -->|Progress update| REDIS
    REDIS -->|Broadcast| BACKEND
    BACKEND -->|Emit| WS
    WS -->|Update UI| USER
    
    %% Event types
    WORKER -.->|job_update| SE1
    WORKER -.->|job_complete| SE2
    WORKER -.->|job_error| SE3
    BACKEND -.->|system_notification| SE4
```

---

## 6. Component Architecture & State Flow

```mermaid
---
title: Component Architecture & State Flow
---

graph TB
    subgraph "React Component Tree"
        APP[App.tsx]
        
        subgraph "Layout"
            SIDEBAR[Sidebar]
            HEADER[Header]
        end
        
        subgraph "Pages"
            VEP[VideoEditorPage]
            DASH[DashboardPage]
            SAFE[SafeDashboard]
        end
        
        subgraph "Video Editor Components"
            VU[VideoUpload]
            SVE[SimpleVideoEditor]
            JSC[JobStatusCard]
            CANVAS[Canvas Annotations]
        end
        
        subgraph "Context Providers"
            AUTH[AuthContext]
            THEME[ThemeContext]
            WS[WebSocketContext]
        end
        
        subgraph "Error Handling"
            EB[ErrorBoundary]
        end
    end
    
    APP --> AUTH
    APP --> THEME
    APP --> WS
    APP --> EB
    
    EB --> VEP
    VEP --> VU
    VEP --> SVE
    VEP --> JSC
    SVE --> CANVAS
    
    DASH --> SAFE
    
    %% State flow
    AUTH -.->|User state| VEP
    WS -.->|Job updates| JSC
    CANVAS -.->|Annotations| SVE
    SVE -.->|Video data| VEP
```

---

## Key Architecture Features

### 🏗️ **System Architecture**
- **Microservices**: Frontend (React), Backend (FastAPI), Workers (Celery)
- **Container Orchestration**: Docker Compose with health checks
- **Real-time Updates**: WebSocket for job progress
- **Scalable Workers**: Multiple Celery instances with Redis broker

### 🔄 **Video Processing Pipeline**
1. **Upload**: Chunked upload for large files
2. **Annotation**: Custom canvas-based rectangle drawing
3. **Submission**: Validates credits and queues job
4. **Processing**: Celery worker calls GhostCut API
5. **Polling**: Real-time status updates via WebSocket
6. **Completion**: Download processed video

### 🔐 **Security & Authentication**
- **JWT Tokens**: Access + refresh token pattern
- **Role-based Access**: User/Admin permissions
- **Credit System**: Pay-per-use with transaction tracking
- **Input Validation**: Pydantic models throughout

### 📊 **Data Management**
- **PostgreSQL**: Relational data with proper foreign keys
- **Redis**: Caching and message broker
- **File Storage**: Local storage with S3 integration planned
- **Type Safety**: Strong typing in both Python and TypeScript

### 🔧 **Development Features**
- **Error Boundaries**: React error handling
- **Health Checks**: All services monitored
- **Logging**: Structured logging to files
- **Testing**: Unit and integration test support

---

## Current System Status

### ✅ Completed Components
- **Frontend**: Working with custom video editor and error handling
- **Backend**: All APIs implemented, ready for GhostCut integration  
- **Database**: Schema complete with all required tables
- **Docker Setup**: Multi-container orchestration with health checks
- **Error Handling**: React ErrorBoundary and comprehensive logging

### ⏳ In Progress / Pending
- **Authentication**: Temporarily bypassed for testing
- **GhostCut API**: Waiting for production credentials
- **WebSocket**: Real-time updates implementation
- **File Upload**: Backend endpoint needs fixes
- **Testing**: Comprehensive test coverage

### 🚀 Technology Stack
- **Frontend**: React 19, TypeScript, Material-UI
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL 15
- **Workers**: Celery, Redis 7
- **Infrastructure**: Docker, Nginx, Flower monitoring
- **External**: GhostCut/Zhaoli API, AWS S3 (planned)

---

## File Locations for Reference

### Key Backend Files
- `backend/api/main.py` - FastAPI application entry point
- `backend/api/routes/` - All API endpoints
- `backend/workers/ghostcut_tasks.py` - Celery background tasks
- `backend/models/` - Database models and schemas

### Key Frontend Files
- `frontend/src/App.tsx` - Main React application
- `frontend/src/pages/VideoEditorPage.tsx` - Video editor interface
- `frontend/src/components/VideoEditor/` - Video editor components
- `frontend/src/services/ghostcutApi.ts` - API client services

### Configuration Files
- `docker-compose.yml` - Container orchestration
- `backend/config.py` - Backend configuration
- `database/schema.sql` - Database schema
- `scripts/` - Run and debug scripts

This comprehensive diagram set provides a complete understanding of the Video Text Inpainting Service architecture for development and study purposes.
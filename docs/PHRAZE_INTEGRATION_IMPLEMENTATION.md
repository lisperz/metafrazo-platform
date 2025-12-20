# Phraze.so Integration - Implementation Guide

This document describes the Phase 1 implementation of the phraze.so embedded editor integration.

## Overview

The MetaFrazo editor can now be embedded in phraze.so as an iframe or redirected editor. Users are authenticated via JWT tokens issued by phraze.so, and job status updates are sent via callbacks.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   phraze.so     │────────►│  editor.phraze  │────────►│   MetaFrazo     │
│   (Client)      │  JWT    │   (Frontend)    │  API    │   (Backend)     │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────────┐
                                                        │   GhostCut/     │
                                                        │   Sync.so       │
                                                        └─────────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────────┐
                                                        │   Callback to   │
                                                        │   phraze.so     │
                                                        └─────────────────┘
```

## New Files Created

### Backend

| File | Description |
|------|-------------|
| `backend/auth/phraze/__init__.py` | Module exports |
| `backend/auth/phraze/schemas.py` | Pydantic schemas for JWT and callbacks |
| `backend/auth/phraze/validator.py` | RS256 JWT validation logic |
| `backend/auth/phraze/callback_service.py` | Service for sending callbacks to phraze.so |
| `backend/api/routes/embedded/__init__.py` | Router exports |
| `backend/api/routes/embedded/routes.py` | Main embedded API endpoints |
| `backend/api/routes/embedded/mock_routes.py` | Mock routes for testing |

### Frontend

| File | Description |
|------|-------------|
| `frontend/src/services/embeddedApi.ts` | API service for embedded endpoints |
| `frontend/src/pages/embedded/EmbeddedEditorPage.tsx` | Embedded editor page |
| `frontend/src/pages/embedded/index.ts` | Page exports |

### Database

| File | Description |
|------|-------------|
| `database/migrations/add_embedded_job_support.sql` | Migration for is_embedded_job column |

## API Endpoints

### Embedded Endpoints (`/api/v1/embedded/`)

#### `GET /validate`
Validates JWT token from phraze.so.

**Query Parameters:**
- `token` (required): JWT token from phraze.so

**Response:**
```json
{
  "valid": true,
  "user_id": "phraze-user-123",
  "job_id": "phraze-job-456",
  "video_url": "https://s3.amazonaws.com/...",
  "callback_url": "https://phraze.so/api/editor/callback",
  "message": "Access granted"
}
```

#### `POST /process`
Starts video processing.

**Query Parameters:**
- `token` (required): JWT token

**Request Body:**
```json
{
  "processing_type": "text_removal",
  "target_language": null,
  "audio_url": null,
  "segments": null
}
```

**Response:**
```json
{
  "job_id": "internal-uuid",
  "phraze_job_id": "phraze-job-456",
  "status": "processing",
  "message": "Video processing started"
}
```

#### `GET /status/{job_id}`
Gets job status.

**Query Parameters:**
- `token` (required): JWT token

**Response:**
```json
{
  "job_id": "internal-uuid",
  "phraze_job_id": "phraze-job-456",
  "status": "processing",
  "progress": 45,
  "message": "Text removal processing...",
  "output_url": null,
  "error_message": null
}
```

#### `POST /cancel/{job_id}`
Cancels a job.

### Mock Endpoints (`/api/v1/embedded/mock/`)

Only available in development mode.

#### `POST /generate-token`
Generates mock JWT tokens for testing.

**Request Body:**
```json
{
  "video_url": "https://s3.amazonaws.com/bucket/video.mp4",
  "user_id": null,
  "job_id": null,
  "expires_in_hours": 1
}
```

#### `GET /test-page`
Serves HTML test page for generating tokens and testing the flow.

#### `GET /redirect-to-editor`
Simulates phraze.so redirect with generated token.

#### `POST /callback`
Mock callback endpoint that logs received callbacks.

## JWT Token Structure

```json
{
  "sub": "phraze-user-id",
  "job_id": "phraze-job-id",
  "video_url": "https://s3.amazonaws.com/...",
  "callback_url": "https://phraze.so/api/editor/callback",
  "permissions": ["edit", "process"],
  "subscription_tier": "pro",
  "iat": 1703001234,
  "exp": 1703004834
}
```

### Subscription Tiers

| Tier | Editor Type | Description |
|------|-------------|-------------|
| `free` | Basic Editor | Basic text removal only |
| `normal` | Basic Editor | Basic text removal + lip-sync |
| `pro` | Pro Editor | Segment-based lip-sync + text removal |
| `enterprise` | Pro Editor | Full features + priority processing |

The `subscription_tier` field determines which editor the user sees:
- **Basic Editor** (`GhostCutVideoEditor`): For `free` and `normal` tiers
- **Pro Editor** (`ProVideoEditor`): For `pro` and `enterprise` tiers

## Callback Payload

Sent to phraze.so when job status changes:

```json
{
  "job_id": "phraze-job-id",
  "status": "completed",
  "output_url": "https://s3.amazonaws.com/.../output.mp4",
  "processing_time_seconds": 120,
  "error_code": null,
  "error_message": null,
  "metadata": {
    "internal_job_id": "metafrazo-uuid"
  },
  "timestamp": "2024-12-19T12:00:00Z",
  "signature": "hmac-sha256-signature"
}
```

### Callback Status Values
- `started`: Job has started processing
- `completed`: Job completed successfully
- `failed`: Job failed with error

## Configuration

Add these environment variables for production:

```bash
# Embedded Mode
EMBEDDED_MODE=true
PHRAZE_DOMAIN=phraze.so
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_PUBLIC_KEY=<RS256 public key from phraze.so>
CALLBACK_HMAC_SECRET=<shared secret for callback signatures>
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com
```

## Testing

1. Start the backend and frontend in development mode
2. Navigate to `http://localhost:8000/api/v1/embedded/mock/test-page`
3. Enter a video S3 URL and click "Generate Token & Open Editor"
4. The editor will open with the video pre-loaded
5. Click "Submit" to process the video
6. Callbacks will be logged in the console

## Frontend Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/editor/embedded` | `EmbeddedEditorPage` | Embedded editor entry point |

The embedded editor:
- Reads JWT token from `?token=` query parameter
- Validates token with backend
- Loads video from S3 URL in token
- Skips file upload UI
- Uses embedded API for processing
- Polls for job completion
- Sends callbacks to phraze.so

## Error Handling

Error codes returned to phraze.so:

| Code | Description |
|------|-------------|
| `TOKEN_MISSING` | No JWT token provided |
| `TOKEN_EXPIRED` | JWT token has expired |
| `TOKEN_INVALID` | JWT signature verification failed |
| `TOKEN_MALFORMED` | JWT payload missing required fields |
| `INVALID_VIDEO_URL` | Video URL not from allowed S3 domain |
| `VALIDATION_ERROR` | General validation error |
| `PROCESSING_ERROR` | Failed to start processing |
| `VIDEO_DOWNLOAD_FAILED` | Could not download video from S3 |
| `PROCESSING_FAILED` | Video processing failed |
| `SYNC_API_ERROR` | Sync.so API error |
| `GHOSTCUT_API_ERROR` | GhostCut API error |
| `S3_UPLOAD_FAILED` | Failed to upload output |
| `TIMEOUT` | Processing timed out |
| `USER_CANCELLED` | User cancelled the job |

## Next Steps (Phase 2+)

1. Add Phraze theme styling (#0A47F2 blue)
2. Add simplified audio upload for embedded lip-sync
3. Add real-time progress updates via WebSocket
4. Add more granular error handling
5. Production deployment to editor.phraze.so subdomain

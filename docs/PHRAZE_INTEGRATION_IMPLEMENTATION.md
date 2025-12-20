# Phraze.so Integration - Implementation Guide

**Last Updated**: December 20, 2025
**Status**: Phase 2 Complete - Ready for Production Deployment

## Overview

The MetaFrazo editor can be embedded in phraze.so as a redirected editor. Users are authenticated via JWT tokens issued by phraze.so, and job status updates are sent via callbacks.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   phraze.so     │────────►│  editor.phraze  │────────►│   MetaFrazo     │
│   (Client)      │  JWT    │   (Frontend)    │  API    │   (Backend)     │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────────┐
                                                        │   Sync.so       │
                                                        │   (Lip-sync)    │
                                                        └─────────────────┘
                                                               │
                                                               ▼
                                                        ┌─────────────────┐
                                                        │   Callback to   │
                                                        │   phraze.so     │
                                                        └─────────────────┘
```

## API Endpoints

### Embedded Endpoints (`/api/v1/embedded/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate` | GET | Validates JWT token from phraze.so |
| `/process` | POST | Starts video processing |
| `/status/{job_id}` | GET | Gets job status |
| `/cancel/{job_id}` | POST | Cancels a job |
| `/upload-audio` | POST | Uploads audio file to S3 |
| `/upload-audio-batch` | POST | Uploads multiple audio files |

### Mock Endpoints (`/api/v1/embedded/mock/`) - Development Only

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-token` | POST | Generates mock JWT tokens for testing |
| `/test-page` | GET | HTML test page for integration testing |
| `/callback` | POST | Mock callback endpoint |
| `/callbacks` | GET | Get received callbacks |

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

| Tier | Editor Type | Features |
|------|-------------|----------|
| `free` | Basic Editor | Basic text removal only |
| `normal` | Basic Editor | Basic text removal + single-audio lip-sync |
| `pro` | Pro Editor | Segment-based lip-sync + text removal |
| `enterprise` | Pro Editor | Full features + priority processing |

## Callback System

### Callback Payload

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
  "timestamp": "2025-12-20T12:00:00Z",
  "signature": "hmac-sha256-signature"
}
```

### Callback Status Values
- `started`: Job has started processing
- `completed`: Job completed successfully
- `failed`: Job failed with error

### Callback URL Handling

The system uses `CALLBACK_BASE_URL` for Docker workers to reach the host/production server:
- **Local development**: `http://host.docker.internal:8000`
- **Production (Railway)**: `https://backend-production-268a.up.railway.app`

The callback service automatically normalizes URLs based on the environment.

## Error Codes

| Code | Description |
|------|-------------|
| `TOKEN_MISSING` | No JWT token provided |
| `TOKEN_EXPIRED` | JWT token has expired |
| `TOKEN_INVALID` | JWT signature verification failed |
| `TOKEN_MALFORMED` | JWT payload missing required fields |
| `INVALID_VIDEO_URL` | Video URL not from allowed S3 domain |
| `PROCESSING_FAILED` | Video processing failed |
| `SYNC_API_ERROR` | Sync.so API error |
| `S3_UPLOAD_FAILED` | Failed to upload output |
| `TIMEOUT` | Processing timed out |
| `USER_CANCELLED` | User cancelled the job |

---

## Production Deployment Steps

### Step 1: Railway Environment Variables

Add these environment variables to Railway backend service:

```bash
# Embedded Mode Configuration
EMBEDDED_MODE=true
PHRAZE_DOMAIN=phraze.so
PHRAZE_PUBLIC_KEY=<RS256 public key from phraze.so - coordinate with Phraze team>
PHRAZE_CALLBACK_URL=https://api.phraze.so/editor/callback
CALLBACK_HMAC_SECRET=<shared secret - coordinate with Phraze team>
CALLBACK_BASE_URL=https://backend-production-268a.up.railway.app
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com

# Update CORS for phraze.so domains
CORS_ORIGINS=https://editor.phraze.so,https://phraze.so,https://frontend-production-b02b.up.railway.app
```

### Step 2: Railway Frontend Environment Variables

```bash
REACT_APP_API_URL=https://backend-production-268a.up.railway.app/api/v1
```

### Step 3: Domain Setup

1. **Create subdomain**: Set up `editor.phraze.so` DNS record pointing to Railway frontend
2. **Update Railway**: Configure custom domain in Railway frontend service
3. **Update FRONTEND_URL**: Set `FRONTEND_URL=https://editor.phraze.so` in backend

### Step 4: Phraze.so Team Coordination

Provide to Phraze.so team:
- Editor URL: `https://editor.phraze.so/editor/embedded?token={jwt_token}`
- Callback endpoint: They need to provide their callback URL
- JWT public key: They need to provide RS256 public key for token verification
- HMAC secret: Agree on shared secret for callback signature verification

Receive from Phraze.so team:
- `PHRAZE_PUBLIC_KEY`: RS256 public key for JWT verification
- `PHRAZE_CALLBACK_URL`: Their callback endpoint URL
- `CALLBACK_HMAC_SECRET`: Shared secret for HMAC signatures

### Step 5: Deploy and Test

```bash
# Deploy backend
cd backend
railway up --service backend --detach

# Deploy frontend
cd frontend
railway up --service frontend --detach

# Check logs
railway logs --service backend
railway logs --service frontend
```

### Step 6: End-to-End Testing

1. Have Phraze.so team generate a real JWT token
2. Navigate to `https://editor.phraze.so/editor/embedded?token={token}`
3. Create segments with audio files
4. Submit for processing
5. Verify callbacks received by Phraze.so

---

## Local Development Testing

### Prerequisites
- Docker running (for Celery workers)
- PostgreSQL and Redis running (via docker-compose)

### Steps

1. Start Docker services:
   ```bash
   docker-compose up -d
   ```

2. Start backend:
   ```bash
   bash scripts/start-backend.sh
   ```

3. Start frontend:
   ```bash
   bash scripts/start-frontend.sh
   ```

4. Open test page:
   ```
   http://localhost:8000/api/v1/embedded/mock/test-page
   ```

5. Generate token with "pro" subscription tier

6. Click "Open Editor" and test the full flow

7. Verify both "started" and "completed" callbacks appear in callback log

---

## Key Files Reference

### Backend
| File | Description |
|------|-------------|
| `backend/config.py` | Configuration including `CALLBACK_BASE_URL` |
| `backend/auth/phraze/` | JWT validation and callback service |
| `backend/api/routes/embedded/` | Embedded API routes |
| `backend/workers/embedded_tasks.py` | Celery tasks for polling and callbacks |
| `backend/services/embedded_processing.py` | Sync.so API integration |

### Frontend
| File | Description |
|------|-------------|
| `frontend/src/pages/embedded/` | Embedded editor page |
| `frontend/src/services/embeddedApi.ts` | API service for embedded endpoints |
| `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` | Job submission and polling |

---

## Troubleshooting

### Callbacks not received
- Check `CALLBACK_BASE_URL` is correctly set
- For local dev: Use `http://host.docker.internal:8000`
- For production: Use actual backend URL

### "started" callback missing but "completed" works
- The callback service normalizes `host.docker.internal` to `localhost` when running on host
- Ensure `_normalize_callback_url()` function is present in callback_service.py

### JWT validation failing
- Check `PHRAZE_PUBLIC_KEY` is correctly set
- Ensure token hasn't expired
- Verify token is RS256 signed

### Sync.so processing failing
- Check `SYNC_API_KEY` is valid
- Verify video URL is accessible
- Check audio files were uploaded successfully

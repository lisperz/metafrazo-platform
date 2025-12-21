# Next Session Context - Phraze.so Integration

**Last Updated**: December 20, 2025
**Current Status**: **Phase 2 COMPLETED - Ready for Production Deployment**

---

## Phase 2 Completion Summary

Phase 2 of the phraze.so embedded editor integration is **complete**. All core functionality including real Sync.so API integration, callback system, and audio/video sync timing is working correctly.

### Completed Features

| Feature | Status | Description |
|---------|--------|-------------|
| JWT Validation | Done | Token validation middleware with RS256/HS256 support |
| Embedded Editor Page | Done | `/editor/embedded` route with video URL from token |
| Video Loading from S3 | Done | Loads video directly from pre-signed URL |
| Pro Editor Integration | Done | Full segment-based lip-sync editing |
| Audio File Upload | Done | Upload audio to S3 via `/upload-audio` endpoint |
| Real Sync.so Integration | Done | Actual lip-sync processing via Sync.so API |
| Celery Worker Polling | Done | Docker workers poll Sync.so and send callbacks |
| Callback System | Done | Both "started" and "completed" callbacks working |
| Audio/Video Sync Timing | Done | Output video length matches input video length |
| Mock Test Page | Done | Test page at `/api/v1/embedded/mock/test-page` |

---

## How to Test Locally

1. Start Docker services: `docker-compose up -d`
2. Start the backend: `bash scripts/start-backend.sh`
3. Start the frontend: `bash scripts/start-frontend.sh`
4. Open test page: `http://localhost:8000/api/v1/embedded/mock/test-page`
5. Generate a new token (subscription tier: "pro")
6. Click "Open Editor" to open embedded editor
7. Add a segment with audio file
8. Click "Process" to submit
9. Verify output video length matches input video length

---

## Key Architecture

### Audio Crop Times Logic

The system ensures audio crop times are ALWAYS sent to Sync.so:
- If user explicitly sets audio crop times, those are used
- If not set, audio crop times default to match video segment times
- This ensures Sync.so knows exactly which portion of audio to use for each segment

### Callback URL Handling

The system uses `CALLBACK_BASE_URL=http://host.docker.internal:8000` for Docker workers to reach the host machine. The callback service automatically normalizes URLs:
- **From host backend**: `host.docker.internal` → `localhost`
- **From Docker worker**: `host.docker.internal` → unchanged

---

## Phase 3: Production Deployment (Next Steps)

### 3.1 Railway Deployment

- [ ] Configure Railway environment variables for embedded mode
- [ ] Set up `CALLBACK_BASE_URL` for Railway (use actual domain)
- [ ] Deploy updated backend and frontend to Railway
- [ ] Test embedded flow on Railway

### 3.2 Phraze.so Integration

- [ ] Coordinate with Phraze.so team for production JWT public key
- [ ] Configure `PHRAZE_PUBLIC_KEY` in Railway environment
- [ ] Set up `PHRAZE_CALLBACK_URL` for Phraze.so production endpoint
- [ ] Configure `CALLBACK_HMAC_SECRET` for callback authentication
- [ ] Test end-to-end flow with Phraze.so team

### 3.3 Domain Setup

- [ ] Set up editor.phraze.so subdomain pointing to Railway frontend
- [ ] Configure CORS for editor.phraze.so domain
- [ ] Update `FRONTEND_URL` in production

---

## Environment Variables for Production

```bash
# Embedded Mode (add to Railway)
EMBEDDED_MODE=true
PHRAZE_DOMAIN=phraze.so
PHRAZE_PUBLIC_KEY=<RS256 public key from phraze.so>
PHRAZE_CALLBACK_URL=https://api.phraze.so/editor/callback
CALLBACK_HMAC_SECRET=<shared secret for callback signatures>
CALLBACK_BASE_URL=https://backend-production-268a.up.railway.app
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com

# Frontend URL (update for editor.phraze.so)
FRONTEND_URL=https://editor.phraze.so
CORS_ORIGINS=https://editor.phraze.so,https://phraze.so
```

---

## Railway Deployment Reference

### Services
| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://backend-production-268a.up.railway.app | Running |
| Frontend | https://frontend-production-b02b.up.railway.app | Running |
| PostgreSQL | Internal Railway connection | Connected |
| Redis | Internal Railway connection | Connected |

### Demo Credentials
| Email | Password | Role |
|-------|----------|------|
| demo@example.com | demo123 | User |
| boss@example.com | boss123 | Admin |

### Railway CLI Reference
```bash
railway logs --service backend
railway logs --service frontend
railway up --service backend --detach
railway up --service frontend --detach
```

---

## Key Files Reference

### Backend
| File | Description |
|------|-------------|
| `backend/config.py` | Configuration including `CALLBACK_BASE_URL` |
| `backend/auth/phraze/` | JWT validation and callback service |
| `backend/api/routes/embedded/` | Embedded API routes |
| `backend/workers/embedded_tasks.py` | Celery tasks for polling and callbacks |
| `backend/services/sync_segments_service.py` | Sync.so API integration with segment support |

### Frontend
| File | Description |
|------|-------------|
| `frontend/src/pages/embedded/` | Embedded editor page |
| `frontend/src/services/embeddedApi.ts` | API service for embedded endpoints |
| `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` | Job submission with audio crop time defaults |
| `frontend/src/components/VideoEditor/Pro/SegmentDialog/hooks/useSegmentForm.ts` | Segment form with audio crop logic |

# Next Session Context - Phraze.so Integration

**Last Updated**: December 25, 2025
**Current Status**: **Phase 3 COMPLETE - Embedded Editor Fully Functional on Railway**

---

## What Was Completed This Session (Dec 25, 2025)

### 1. JWT Token Generation & Testing Infrastructure
- Created `/keys/phraze_private.pem` and `/keys/phraze_public.pem` for RSA256 signing
- Created `/scripts/generate_jwt_token.py` to generate test JWT tokens for local development and testing
- Tested JWT token validation on backend - confirmed working with `ENVIRONMENT=development`

### 2. Fixed Embedded Editor Route on Frontend
- **CRITICAL FIX**: Changed import in `frontend/src/App.tsx` line 25
  - From: `import { EmbeddedEditorPage } from './pages/embedded'` (named import - WRONG)
  - To: `import EmbeddedEditorPage from './pages/embedded/EmbeddedEditorPage'` (default import - CORRECT)
- This was causing the `/editor/embedded` route to fail silently and redirect to `/dashboard`
- Fixed by updating import to match the default export in `EmbeddedEditorPage.tsx`

### 3. Cleared Railway Frontend Cache & Redeployed
- Issue: Frontend build cache was stale, preventing code updates from deploying
- Solution: Cleared Railway cache in dashboard, triggered manual rebuild
- Result: Frontend now updated with the import fix and routes correctly to embedded editor

### 4. Verified Embedded Editor Works End-to-End
- Generated JWT token with test credentials
- Tested URL: `https://frontend-production-b02b.up.railway.app/editor/embedded?token=<token>`
- Confirmed: Embedded editor now loads and displays video editor (not redirecting to dashboard anymore)
- Backend validates JWT tokens correctly with `ENVIRONMENT=development`

### 5. Created JWT Token Generation Script
- Script: `scripts/generate_jwt_token.py`
- Generates RS256-signed JWT tokens with proper payload structure
- Includes example values for testing (Taylor Swift S3 bucket URL)
- Output: Full test URLs for both Railway and local development

---

## Immediate Next Steps for Phraze.so Integration (Priority Order)

### Step 1: Production JWT Signature Verification Setup (CRITICAL)
Current state: Backend running with `ENVIRONMENT=development` (skips signature verification)
Need to do:
1. Request RSA public key from Harshit (Phraze.so developer)
   - Save as `PHRAZE_PUBLIC_KEY` environment variable on Railway
   - Remove `ENVIRONMENT=development` to enable signature verification
2. Coordinate on `CALLBACK_HMAC_SECRET`
   - Generate production secret: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Share with Harshit for callback validation

### Step 2: Test Production Flow with Real Phraze.so Account
Once signature verification is enabled:
1. Have Harshit create a test job in Phraze.so
2. Request JWT token from Phraze.so for that job
3. Test the embedded editor URL on Railway with real token
4. Verify entire workflow: edit → submit → process → callback

### Step 3: Configure Callback URL in Production
Currently callback URL is hardcoded in test script as `http://localhost:3000/api/open/editor-jobs`
Need to:
1. Set correct backend callback endpoint in Phraze.so
   - Should be: `https://backend-production-268a.up.railway.app/api/v1/embedded/callback`
2. Coordinate with Harshit to configure on Phraze.so side

---

## Current Environment Variables on Railway (Backend)

### Already Configured ✓
- DATABASE_URL - PostgreSQL on Railway
- REDIS_URL - Redis on Railway
- AWS_* - AWS S3 credentials for uploading
- GHOSTCUT_* - GhostCut API keys
- SYNC_API_KEY - Sync.so lip-sync API key
- FRONTEND_URL - Frontend Railway URL
- CORS_ORIGINS - Includes Phraze.so domain

### Need to Update for Production
- **ENVIRONMENT**: Currently `development` (skips JWT signature verification)
  - Change to: `production` (requires valid PHRAZE_PUBLIC_KEY)
- **PHRAZE_PUBLIC_KEY**: Currently has test key, needs real Phraze.so key from Harshit
- **CALLBACK_HMAC_SECRET**: Has test value, needs coordinated production value with Harshit

---

## Architecture Overview

### Two-Phase Video Processing
1. **Sync.so (Lip-sync)**: User adds audio segments → Sync.so processes lip-sync
2. **GhostCut (Text Removal)**: If user adds erasure areas → Chain to GhostCut after Sync.so completes

### Processing Flow
```
Phraze.so → JWT Token → Metafrazo Editor (iframe) → Submit Job
                                                      ↓
                                              Sync.so Processing
                                                      ↓
                                              GhostCut Processing (if needed)
                                                      ↓
                                              Upload to S3
                                                      ↓
                                              Callback to Phraze.so
```

### Celery Workers
- **Worker**: Processes video jobs (Sync.so polling, GhostCut polling)
- **Beat**: Schedules periodic tasks (check job completion every 30 seconds)
- Task file: `backend/workers/embedded_tasks.py`

---

## Key Files Reference

### Backend
| File | Description |
|------|-------------|
| `backend/config.py` | Configuration including `CALLBACK_BASE_URL` |
| `backend/auth/phraze/` | JWT validation and callback service |
| `backend/api/routes/embedded/` | Embedded API routes |
| `backend/workers/embedded_tasks.py` | Celery tasks for polling and callbacks |
| `backend/services/embedded_processing.py` | Embedded processing service |

### Frontend
| File | Description |
|------|-------------|
| `frontend/src/pages/embedded/` | Embedded editor page |
| `frontend/src/services/embeddedApi.ts` | API service for embedded endpoints |
| `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` | Job submission hook |

### Documentation
| File | Description |
|------|-------------|
| `docs/PHRAZE_INTEGRATION_GUIDE.md` | Integration guide for Phraze.so developer |
| `docs/RAILWAY_ENVIRONMENT_VARIABLES.md` | Railway env vars documentation |

---

## Railway Services Reference

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://backend-production-268a.up.railway.app | Deploying |
| Frontend | https://frontend-production-b02b.up.railway.app | Deploying |
| PostgreSQL | Internal Railway connection | Connected |
| Redis | Internal Railway connection | Connected |

---

## JWT Authentication

Phraze.so signs JWT tokens with RS256 (RSA private key)
Metafrazo verifies with RS256 (RSA public key from `PHRAZE_PUBLIC_KEY` env var)

JWT payload includes:
- `user_id` - Phraze.so user ID
- `job_id` - Phraze.so job ID
- `video_url` - S3 URL of video to edit
- `callback_url` - URL to send completion/failure callbacks
- `exp` - Expiration timestamp

---

## Callback Format

**Completion callback:**
```json
{
  "event": "job.completed",
  "job_id": "phraze-job-uuid",
  "output_url": "https://s3.amazonaws.com/bucket/output.mp4",
  "processing_time_seconds": 120,
  "metadata": {...}
}
```

**Failure callback:**
```json
{
  "event": "job.failed",
  "job_id": "phraze-job-uuid",
  "error_code": "SYNC_FAILED",
  "error_message": "Lip-sync processing failed",
  "processing_time_seconds": 30
}
```

---

## Testing the Embedded Editor Locally or on Railway

### Using the JWT Token Generation Script
```bash
# Generate a test JWT token
python scripts/generate_jwt_token.py

# Output will show test URLs
# Railway: https://frontend-production-b02b.up.railway.app/editor/embedded?token=<token>
# Local:   http://localhost:3001/editor/embedded?token=<token>
```

### Testing Workflow
1. Copy the token from script output
2. Paste full URL into browser (includes token as query parameter)
3. Frontend validates token with backend
4. Backend returns validation response with video URL
5. Embedded editor loads and displays video for editing

### What Works Now
- JWT token generation with RS256 signature
- Backend token validation
- Embedded editor UI loads correctly
- Video loads from S3
- (Two-phase processing not yet tested end-to-end)

---

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | Fixed EmbeddedEditorPage import (line 25) |
| `keys/phraze_private.pem` | NEW - RSA private key for JWT signing |
| `keys/phraze_public.pem` | NEW - RSA public key for JWT verification |
| `scripts/generate_jwt_token.py` | NEW - Script to generate test JWT tokens |

## GitHub Repository & Commits

- Repository: `https://github.com/lisperz/metafrazo-platform`
- Branch: `main`
- Latest commits:
  - `074b29d` - Fix EmbeddedEditorPage import from named to default export
  - `5035464` - Add JWT token generation script and force frontend rebuild

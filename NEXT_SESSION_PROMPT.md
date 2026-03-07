# Next Session Context - MetaFrazo Platform

**Last Updated:** March 7, 2026
**Current Branch:** `develop` (ready to merge to main)
**Current Status:** ✅ Callback system working, Phraze.so integration fully functional

---

## Project Overview

**MetaFrazo** - Video Editor Platform (editor.phraze.so)
**Tech Stack:** FastAPI + React 19 + Celery + PostgreSQL + Redis + AWS S3
**Deployment:** Railway (https://railway.app)
**Repository:** https://github.com/lisperz/metafrazo-platform

**Services on Railway:**
1. backend (FastAPI)
2. worker (Celery worker)
3. beat (Celery beat scheduler) - **Critical for callbacks**
4. frontend (React)
5. PostgreSQL
6. Redis

---

## Latest Session: Phraze.so Integration Fix (March 7, 2026)

### Problem Summary

Jobs completed in MetaFrazo but Phraze.so (Cadence) showed "Completed - Final video not available" because:
1. Callbacks were not being sent to Phraze.so
2. `final_video_url` was NULL in Cadence MySQL
3. Status mismatch between two systems

### Root Cause

Callback system was implemented but not properly configured in Railway deployment:
- Missing `PHRAZE_CALLBACK_URL` environment variable in beat and worker services
- Celery beat was running but couldn't send callbacks without the URL

### Solution Implemented

#### 1. Railway Environment Variables Updated

Added to **both beat and worker services:**
```bash
PHRAZE_CALLBACK_URL=https://699f-76-191-26-60.ngrok-free.app/api/editor/callback
PHRAZE_DOMAIN=phraze.so
EMBEDDED_MODE=true
```

**Note:** Using ngrok to expose local Cadence for testing. For production:
```bash
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
```

#### 2. Verified Callback System Working

**Celery Beat Schedule:**
- Task: `check_embedded_job_completion`
- Frequency: Every 30 seconds
- Function: Polls PostgreSQL for completed embedded jobs
- Action: Sends HTTP POST to Phraze.so callback URL

**Callback Payload:**
```json
{
  "job_id": "phraze-job-id",
  "status": "completed",
  "output_url": "https://s3.amazonaws.com/...",
  "processing_time_seconds": 123,
  "metadata": {
    "segments_data": [...],
    "effects_data": [...]
  }
}
```

#### 3. Created Retroactive Sync Script

**Script:** `scripts/send_retroactive_callbacks.py`
- Queries PostgreSQL for completed embedded jobs
- Sends callbacks for jobs that completed before callback URL was configured
- Successfully synced 6 jobs to Phraze.so

---

## Integration Architecture

### Two-System Integration

**MetaFrazo (this platform):**
- Receives JWT token from Phraze.so
- Validates token using Phraze.so public key
- Processes video (lip-sync, text removal)
- Stores output in AWS S3
- Sends callback to Phraze.so when complete

**Phraze.so (Cadence):**
- Generates JWT token with callback URL
- User opens MetaFrazo editor with token
- Receives callback when processing completes
- Updates MySQL with final_video_url
- Shows "Download Final Video" button in UI

### Integration Flow

```
1. Phraze.so generates JWT token
   - Includes: job_id, video_url, callback_url, permissions
   - Signed with RSA private key

2. User opens MetaFrazo editor
   - URL: https://editor.phraze.so/editor/embedded?token={jwt}
   - MetaFrazo validates token with Phraze.so public key

3. Video processing
   - Celery worker processes video
   - Job status: queued → processing → completed
   - Output stored in AWS S3

4. Callback sent
   - Celery beat detects completion (every 30s)
   - Worker sends POST to callback_url
   - Phraze.so updates database

5. UI updates
   - Phraze.so shows "Download Final Video" button
   - User can download processed video
```

---

## Database Schema

### PostgreSQL (Railway)

**Connection:** Get from Railway dashboard → PostgreSQL service → Variables tab

**Public URL Format:**
```
postgresql://postgres:PASSWORD@ballast.proxy.rlwy.net:PORT/railway
```

**Key Tables:**
- `video_jobs` - All video processing jobs
- `is_embedded_job = true` - Jobs from Phraze.so integration
- `output_url` - Final video URL (S3)
- `job_metadata` - Contains `phraze_job_id` for matching

**Job Status Values:**
- `queued` - Waiting to be processed
- `processing` - Currently being processed
- `completed` - Processing finished successfully
- `failed` - Processing failed

---

## Celery Configuration

### Beat Schedule (Periodic Tasks)

**File:** `backend/workers/celery_app.py`

**Key Tasks:**
```python
'check-embedded-job-completion': {
    'task': 'backend.workers.embedded_tasks.check_embedded_job_completion',
    'schedule': 30.0,  # Every 30 seconds
}
```

**What it does:**
1. Queries PostgreSQL for embedded jobs with `status = 'completed'`
2. Checks if callback was already sent
3. Sends HTTP POST to Phraze.so callback URL
4. Updates job with `callback_sent = true`

### Worker Configuration

**File:** `backend/workers/embedded_tasks.py`

**Callback Function:**
```python
@celery_app.task
def send_callback_to_phraze(job_id, phraze_job_id, output_url):
    callback_url = settings.phraze_callback_url
    payload = {
        "job_id": phraze_job_id,
        "status": "completed",
        "output_url": output_url,
        "processing_time_seconds": ...
    }
    response = requests.post(callback_url, json=payload)
```

---

## Railway Deployment

### Services Configuration

**1. Backend Service**
- Dockerfile: `Dockerfile.backend`
- Config: `railway.backend.toml`
- Command: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`

**2. Worker Service**
- Dockerfile: `Dockerfile.worker`
- Config: `railway.worker.toml`
- Command: `celery -A backend.workers.celery_app worker -l info`
- **Requires:** `PHRAZE_CALLBACK_URL` environment variable

**3. Beat Service** ⭐ **Critical for callbacks**
- Dockerfile: `Dockerfile.beat`
- Config: `railway.beat.toml`
- Command: `celery -A backend.workers.celery_app beat -l info`
- **Requires:** `PHRAZE_CALLBACK_URL` environment variable

**4. Frontend Service**
- Dockerfile: `Dockerfile.frontend`
- Config: `railway.frontend.toml`
- Serves React app via Nginx

### Environment Variables

**Required for Callback System:**
```bash
# Phraze.so Integration
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_DOMAIN=phraze.so
PHRAZE_PUBLIC_KEY=<RSA public key>
EMBEDDED_MODE=true

# Database (auto-set by Railway)
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=taylorswiftnyu
AWS_REGION=us-east-2

# External APIs
SYNC_API_KEY=...
GHOSTCUT_API_KEY=...
GHOSTCUT_APP_SECRET=...
GHOSTCUT_UID=...
```

---

## Scripts Created

### New Scripts (in `/scripts` directory)

1. **`send_retroactive_callbacks.py`** - Send callbacks for jobs completed before callback URL was configured
2. **`start-beat.sh`** - Start Celery beat locally for testing

### Existing Scripts

- `start-backend.sh` - Start FastAPI backend
- `start-frontend.sh` - Start React frontend
- `start-worker.sh` - Start Celery worker

---

## Documentation Created

1. **`CALLBACK_TROUBLESHOOTING.md`** - Callback system troubleshooting guide
2. **`RAILWAY_BEAT_FIX.md`** - Railway beat service deployment guide
3. **`RAILWAY_VERIFICATION_CHECKLIST.md`** - Railway deployment verification checklist
4. **`docs/SYSTEM_ARCHITECTURE_DIAGRAMS.md`** - System architecture diagrams
5. **`NEXT_SESSION_PROMPT.md`** - This file (updated)

---

## Previous Session: Codebase Cleanup (February 24, 2026)

### What Was Done

Major cleanup of redundant files from the local repo, followed by fixing Railway deployment errors.

### Files Removed (Commit a060fc2)

1. Duplicate files with "(1)" suffix
2. `.backup` files
3. `_backup_original/` directory
4. Unused `*_original.py` files (dead code)
5. Root-level standalone Python scripts
6. Orphaned frontend pages
7. Root-level docs (moved to `docs/`)
8. Old untracked backend files
9. Misc test files and build artifacts
10. **Security:** `harshilsuvarna_accessKeys.csv` (exposed AWS key - **rotation required**)

### Files Restored (Commit 6dd9e43)

4 files with `*_original.py` naming were **not backups** but actively imported production routes:
1. `backend/api/routes/test_login_debug.py`
2. `backend/api/routes/jobs/management/jobs_original.py`
3. `backend/api/routes/jobs/processing/direct_process_original.py`
4. `backend/api/routes/video_editors/sync/sync_api_original.py`

### Lessons Learned

- Files named `*_original.py` can be production code, not just backups
- Always trace imports before deleting: `grep -r "import.*_original" backend/`

---

## Open Issue: Speaker Detection Quality

### Problem Summary

Speaker detection (bounding box) implementation is functionally correct end-to-end, but the output video quality from Sync.so is not satisfactory.

### What Works

- Frontend sends `speakerBox` with normalized coordinates per segment
- Backend `build_bounding_boxes()` correctly converts to per-frame pixel arrays
- Sync.so API payload includes `options.active_speaker_detection.bounding_boxes`

### Still Needs Investigation

1. What specific issue in the output? (wrong person, no lip-sync, poor quality?)
2. Is the bounding box tight enough around the speaker's face?
3. Does the speaker move outside the fixed box during the segment?
4. How does Sync.so interpret the bounding_boxes parameter?

### Key Files

- `backend/services/sync_segments_service.py` - `build_bounding_boxes()` function
- `backend/services/embedded_processing.py` - Sync.so generation with video_metadata
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` - sends speakerBox to API
- `frontend/src/store/segmentsStore.ts` - stores segment.speakerBox

---

## Current System State

### ✅ Working Correctly

1. **Callback System:**
   - Beat service running and scheduling tasks every 30s
   - Worker service sending callbacks to Phraze.so
   - Callbacks successfully received and processed
   - New jobs automatically trigger callbacks

2. **Video Processing:**
   - Lip-sync dubbing via Sync.so API
   - Text removal via GhostCut API
   - Output stored in AWS S3
   - Embedded jobs tracked in PostgreSQL

3. **JWT Authentication:**
   - Token validation with Phraze.so public key
   - Secure access to embedded editor
   - Callback URL included in token payload

### 🔧 Configuration

**Railway Environment Variables (beat & worker):**
```bash
PHRAZE_CALLBACK_URL=https://699f-76-191-26-60.ngrok-free.app/api/editor/callback
```

**For Production:**
```bash
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
```

---

## For Next Session

### If Callbacks Stop Working

1. **Check Railway environment variables:**
   - Beat service has `PHRAZE_CALLBACK_URL`
   - Worker service has `PHRAZE_CALLBACK_URL`
   - Both services restarted after variable update

2. **Check Railway logs:**
   ```bash
   railway logs --service beat
   railway logs --service worker
   ```

3. **Test callback endpoint:**
   ```bash
   curl -X POST https://phraze.so/api/editor/callback \
     -H "Content-Type: application/json" \
     -d '{"job_id":"test","status":"completed","output_url":"https://s3.amazonaws.com/test.mp4"}'
   ```

4. **Run retroactive sync:**
   ```bash
   cd /Users/zhuchen/Downloads/metafrazo-platform
   python scripts/send_retroactive_callbacks.py
   ```

### If ngrok URL Changes

1. Update Railway environment variables in beat and worker services
2. Restart both services
3. Test with new job submission

### Before Deploying to Production

1. Update `PHRAZE_CALLBACK_URL` to production domain
2. Verify Phraze.so is accessible at `https://phraze.so`
3. Test complete flow with real job
4. Monitor logs for any errors

---

## Git Workflow

**Current Branch:** `develop`
**Main Branch:** `main` (production)
**Repository:** https://github.com/lisperz/metafrazo-platform

**Workflow:**
1. Develop on `develop` branch
2. Test thoroughly
3. Merge to `main` for production deployment

---

## Action Items

- [ ] Rotate AWS access key `AKIAQSJTZYWNZBAKB7NB` (exposed in deleted CSV file)
- [ ] Investigate speaker detection output quality with Sync.so
- [ ] Consider refactoring `backend/workers/video_tasks/pro_jobs.py` (~700 lines, exceeds 300-line limit)
- [ ] Consider renaming `*_original.py` files to avoid confusion
- [ ] Update Railway callback URL to production domain before production deployment

---

## Key Files & Locations

**Project Location:** `/Users/zhuchen/Downloads/metafrazo-platform`
**Related Project:** Cadence (Phraze.so) at `/Users/zhuchen/Downloads/cadence`

**Critical Files:**
- `backend/workers/celery_app.py` - Celery configuration and beat schedule
- `backend/workers/embedded_tasks.py` - Callback sending logic
- `backend/services/embedded_processing.py` - Embedded job processing
- `backend/auth/phraze/validator.py` - JWT token validation
- `backend/auth/phraze/callback_service.py` - Callback service

**Configuration:**
- `railway.beat.toml` - Beat service configuration
- `railway.worker.toml` - Worker service configuration
- `Dockerfile.beat` - Beat service Docker image
- `Dockerfile.worker` - Worker service Docker image

---

**Status:** ✅ Callback system working, integration with Phraze.so fully functional, ready for production deployment

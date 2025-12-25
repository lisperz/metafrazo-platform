# Next Session Context - Phraze.so Integration

**Last Updated**: December 25, 2025
**Current Status**: **Phase 4 COMPLETE - Full Phraze.so Integration Working End-to-End**

---

## What Was Completed This Session (Dec 25, 2025)

### 1. Phraze.so Callback Integration - COMPLETE ✅
**Problem**: MetaFrazo sent callbacks via POST, but Phraze.so only handled POST for job creation.

**Solution**: Modified Phraze.so's `/api/open/editor-jobs` endpoint to handle both:
- Job creation (when request has `user_id` + `video_url`)
- Callbacks (when request has `job_id` + `status`)

**File Modified**: `/Users/zhuchen/Downloads/cadence/src/app/api/open/editor-jobs/route.ts`
- Added status mapping: `'started' → 'processing'` to match database constraints
- Added callback detection logic
- Added comprehensive logging for debugging

### 2. Fixed Segment Audio Timing Issue ✅
**Problem**: Output video duration didn't match input because audio crop times didn't match video segment times.

**Root Cause**: When segments were dragged/resized, audio `endTime` was using audio file duration instead of video segment `endTime`.

**Solution**: Force audio times to ALWAYS match video segment times in:
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` - At submission
- `frontend/src/components/VideoEditor/Pro/hooks/useSegmentHandlers.ts` - During drag/resize
- `frontend/src/store/segmentsStore.ts` - During segment split

**Result**: Output video duration now matches input segment duration perfectly (no more "remap" issues).

### 3. Database Schema Fixes ✅
- Created `scripts/fix_railway_db.py` to add missing columns:
  - `segments_data`, `job_metadata`, `is_embedded_job`, `is_pro_job`
- Removed NOT NULL constraint from `user_id` for embedded jobs
- Created embedded user with ID `03139de3-8cc6-4702-a2fd-048dff642ccb`

### 4. Local Testing Infrastructure ✅
- Created `scripts/test_phraze_callback_flow.py` for end-to-end testing
- Set up ngrok testing with local Phraze.so instance
- Created comprehensive documentation:
  - `docs/PHRAZE_CALLBACK_FIX_SUMMARY.md`
  - `docs/TESTING_PHRAZE_INTEGRATION.md`
  - `docs/CALLBACK_SETUP_GUIDE.md`
  - `docs/LOCAL_TESTING_GUIDE.md`
  - `examples/phraze-callback-endpoint.js`

---

## Current State - What Works

### ✅ Complete End-to-End Flow
1. **Phraze.so creates editing job** → Stores in MySQL database
2. **Phraze.so generates JWT token** → Includes job_id, video_url, callback_url
3. **User opens embedded editor** → MetaFrazo validates JWT token
4. **User edits video** → Adds audio segments, adjusts timing
5. **User submits job** → MetaFrazo processes with Sync.so
6. **MetaFrazo sends callbacks**:
   - `status: 'started'` → Phraze.so updates to `'processing'`
   - `status: 'completed'` → Phraze.so updates with `output_url`
7. **Phraze.so database updated** → Job shows completed with output video URL

### ✅ Video Processing
- Sync.so lip-sync processing working
- GhostCut text removal working (when erasure areas added)
- Two-phase processing (lip-sync → text removal)
- Output videos uploaded to S3
- Processing time tracked correctly

### ✅ Callback System
- POST callbacks handled correctly
- PUT callbacks handled correctly (legacy)
- Status mapping working (`started` → `processing`)
- Timestamps set automatically (`started_at`, `completed_at`)
- Error handling for failed jobs

---

## Architecture Overview

### System Components
```
┌─────────────────────────────────────────────────────────────┐
│  Phraze.so (Next.js + MySQL)                                 │
│  - Creates editor jobs in database                           │
│  - Generates JWT tokens (RS256)                              │
│  - Receives callbacks via /api/open/editor-jobs              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ JWT Token
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  MetaFrazo (FastAPI + PostgreSQL + Redis)                   │
│  Frontend: https://frontend-production-b02b.up.railway.app   │
│  Backend:  https://backend-production-268a.up.railway.app    │
│  - Validates JWT tokens                                      │
│  - Processes videos (Sync.so + GhostCut)                     │
│  - Sends callbacks to Phraze.so                              │
└─────────────────────────────────────────────────────────────┘
```

### Processing Flow
```
User → Embedded Editor → Submit Job
                           ↓
                    Upload Audio to S3
                           ↓
                    Sync.so Lip-Sync
                           ↓
          (if erasure areas) → GhostCut Text Removal
                           ↓
                    Upload Output to S3
                           ↓
              Send Callback to Phraze.so (POST)
                           ↓
              Phraze.so Updates Job Status
```

---

## Key Files Reference

### MetaFrazo Platform
| File | Description |
|------|-------------|
| `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` | Job submission (forces audio times = video times) |
| `frontend/src/components/VideoEditor/Pro/hooks/useSegmentHandlers.ts` | Drag/resize handlers (syncs audio times) |
| `frontend/src/store/segmentsStore.ts` | Segment store (syncs audio times on split) |
| `backend/api/routes/embedded/routes.py` | Embedded API routes (job submission) |
| `backend/workers/embedded_tasks.py` | Celery tasks (processing + callbacks) |
| `scripts/test_phraze_callback_flow.py` | End-to-end testing script |
| `scripts/fix_railway_db.py` | Database schema fix script |
| `scripts/create_embedded_user.py` | Create embedded user script |

### Phraze.so (Cadence Repo)
| File | Description |
|------|-------------|
| `/Users/zhuchen/Downloads/cadence/src/app/api/open/editor-jobs/route.ts` | Callback endpoint (handles POST/PUT) |

---

## Environment Variables (Railway Backend)

### Production Configuration ✓
- `ENVIRONMENT=production` - Enables JWT signature verification
- `PHRAZE_PUBLIC_KEY` - RSA public key from Phraze.so for JWT validation
- `CALLBACK_HMAC_SECRET` - Shared secret for callback signature validation
- `DATABASE_URL` - PostgreSQL on Railway
- `REDIS_URL` - Redis on Railway
- `AWS_*` - S3 credentials for video upload
- `SYNC_API_KEY` - Sync.so API key for lip-sync
- `GHOSTCUT_*` - GhostCut API keys for text removal
- `FRONTEND_URL` - https://frontend-production-b02b.up.railway.app
- `CORS_ORIGINS` - Includes phraze.so domain

---

## Local Testing with Phraze.so

### Setup
1. **Start Phraze.so locally**:
   ```bash
   cd /Users/zhuchen/Downloads/cadence
   npm run dev  # Runs on localhost:3000
   ```

2. **Start ngrok tunnel**:
   ```bash
   ngrok http 3000
   # Copy the https URL (e.g., https://abc123.ngrok.io)
   ```

3. **Run test script**:
   ```bash
   cd /Users/zhuchen/Downloads/metafrazo-platform
   python3 scripts/test_phraze_callback_flow.py https://abc123.ngrok.io
   ```

4. **Open Railway URL** from script output and test the workflow

### Testing Workflow
- Script creates job in Phraze.so database
- Generates JWT token for that job
- Outputs Railway frontend URL with token
- Open URL → Edit video → Submit
- Watch Phraze.so terminal for callbacks
- Verify database updates with job status and output URL

---

## Important Notes for Next Session

### Segment Audio Timing (CRITICAL)
**ALWAYS ensure audio crop times match video segment times** to prevent output duration mismatches.

This is enforced in:
- Submission (`useVideoSubmission.ts`)
- Drag/resize (`useSegmentHandlers.ts`)
- Split (`segmentsStore.ts`)

### Callback Endpoint Design
Phraze.so's `/api/open/editor-jobs` endpoint handles both:
- **Job creation**: `POST` with `user_id` + `video_url`
- **Callbacks**: `POST` or `PUT` with `job_id` + `status`

Status mapping: `started` → `processing` (database constraint)

### Database Constraints
Phraze.so database has CHECK constraint `valid_status`:
- Allowed values: `'pending'`, `'editing'`, `'processing'`, `'completed'`, `'failed'`
- MetaFrazo must map status values accordingly

---

## GitHub Repository

- **Repository**: https://github.com/lisperz/metafrazo-platform
- **Branch**: `main`
- **Latest Commit**: Fix segment audio times to always match video segment times

---

## Next Steps (If Needed)

### Production Deployment
1. Deploy updated Phraze.so code to production (phraze.so domain)
2. Ensure production Phraze.so generates JWT tokens with correct callback URL
3. Test end-to-end with production Phraze.so instance

### Monitoring
- Monitor callback logs in Phraze.so production
- Monitor job processing in MetaFrazo Railway logs
- Track job completion rates and processing times

### Optional Enhancements
- Add webhook retry logic for failed callbacks
- Add job status polling endpoint for Phraze.so
- Add processing progress updates (currently only start/complete/failed)

---

*All core functionality is working. Integration is production-ready.*

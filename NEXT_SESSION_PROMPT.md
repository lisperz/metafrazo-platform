# Next Session Context - MetaFrazo Platform

**Last Updated**: December 26, 2025
**Current Status**: **Phase 4 COMPLETE - Full Production Integration with editor.phraze.so**

---

## What Was Completed This Session (Dec 26, 2025)

### 1. Fixed editor.phraze.so API URL Detection ✅
**Problem**: Frontend worked on Railway URL but failed on `editor.phraze.so` with "VALIDATION_FAILED" error.

**Root Cause**: Frontend `api.ts` only detected Railway URLs, not phraze.so domains.

**Solution**: Modified `frontend/src/services/api.ts`:
```typescript
const isProduction = typeof window !== 'undefined' && (
  window.location.hostname.includes('railway.app') ||
  window.location.hostname.includes('phraze.so')  // ← Added this
);
```

**Result**: `editor.phraze.so` now correctly calls Railway backend instead of itself.

### 2. Updated Test Script for editor.phraze.so ✅
**File**: `scripts/test_phraze_callback_flow.py`

**Changes**:
- Added `editor.phraze.so` as primary production URL
- Kept Railway URL as backup
- Updated documentation to reference editor.phraze.so

**Output URLs**:
1. **Production**: `https://editor.phraze.so/editor/embedded?token=...` (recommended)
2. **Backup**: `https://frontend-production-b02b.up.railway.app/editor/embedded?token=...`
3. **Local**: `http://localhost:3001/editor/embedded?token=...`

### 3. Created Phraze.so Editor Jobs Implementation Plan ✅
**Purpose**: Enable Phraze.so users to upload videos for AI editing.

**Document**: `/Users/zhuchen/Downloads/cadence/EDITOR_JOBS_IMPLEMENTATION_PLAN.md`

**Key Features**:
- Video upload to S3
- JWT token generation
- Redirect to editor.phraze.so
- Job status tracking (pending → editing → processing → completed)
- Download completed videos from S3

**Implementation Status**: **Documented, ready for implementation in Phraze.so repo**

---

## Current Production URLs

### MetaFrazo Platform (Railway)
- **Frontend**: https://frontend-production-b02b.up.railway.app
- **Backend**: https://backend-production-268a.up.railway.app
- **Embedded Editor**: https://editor.phraze.so (Cloudflare subdomain → Railway frontend)

### Phraze.so Platform
- **Main Site**: https://phraze.so
- **Editor Subdomain**: https://editor.phraze.so (points to MetaFrazo Railway frontend)
- **Callback Endpoint**: https://phraze.so/api/open/editor-jobs (or ngrok in testing)

---

## Complete Working Flow (End-to-End)

### From Phraze.so:
1. User creates editor job in Phraze.so → Stores in MySQL
2. Phraze.so generates JWT token → Includes job_id, video_url, callback_url
3. User redirected to `https://editor.phraze.so/editor/embedded?token=...`

### In MetaFrazo:
4. MetaFrazo validates JWT token (RS256 with Phraze public key)
5. User edits video → Adds audio segments, sets erasure areas
6. User submits → MetaFrazo uploads audio to S3
7. Celery worker processes → Sync.so lip-sync → GhostCut text removal
8. MetaFrazo sends callbacks to Phraze.so callback URL:
   - `status: 'started'` → Phraze updates to `'processing'`
   - `status: 'completed'` → Phraze updates with `output_url`

### Back to Phraze.so:
9. Phraze.so database updated with job status and output video URL
10. User downloads completed video from S3

---

## Key Technical Achievements

### ✅ Segment Audio Timing Fix (Dec 25)
**Critical Fix**: Audio crop times now ALWAYS match video segment times to prevent output duration mismatches.

**Enforced in**:
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` - At submission
- `frontend/src/components/VideoEditor/Pro/hooks/useSegmentHandlers.ts` - During drag/resize
- `frontend/src/store/segmentsStore.ts` - During segment split

### ✅ Callback System (Dec 25)
- POST/PUT callbacks handled by Phraze.so `/api/open/editor-jobs`
- Status mapping: `started` → `processing` (database constraint)
- Automatic timestamps for `started_at`, `completed_at`, `callback_received_at`

### ✅ Multi-Domain Support (Dec 26)
- Railway URL: `frontend-production-b02b.up.railway.app`
- Phraze.so subdomain: `editor.phraze.so`
- Both call same Railway backend API

---

## Environment Variables (Railway Backend)

### Production Configuration
```bash
ENVIRONMENT=production
PHRAZE_PUBLIC_KEY=<RSA public key from Phraze.so>
CALLBACK_HMAC_SECRET=<shared secret>
DATABASE_URL=<PostgreSQL on Railway>
REDIS_URL=<Redis on Railway>
AWS_REGION=us-east-2
AWS_ACCESS_KEY_ID=<S3 credentials>
AWS_SECRET_ACCESS_KEY=<S3 credentials>
AWS_S3_BUCKET=taylorswiftnyu
SYNC_API_KEY=<Sync.so API key>
GHOSTCUT_API_KEY=<GhostCut API key>
GHOSTCUT_API_SECRET=<GhostCut API secret>
CORS_ORIGINS=https://phraze.so,https://frontend-production-b02b.up.railway.app,https://editor.phraze.so
```

---

## Testing

### Local Testing with Phraze.so
```bash
# Terminal 1: Start Phraze.so
cd /Users/zhuchen/Downloads/cadence
npm run dev  # localhost:3000

# Terminal 2: Start ngrok
ngrok http 3000  # Copy the HTTPS URL

# Terminal 3: Run test script
cd /Users/zhuchen/Downloads/metafrazo-platform
python3 scripts/test_phraze_callback_flow.py https://YOUR-NGROK-URL.ngrok.io

# Open the editor.phraze.so URL from script output
```

### Production Testing
```bash
# Just run the test script with Phraze.so production URL
python3 scripts/test_phraze_callback_flow.py https://phraze.so
```

---

## Key Files

### MetaFrazo Platform (This Repo)
| File | Purpose |
|------|---------|
| `frontend/src/services/api.ts` | API URL detection (Railway + phraze.so) |
| `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` | Job submission with audio timing fix |
| `backend/api/routes/embedded/routes.py` | Embedded API routes |
| `backend/workers/embedded_tasks.py` | Celery tasks for processing + callbacks |
| `backend/auth/phraze/validator.py` | JWT token validation |
| `scripts/test_phraze_callback_flow.py` | End-to-end testing script |

### Phraze.so Platform (Cadence Repo)
| File | Purpose |
|------|---------|
| `/Users/zhuchen/Downloads/cadence/src/app/api/open/editor-jobs/route.ts` | Callback endpoint (POST/PUT) |
| `/Users/zhuchen/Downloads/cadence/EDITOR_JOBS_IMPLEMENTATION_PLAN.md` | Complete implementation guide for Editor Jobs feature |

---

## Next Steps

### For Phraze.so (Cadence Repo)
**Implement Editor Jobs Feature** using `/Users/zhuchen/Downloads/cadence/EDITOR_JOBS_IMPLEMENTATION_PLAN.md`:
1. Create JWT keys (`keys/phraze_private.pem`, `keys/phraze_public.pem`)
2. Create upload endpoint (`src/app/api/translator/upload-video/route.ts`)
3. Create job management endpoint (`src/app/api/translator/editor-jobs/route.ts`)
4. Create frontend page (`src/app/dashboard/translator/editor-jobs/page.tsx`)
5. Update navigation (`src/app/dashboard/translator/layout.tsx`)

**Estimated Time**: 2-3 hours

### For MetaFrazo (This Repo)
**Status**: ✅ Complete - No changes needed

The platform is production-ready and working end-to-end with both:
- `https://editor.phraze.so` (production)
- `https://frontend-production-b02b.up.railway.app` (backup)

---

## GitHub Repository

- **Repository**: https://github.com/lisperz/metafrazo-platform
- **Branch**: `main`
- **Latest Changes**: Fixed API URL detection for editor.phraze.so domain

---

*All MetaFrazo platform functionality is complete and production-ready.*

# Next Session Context - MetaFrazo Platform

**Last Updated**: December 27, 2025
**Current Status**: **Phase 5 COMPLETE - Editor Jobs Feature Fully Implemented in Phraze.so**

---

## What Was Completed (Dec 26-27, 2025)

### 1. Full Editor Jobs Feature Implementation in Phraze.so (Cadence Repo) ✅

**Complete end-to-end video editing workflow implemented:**

- **Video Upload**: Users can upload videos directly to S3 via presigned URLs
- **S3 URL Input**: Users can also paste existing S3 video URLs to start editing
- **Job Name**: Users can set custom job names (defaults to filename if empty)
- **Job ID Format**: Sequential "EJ-1", "EJ-2", etc. per user (not UUID)
- **JWT Token Generation**: Secure tokens for MetaFrazo editor authentication
- **Status Tracking**: pending → editing → processing → completed/failed
- **Callback Handling**: Railway backend sends status updates to Phraze.so
- **Download**: Completed videos downloadable from S3

### 2. Database Schema Updates ✅

**Migration**: `src/migrations/20241227_add_editor_job_number_and_name.sql`

Added columns to `editor_jobs` table:
- `job_number` - Auto-incrementing sequential number per user
- `video_name` - User-defined job name

### 3. S3 CORS Configuration ✅

Updated S3 CORS to allow uploads from:
- `http://localhost:3000`
- `https://phraze.so`
- `https://editor.phraze.so`
- `https://*.ngrok-free.app` (for local testing)

### 4. ngrok Setup for Local Testing ✅

**Purpose**: Railway backend cannot callback to localhost:3000 directly.

**Solution**: Use ngrok to expose local Phraze.so for callbacks:
```bash
ngrok http 3000
# Update .env.local with ngrok URL:
# NEXT_PUBLIC_APP_URL=https://YOUR-NGROK-URL.ngrok-free.app
```

---

## Current Production URLs

### MetaFrazo Platform (Railway)
- **Frontend**: https://frontend-production-b02b.up.railway.app
- **Backend**: https://backend-production-268a.up.railway.app
- **Embedded Editor**: https://editor.phraze.so

### Phraze.so Platform
- **Main Site**: https://phraze.so
- **Editor Subdomain**: https://editor.phraze.so (points to MetaFrazo Railway frontend)
- **Callback Endpoint**: https://phraze.so/api/open/editor-jobs

---

## Complete Working Flow (End-to-End)

### From Phraze.so:
1. User goes to Jobs page → Editor Jobs tab
2. User enters job name (optional) and uploads video OR pastes S3 URL
3. Video uploaded to S3 via presigned URL
4. Editor job created in MySQL with auto-generated job_number
5. JWT token generated with job_id, video_url, callback_url
6. User redirected to `https://editor.phraze.so/editor/embedded?token=...`

### In MetaFrazo:
7. MetaFrazo validates JWT token (RS256 with Phraze public key)
8. User edits video → Adds audio segments, sets erasure areas
9. User submits → MetaFrazo uploads audio to S3
10. Celery worker processes → Sync.so lip-sync → GhostCut text removal
11. MetaFrazo sends callbacks to Phraze.so callback URL

### Back to Phraze.so:
12. Callback updates job status in MySQL (processing → completed)
13. User sees updated status in Jobs page
14. User downloads completed video from S3

---

## Key Files

### MetaFrazo Platform (This Repo)
| File | Purpose |
|------|---------|
| `frontend/src/services/api.ts` | API URL detection (Railway + phraze.so) |
| `frontend/src/services/embeddedApi.ts` | Redirect functions with job submission params |
| `frontend/src/components/VideoEditor/GhostCutVideoEditor.tsx` | Editor component with submit handler |
| `backend/workers/embedded_tasks.py` | Celery tasks for processing + callbacks |
| `backend/auth/phraze/validator.py` | JWT token validation |

### Phraze.so Platform (Cadence Repo - dev branch)
| File | Purpose |
|------|---------|
| `src/app/api/open/editor-jobs/route.ts` | Open API for job CRUD + callbacks |
| `src/app/api/translator/editor-jobs/generate-token/route.ts` | JWT token generation |
| `src/app/api/translator/upload-video/route.ts` | S3 presigned URL generation |
| `src/app/dashboard/translator/jobs/page.tsx` | Jobs page with Editor Jobs tab |
| `src/migrations/20241227_add_editor_job_number_and_name.sql` | Database migration |
| `scripts/run-migration.js` | Migration runner script |

---

## Testing

### Local Testing with ngrok
```bash
# Terminal 1: Start ngrok
ngrok http 3000

# Terminal 2: Update .env.local with ngrok URL
NEXT_PUBLIC_APP_URL=https://YOUR-NGROK-URL.ngrok-free.app

# Terminal 3: Start Phraze.so
cd /Users/zhuchen/Downloads/cadence
npm run dev

# Open browser: https://YOUR-NGROK-URL.ngrok-free.app/dashboard/translator/jobs
# Switch to "Editor Jobs" tab and test upload/URL input
```

### Production Testing
```bash
# Deploy to production and test at:
https://phraze.so/dashboard/translator/jobs
```

---

## Next Steps

### For Phraze.so Production Deployment
**IMPORTANT**: All changes are in the `dev` branch. To deploy to production:

1. **Merge dev branch to main**:
   ```bash
   git checkout main
   git merge dev
   git push origin main
   ```

2. **Run database migration on production**:
   ```bash
   node scripts/run-migration.js
   ```

3. **Update production environment**:
   - Set `NEXT_PUBLIC_APP_URL=https://phraze.so`

### For MetaFrazo (This Repo)
**Status**: ✅ Complete - No changes needed

---

## GitHub Repositories

- **MetaFrazo**: https://github.com/lisperz/metafrazo-platform (main branch)
- **Phraze.so (Cadence)**: dev branch contains all Editor Jobs changes

---

*Both platforms are fully integrated and ready for production deployment.*

# Next Session Context - MetaFrazo Platform

**Last Updated**: February 23, 2026
**Current Status**: Codebase cleanup completed; speaker detection quality issue still open

---

## Latest Session: Codebase Cleanup (February 23, 2026)

### What Was Done

Major cleanup of redundant files from the local repo. The remote at `https://github.com/lisperz/metafrazo-platform` (branch: `main`) is the source of truth.

### Files Removed

1. **"(1)" duplicate files** (32 files + hundreds in node_modules/.venv) — old copies from file duplication, originals all intact
2. **`.backup` files** (8) — `ghostcut_client.py.backup`, `s3_service.py.backup`, `video_tasks.py.backup`, `ghostcut_tasks.py.backup`, `JobsPage.tsx.backup`, `UploadPage.tsx.backup`, `GhostCutVideoEditor.tsx.backup`, `ProVideoEditor.tsx.backup`
3. **`_backup_original/` directory + `*_original.py` files** (23) — pre-refactor snapshots already in git history
4. **Root-level standalone Python scripts** (11) — `video_processing.py`, `batch_automatic_inpaint.py`, `check_jobs.py`, `ghostcut_api.py`, `dev_server.py`, `start_dev.py`, `zhaoli_processor.py`, `create_client_user.py`, `decode_payload.py`, `test_bounding_box_params.py`, `test_your_payload.py`
5. **Orphaned frontend pages** (16 in `pages/` + 5 in `src/`) — standalone page files not imported by `App.tsx` (which imports from subdirectories like `./pages/dashboard/`, `./pages/video/`, etc.)
6. **Root-level docs** (8) — `EXECUTIVE_PRESENTATION.md`, `NGROK_QUICK_START.md`, `PRODUCTION_DEPLOYMENT_GUIDE.md`, `TECHNICAL_CODE_DOCUMENTATION.md`, `USAGE_GUIDE.md`, `VIDEO_EDITOR_IMPLEMENTATION_PLAN.md`, `DEVELOPMENT_GUIDELINES.md`, `CLAUDE.md` (project instructions remain in `.claude/CLAUDE.md`)
7. **Old untracked backend files** (5) — `backend/services/ghostcut_client.py` (replaced by `ghostcut/client.py`), `backend/services/s3_service.py` (replaced by `s3/service.py`), `backend/api/routes/__init__.py`, `backend/api/routes/jobs.py`, `backend/api/routes/test_login_debug.py`
8. **Misc** — `requirements.txt`, `requirements_clean.txt`, `test_status.html`, `video_inpainting_demo.html`, `zhaoli_config.json`, `.ebextensions/`, `.platform/`, `TestForMyself_Before/` (with ~40 test videos), old build artifacts in `frontend/build/static/js/`
9. **Security** — `harshilsuvarna_accessKeys.csv` (contained plaintext AWS key `AKIAQSJTZYWNZBAKB7NB` — **key rotation in AWS IAM is required**)

### Current Root Directory (Clean)

```
metafrazo-platform/
├── backend/          # FastAPI application
├── database/         # PostgreSQL schema
├── discuss/          # Discussion documents
├── docs/             # Official documentation
├── examples/         # Example files
├── fonts/            # Font assets
├── frontend/         # React 19 + TypeScript
├── keys/             # Key files
├── logs/             # Application logs
├── scripts/          # Run & debug scripts
├── static/           # Static file storage
├── docker-compose.yml
├── Dockerfile.backend / .beat / .frontend / .worker
├── deploy_to_railway.sh
├── nginx.conf / nginx.railway.conf
├── railway.*.toml
├── LICENSE (Apache 2.0)
├── README.md
├── NEXT_SESSION_PROMPT.md
├── RAILWAY_CHECKLIST.md
└── RAILWAY_QUICK_START.md
```

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

- `backend/services/sync_segments_service.py` — `build_bounding_boxes()` function
- `backend/services/embedded_processing.py` — Sync.so generation with video_metadata
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` — sends speakerBox to API
- `frontend/src/store/segmentsStore.ts` — stores segment.speakerBox

---

## Project Architecture

### MetaFrazo Platform (Video Editor)

**Tech Stack**: FastAPI + React 19 + Celery + PostgreSQL + Redis + AWS S3
**Repo**: `https://github.com/lisperz/metafrazo-platform`
**Location**: `/Users/zhuchen/Downloads/metafrazo-platform`
**Production**: `https://frontend-production-b02b.up.railway.app`

### Phraze.so Platform (Client Portal)

**Tech Stack**: Next.js 15 + React 19 + MySQL + Supabase Auth
**Location**: `/Users/zhuchen/Downloads/cadence`
**Domains**: `phraze.so` (prod), `staging.phraze.so`, `dev.phraze.so`

### Integration Flow

```
Phraze.so → JWT Token → MetaFrazo Editor → Sync.so API → Callback → Phraze.so
```

### External APIs

- **Sync.so** — Lip-sync dubbing (segment-based, per-frame bounding boxes)
- **GhostCut/Zhaoli** — Text/watermark removal (MD5 signature auth)
- **AWS S3** — Video/audio file storage

---

## Useful Commands

```bash
# Start MetaFrazo backend
cd /Users/zhuchen/Downloads/metafrazo-platform
./scripts/start-backend.sh

# Start MetaFrazo frontend
./scripts/start-frontend.sh

# Start Celery worker
./scripts/start-worker.sh

# Start Phraze.so (Cadence)
cd /Users/zhuchen/Downloads/cadence
npm run dev
```

---

## Action Items

- [ ] Rotate AWS access key `AKIAQSJTZYWNZBAKB7NB` in IAM console
- [ ] Investigate speaker detection output quality with Sync.so
- [ ] Consider refactoring `backend/workers/video_tasks/pro_jobs.py` (~700 lines, exceeds 300-line limit)

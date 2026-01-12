# Next Session Context - MetaFrazo Platform

**Last Updated**: January 12, 2026
**Current Status**: Speaker-Selection Feature Ready for Implementation

---

## Current Priority: Speaker-Selection Feature (5-Day Implementation)

### Feature Overview

Enable per-segment speaker selection in Pro Video Editor using Sync.so bounding boxes API.

**Key Approach**: Fixed bounding box per segment → Single API call with `bounding_boxes` array

```
Segment 1 frames → [x1,y1,x2,y2] (Speaker A's face)
Gap frames       → null (no lip-sync)
Segment 2 frames → [x1,y1,x2,y2] (Speaker B's face)
```

### Implementation Plan (5 Days)

| Day | Focus | Key Files |
|-----|-------|-----------|
| **Day 1** | Speaker Box Drawing Component | `SpeakerBoxDrawer.tsx`, `speakerStore.ts` |
| **Day 2** | Segment Form Integration | `SegmentForm.tsx`, `types/segments.ts` |
| **Day 3** | Backend Bounding Boxes Builder | `sync_segments_service.py`, `video_utils.py` |
| **Day 4** | Frontend-Backend Integration | `useVideoSubmission.ts`, `processing.py` |
| **Day 5** | Testing & Polish | All scenarios + edge cases |

**Full Details**: See `discuss/speaker-selection-task-breakdown.md`

---

## Project Architecture

### MetaFrazo Platform (Video Editor)

**Tech Stack**: FastAPI + React + Celery + PostgreSQL + AWS S3
**Location**: `/Users/zhuchen/Downloads/metafrazo-platform`

**Key Components**:
- **Frontend**: React 19, Material-UI, Zustand stores
- **Backend**: FastAPI, Celery workers, Sync.so API integration
- **Pro Editor**: Multi-segment lip-sync with timeline (`frontend/src/components/VideoEditor/Pro/`)

### Phraze.so Platform (Client Portal)

**Tech Stack**: Next.js 15 + React 19 + MySQL + Supabase Auth
**Location**: `/Users/zhuchen/Downloads/cadence`

**Key Components**:
- **Editor Jobs**: Embedded video editor integration
- **Feature Flags**: Per-environment user access control (`src/constants/featureFlags.ts`)
- **Domains**: `phraze.so` (prod), `staging.phraze.so`, `dev.phraze.so` (local/ngrok)

### Integration Flow

```
Phraze.so (Client) → JWT Token → MetaFrazo Editor → Process Video → Callback → Phraze.so
```

1. User clicks "Edit Video" in Phraze.so
2. Phraze generates JWT token with job_id, video_url, callback_url
3. MetaFrazo validates token, loads video in Pro Editor
4. User edits (segments, audio, speaker selection)
5. MetaFrazo processes via Sync.so API
6. MetaFrazo sends callback to Phraze with result URL

---

## Environment Configuration

### Phraze.so Environments

**Dev** (`dev.phraze.so`, `localhost`, ngrok):
- User: `03139de3-8cc6-4702-a2fd-048dff642ccb`
- Database: `phraze-dev-instance-1.ccdrwsnbgg82.us-east-2.rds.amazonaws.com`
- Password: `etSipaV_Vwvo>FhC1z[Zs-].~x.f`

**Staging** (`staging.phraze.so`):
- User: `3793b467-c3c0-4982-8d23-1b2a21aafb18`

**Production** (`phraze.so`):
- User: `3793b467-c3c0-4982-8d23-1b2a21aafb18`

### Database Passwords (Updated Jan 2026)

**Phraze Dev DB**:
```
AWS_DB_HOST=phraze-dev-instance-1.ccdrwsnbgg82.us-east-2.rds.amazonaws.com
AWS_DB_PASSWORD="etSipaV_Vwvo>FhC1z[Zs-].~x.f"
```

**MetaFrazo DB** (if needed):
```
Check .env file in metafrazo-platform root
```

---

## Key Technical Details

### Pro Video Editor Architecture

**State Management**:
- `segmentsStore.ts`: Video segments with audio
- `effectsStore.ts`: Erasure/protection areas (GhostCut)
- `speakerStore.ts`: Speaker selection (NEW - to be created)

**Bounding Box System**:
- Uses `react-rnd` for drag/resize
- Normalized coordinates (0-1) relative to video dimensions
- Conversion: `pixelPosition = videoBounds.offset + (normalized * videoBounds.size)`

**Submission Flow**:
```
useVideoSubmission → embeddedApi.submitJob() → backend/api/routes/embedded/processing.py
→ sync_segments_service.py → Sync.so API
```

### Sync.so API Integration

**Endpoint**: `POST https://api.sync.so/v2/generate`

**Payload Structure**:
```json
{
  "model": "lipsync-2",
  "input": [
    { "type": "video", "url": "..." },
    { "type": "audio", "url": "...", "refId": "audio1" }
  ],
  "segments": [
    { "startTime": 2.58, "endTime": 10.22, "audioInput": { "refId": "audio1" } }
  ],
  "options": {
    "active_speaker_detection": {
      "bounding_boxes": [[x1,y1,x2,y2], null, ...]  // Per-frame array
    }
  }
}
```

**Key Constraint**: `active_speaker_detection` is GLOBAL (not per-segment), but we use `bounding_boxes` array to achieve per-segment control.

---

## Important Notes

### Development Guidelines

- **No Claude co-author**: Git commits should only have your name
- **File limits**: Max 300 lines per file (JS/TS/Python), 400 lines (Java/Go/Rust)
- **Folder limits**: Max 8 files per folder
- **Run scripts**: Always use `.sh` scripts in `scripts/` directory
- **Code architecture**: Avoid rigidity, redundancy, circular dependencies, fragility, obscurity

### Known Issues

- **AudioInput interface**: Properties `file`, `fileName`, `fileSize` are optional - use `?? null` or `?? 0`
- **Re-edit feature**: Removed (Dec 2025), but database still stores data for auditing
- **Cross-env testing**: Waiting for Phraze developer to update AWS env vars

### Testing Checklist

When implementing speaker-selection:
- [ ] Single segment with speaker box
- [ ] Multiple segments, same speaker
- [ ] Multiple segments, different speakers
- [ ] Segment without speaker box (auto-detect fallback)
- [ ] Various video resolutions (coordinate accuracy)
- [ ] Long videos (bounding_boxes array size)

---

## Quick Reference

### Key Files for Speaker-Selection

**Frontend**:
- `frontend/src/components/VideoEditor/Pro/components/SpeakerBoxDrawer.tsx` (NEW)
- `frontend/src/components/VideoEditor/Pro/components/SegmentForm.tsx` (MODIFY)
- `frontend/src/store/speakerStore.ts` (NEW)
- `frontend/src/types/segments.ts` (MODIFY - add `speakerBox` field)

**Backend**:
- `backend/services/sync_segments_service.py` (MODIFY - add `build_bounding_boxes()`)
- `backend/api/routes/embedded/processing.py` (MODIFY - accept speaker data)

### Useful Commands

```bash
# Start MetaFrazo backend
cd /Users/zhuchen/Downloads/metafrazo-platform
./scripts/start-backend.sh

# Start MetaFrazo frontend
./scripts/start-frontend.sh

# Start Phraze.so (Cadence)
cd /Users/zhuchen/Downloads/cadence
npm run dev
```

---

## Documentation

- **Speaker-Selection Plan**: `discuss/speaker-selection-task-breakdown.md`
- **Phraze Integration**: `docs/PHRAZE_INTEGRATION_GUIDE.md`
- **API Specification**: `docs/API_SPECIFICATION.md`
- **Development Guidelines**: `DEVELOPMENT_GUIDELINES.md`

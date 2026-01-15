# Next Session Context - MetaFrazo Platform

**Last Updated**: January 14, 2026
**Current Status**: Per-Segment Speaker Selection Feature Completed

---

## Recently Completed: Per-Segment Speaker Selection

### Feature Summary

Implemented per-segment speaker selection in Pro Video Editor. Each segment can have its own speaker bounding box for multi-person videos.

### Implementation Details

**How it works**:
1. User positions playhead on a segment in the timeline
2. Clicks "Set Speaker (Segment Name)" button in toolbar
3. Drags/resizes the orange bounding box on the video to frame the speaker's face
4. Clicks "Confirm" to save the speaker box to that specific segment
5. Face icon appears on the segment bar in timeline to indicate speaker is set
6. When playhead is on a segment with speaker box, a dashed outline shows the configured area

**Key Files Modified**:
- `frontend/src/store/effectsStore.ts` - Per-segment editing state (`speakerEditingSegmentId`, `speakerEditingBox`)
- `frontend/src/components/VideoEditor/Pro/components/TimelineControls.tsx` - "Set Speaker" button with segment context
- `frontend/src/components/VideoEditor/Pro/components/TimelineSection.tsx` - Handles speaker selection for current segment
- `frontend/src/components/VideoEditor/Pro/components/VideoPlayerSection.tsx` - Speaker box overlay per-segment
- `frontend/src/components/VideoEditor/Pro/components/TimelineEffectsTrack.tsx` - Face icon per-segment
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` - Sends per-segment speakerBox to API

**Data Flow**:
```
User draws box → effectsStore (editing state) → Confirm → segmentsStore (segment.speakerBox)
→ Submit → useVideoSubmission → API payload with per-segment speakerBox
```

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

---

## Key Technical Details

### Pro Video Editor State Management

- `segmentsStore.ts`: Video segments with audio and speakerBox
- `effectsStore.ts`: Erasure/protection areas + speaker editing state
- Segments have optional `speakerBox: { x1, y1, x2, y2, method }` (normalized 0-1 coordinates)

### Sync.so API Integration

**Endpoint**: `POST https://api.sync.so/v2/generate`

**Payload with Speaker Boxes**:
```json
{
  "model": "lipsync-2",
  "input": [
    { "type": "video", "url": "..." },
    { "type": "audio", "url": "...", "refId": "audio1" }
  ],
  "segments": [
    {
      "startTime": 2.58,
      "endTime": 10.22,
      "audioInput": { "refId": "audio1" },
      "speakerBox": { "x1": 0.2, "y1": 0.1, "x2": 0.8, "y2": 0.9, "method": "manual" }
    }
  ]
}
```

---

## Development Guidelines

- **File limits**: Max 300 lines per file (JS/TS/Python), 400 lines (Java/Go/Rust)
- **Folder limits**: Max 8 files per folder
- **Run scripts**: Always use `.sh` scripts in `scripts/` directory

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

- **Phraze Integration**: `docs/PHRAZE_INTEGRATION_GUIDE.md`
- **API Specification**: `docs/API_SPECIFICATION.md`
- **Development Guidelines**: `DEVELOPMENT_GUIDELINES.md`

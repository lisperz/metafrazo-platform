# Next Session Context - MetaFrazo Platform

**Last Updated**: January 15, 2026
**Current Status**: Investigating Speaker Detection Quality Issue

---

## Current Issue: Speaker Detection Not Working Well

### Problem Summary

User submitted a job with speaker detection (bounding box) for one segment, but the speaker detection effects in the output video are not good.

### Investigation Findings

**The bounding boxes ARE being built correctly:**
```
Segment 14.522333-21.669604: frames 435-650, box=[863, 206, 1453, 610]
Built bounding_boxes array: 1803 frames, 216 with speaker box, 1587 auto-detect
Added bounding_boxes to options (1803 frames)
```

**Video metadata:**
- Resolution: 1920x1080
- FPS: 30
- Total frames: 1803

**Speaker box coordinates (pixel values):**
- x1=863, y1=206 (top-left)
- x2=1453, y2=610 (bottom-right)
- This covers roughly x: 45%-76% and y: 19%-56% of the frame

**Normalized coordinates from frontend:**
```json
{
  "x1": 0.44952532611315765,
  "y1": 0.19156122006444487,
  "x2": 0.7568829210498665,
  "y2": 0.5649789415834322,
  "method": "manual"
}
```

### Key Log Evidence

The implementation is working correctly:
1. Frontend sends `speakerBox` with normalized coordinates
2. Backend receives and logs: `Segments contain speaker boxes - will build bounding_boxes array`
3. `build_bounding_boxes()` correctly builds the array:
   - Frames 0-434: `null` (before segment)
   - Frames 435-650: `[863, 206, 1453, 610]` (speaker box)
   - Frames 651-1802: `null` (after segment)
4. Sync.so API payload includes `options.active_speaker_detection.bounding_boxes`

### Diagnose Further - Questions to Ask User

1. **What specific issue in the output video?**
   - Wrong person being lip-synced?
   - Lip-sync not happening at all?
   - Lip-sync quality is poor/glitchy?

2. **Is there more than one person visible during segment (14.5s - 21.7s)?**

3. **Does the speaker move significantly during this segment?**

4. **Can user share a screenshot of the bounding box they drew?**
   - Verify box is correctly positioned on speaker's face

### Possible Root Causes

1. **Bounding box not accurate enough** - Box needs to tightly frame the speaker's face
2. **Speaker moves outside fixed box** - Fixed box for all frames, but speaker may move
3. **Sync.so interpretation** - `bounding_boxes` tells Sync.so where to look, but it still needs to detect/track the face within that region

### Key Files for Speaker Detection

**Backend:**
- `backend/services/sync_segments_service.py` - `build_bounding_boxes()` function (lines 14-97)
- `backend/services/embedded_processing.py` - Creates Sync.so generation with video_metadata

**Frontend:**
- `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts` - Sends speakerBox to API
- `frontend/src/store/segmentsStore.ts` - Stores segment.speakerBox

---

## Project Architecture

### MetaFrazo Platform (Video Editor)

**Tech Stack**: FastAPI + React + Celery + PostgreSQL + AWS S3
**Location**: `/Users/zhuchen/Downloads/metafrazo-platform`

### Phraze.so Platform (Client Portal)

**Tech Stack**: Next.js 15 + React 19 + MySQL + Supabase Auth
**Location**: `/Users/zhuchen/Downloads/cadence`

**Domains**: `phraze.so` (prod), `staging.phraze.so`, `dev.phraze.so`

### Integration Flow

```
Phraze.so → JWT Token → MetaFrazo Editor → Sync.so API → Callback → Phraze.so
```

---

## Useful Commands

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

# Speaker-Selection Feature - Implementation Plan

**Last Updated**: January 12, 2026
**Feature**: Per-Segment Speaker Selection via Bounding Boxes
**API Reference**: https://docs.sync.so/api-reference/api/generate-api/create

---

## Executive Summary

Enable users to select different speakers for different segments in multi-person videos using fixed bounding boxes per segment.

### How It Works

```
Video: |--- Segment 1 (Girl) ---|--- Gap ---|--- Segment 2 (Man) ---|
       Frame 0-300              301-449      450-700

Bounding Boxes Array:
[
  [500,200,700,450], // Frame 0-300: Girl's face (fixed box)
  [500,200,700,450], // ... same box repeated
  null,              // Frame 301-449: No lip-sync
  null,              // ... null for gap
  [100,150,300,400], // Frame 450-700: Man's face (fixed box)
  [100,150,300,400], // ... same box repeated
]
```

**Result**: Single API call, per-segment speaker control, no video stitching needed.

---

## API Payload Structure

```json
{
  "model": "lipsync-2",
  "input": [
    { "type": "video", "url": "https://..." },
    { "type": "audio", "url": "https://...", "refId": "audio1" },
    { "type": "audio", "url": "https://...", "refId": "audio2" }
  ],
  "segments": [
    { "startTime": 2.58, "endTime": 10.22, "audioInput": { "refId": "audio1", "startTime": 2.58, "endTime": 10.22 } },
    { "startTime": 15.75, "endTime": 24.64, "audioInput": { "refId": "audio2", "startTime": 15.75, "endTime": 24.64 } }
  ],
  "options": {
    "active_speaker_detection": {
      "bounding_boxes": [
        [500, 200, 700, 450],  // Segment 1 frames: Girl
        // ... repeated for all segment 1 frames
        null,                   // Gap frames: no lip-sync
        // ... null for all gap frames
        [100, 150, 300, 400]   // Segment 2 frames: Man
        // ... repeated for all segment 2 frames
      ]
    }
  }
}
```

---

## UI Design

### Per-Segment Speaker Selection

```
┌─────────────────────────────────────────────────────────────────┐
│  Segment 1 Settings                                              │
├─────────────────────────────────────────────────────────────────┤
│  Time: 00:02:58 - 00:10:22    Audio: ✓ uploaded                 │
│                                                                  │
│  Speaker Selection:                                              │
│  ┌────────────────────────┐                                     │
│  │  [Video Frame]         │  ← Draw box on speaker's face       │
│  │     ┌─────┐            │                                     │
│  │     │ 👧  │ ← Box      │                                     │
│  │     └─────┘            │                                     │
│  └────────────────────────┘                                     │
│  ○ Auto-detect  ● Manual box: [500, 200, 700, 450]              │
└─────────────────────────────────────────────────────────────────┘
```

### Timeline with Speaker Indicators

```
Effect Track:
┌──────────────────────┐         ┌──────────────────────┐
│ Segment 1            │         │ Segment 2            │
│ 00:02:58 - 00:10:22  │         │ 00:15:75 - 00:24:64  │
│ 🎯 Speaker: Manual   │         │ 🎯 Speaker: Manual   │
└──────────────────────┘         └──────────────────────┘
```

Note: The timeline shows whether a speaker box has been manually set (🎯) or uses auto-detect. We don't display specific speaker identity since users select by drawing a bounding box on the face.

---

## Data Model

### Frontend: Segment Interface

```typescript
interface VideoSegment {
  id: string;
  startTime: number;
  endTime: number;
  audioInput: AudioInput | null;

  // NEW: Speaker bounding box
  speakerBox?: {
    x1: number; y1: number;  // Top-left
    x2: number; y2: number;  // Bottom-right
    method: 'auto' | 'manual';
  } | null;
}
```

### Backend: Bounding Boxes Builder

```python
def build_bounding_boxes(video_fps: float, total_frames: int, segments: List[dict]) -> List:
    """Build per-frame bounding boxes array from segments"""
    boxes = [None] * total_frames

    for segment in segments:
        if segment.get('speakerBox'):
            start_frame = int(segment['startTime'] * video_fps)
            end_frame = int(segment['endTime'] * video_fps)
            box = [
                segment['speakerBox']['x1'],
                segment['speakerBox']['y1'],
                segment['speakerBox']['x2'],
                segment['speakerBox']['y2']
            ]
            for frame in range(start_frame, end_frame + 1):
                boxes[frame] = box

    return boxes
```

---

## 5-Day Implementation Plan

### Day 1: Speaker Box Drawing Component

**Goal**: Create reusable component for drawing speaker bounding box on video frame

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Create `SpeakerBoxDrawer.tsx` component | `components/VideoEditor/Pro/components/` |
| 1.2 | Reuse existing `react-rnd` for drag/resize | Similar to `DrawingRectangle.tsx` |
| 1.3 | Add coordinate conversion (screen → video pixels) | `utils/coordinateUtils.ts` |
| 1.4 | Create `speakerStore.ts` for state management | `store/speakerStore.ts` |

**Deliverable**: Working component that draws resizable box on video frame

---

### Day 2: Segment Form Integration

**Goal**: Add speaker selection UI to each segment's edit panel

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Add "Speaker Selection" section to `SegmentForm` | `components/SegmentForm.tsx` |
| 2.2 | Add speaker box modal/popover with video preview | `SpeakerSelectionModal.tsx` |
| 2.3 | Update `VideoSegment` type with `speakerBox` field | `types/segments.ts` |
| 2.4 | Update `segmentsStore` to handle speaker data | `store/segmentsStore.ts` |

**Deliverable**: Users can draw speaker box for each segment

---

### Day 3: Backend Bounding Boxes Builder

**Goal**: Convert segment speaker boxes to Sync.so bounding_boxes array

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Add `build_bounding_boxes()` function | `services/sync_segments_service.py` |
| 3.2 | Get video FPS and total frames (use ffprobe or video metadata) | `services/video_utils.py` |
| 3.3 | Update API payload builder to include bounding_boxes | `sync_segments_service.py` |
| 3.4 | Handle edge cases (no speaker box = auto-detect) | `sync_segments_service.py` |

**Deliverable**: Backend generates correct bounding_boxes array for Sync.so API

---

### Day 4: Frontend-Backend Integration

**Goal**: Connect frontend speaker selection to backend processing

| Task | Description | Files |
|------|-------------|-------|
| 4.1 | Update `useVideoSubmission` to include speaker boxes | `hooks/useVideoSubmission.ts` |
| 4.2 | Update embedded processing endpoint to accept speaker data | `api/routes/embedded/processing.py` |
| 4.3 | Add speaker box validation (within video bounds) | Frontend + Backend |
| 4.4 | Update Phraze callback to store speaker selection | `api/routes/embedded/routes.py` |

**Deliverable**: End-to-end flow working with speaker selection

---

### Day 5: Testing & Polish

**Goal**: Test all scenarios and fix edge cases

| Task | Description | Notes |
|------|-------------|-------|
| 5.1 | Test: Single segment with speaker box | Basic case |
| 5.2 | Test: Multiple segments, same speaker | Same box for all |
| 5.3 | Test: Multiple segments, different speakers | Different boxes |
| 5.4 | Test: Segment without speaker box (auto-detect fallback) | Graceful fallback |
| 5.5 | Test: Various video resolutions | Coordinate accuracy |
| 5.6 | UI polish: Speaker indicator on timeline | Visual feedback |

**Deliverable**: Feature ready for production

---

## File Changes Summary

### New Files
```
frontend/src/components/VideoEditor/Pro/components/SpeakerBoxDrawer.tsx
frontend/src/components/VideoEditor/Pro/components/SpeakerSelectionModal.tsx
frontend/src/store/speakerStore.ts
backend/services/video_utils.py (if needed for FPS detection)
```

### Modified Files
```
frontend/src/types/segments.ts                    # Add speakerBox to VideoSegment
frontend/src/store/segmentsStore.ts               # Handle speaker data
frontend/src/components/VideoEditor/Pro/components/SegmentForm.tsx
frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts
backend/services/sync_segments_service.py         # Build bounding_boxes array
backend/api/routes/embedded/processing.py         # Accept speaker data
```

---

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Coordinate mismatch (UI vs video) | Test with multiple resolutions, add validation |
| Large bounding_boxes array (long videos) | Optimize: only include non-null ranges |
| FPS detection accuracy | Use video metadata or default to 30fps |

---

## Success Criteria

- [ ] User can draw speaker box for each segment
- [ ] Different segments can have different speakers
- [ ] Backend generates correct bounding_boxes array
- [ ] Sync.so API processes video with correct speaker per segment
- [ ] Segments without speaker box fall back to auto-detect

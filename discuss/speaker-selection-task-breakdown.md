# Speaker-Selection Feature - Task Breakdown

**Document Created**: January 9, 2026
**Feature**: Sync.so Speaker Selection Integration
**API Reference**: https://docs.sync.so/developer-guides/speaker-selection

---

## Executive Summary

The speaker-selection feature allows users to specify which person in a multi-person video should be lip-synced. This is critical for videos with multiple faces on screen.

### Three Implementation Methods

| Method | Use Case | Complexity | UX Quality |
|--------|----------|------------|------------|
| **Auto-detect** | Single-speaker videos | Low | Good |
| **Manual Selection** | Multi-person videos | Medium | Best |
| **Bounding Boxes** | Pre-computed face tracking | High | Best (batch) |

**Recommended Approach**: Start with **Manual Selection** (frame + click coordinates) as it provides the best balance of UX and implementation effort.

---

## Current Architecture Analysis

### Existing Integration Points

```
Frontend (ProVideoEditor.tsx)
    ↓
useVideoSubmission hook
    ↓
API: /api/v1/video-editors/pro-sync-process
    ↓
SyncSegmentsService.create_segmented_lipsync()
    ↓
Sync.so API: POST /v2/generate
```

### Current Payload Structure (sync_segments_service.py:118-125)

```python
payload = {
    "model": "lipsync-2-pro",
    "input": input_array,
    "segments": segments_array,
    "options": {
        "sync_mode": "remap"
    }
}
```

### What Needs to Be Added

```python
payload = {
    "model": "lipsync-2-pro",
    "input": input_array,
    "segments": segments_array,
    "options": {
        "sync_mode": "remap",
        "active_speaker_detection": {       # NEW
            "auto_detect": False,           # NEW
            "frame_number": 240,            # NEW - from user selection
            "coordinates": [640, 360]       # NEW - click point on face
        }
    }
}
```

---

## Task Breakdown

### Phase 1: Backend API Enhancement

#### Task 1.1: Update Pydantic Schemas
**File**: `backend/auth/phraze/schemas.py` or new `backend/api/schemas/speaker_selection.py`

- [ ] Create `ActiveSpeakerDetection` schema:
  ```python
  class ActiveSpeakerDetection(BaseModel):
      auto_detect: bool = False
      frame_number: Optional[int] = None
      coordinates: Optional[List[float]] = None  # [x, y]
      bounding_boxes: Optional[List[Optional[List[float]]]] = None
  ```
- [ ] Update `ProcessRequest` to include speaker selection

#### Task 1.2: Update SyncSegmentsService
**File**: `backend/services/sync_segments_service.py`

- [ ] Add `speaker_selection` parameter to `create_segmented_lipsync()`
- [ ] Include `active_speaker_detection` in API payload when provided
- [ ] Add validation: either `auto_detect=True` OR (`frame_number` + `coordinates`)
- [ ] Add logging for speaker selection parameters

#### Task 1.3: Update API Route
**File**: `backend/api/routes/video_editors/` (find pro sync route)

- [ ] Accept speaker selection data from frontend
- [ ] Pass to SyncSegmentsService
- [ ] Handle validation errors gracefully

---

### Phase 2: Frontend - Video Frame Capture

#### Task 2.1: Frame Extraction Utility
**File**: `frontend/src/components/VideoEditor/Pro/utils/frameCapture.ts` (new)

- [ ] Create function to capture current video frame as canvas/image
- [ ] Calculate frame number from currentTime + fps
- [ ] Handle different video formats and frame rates
- [ ] Return frame data URL for display

```typescript
interface FrameCaptureResult {
  frameNumber: number;
  frameDataUrl: string;
  videoWidth: number;
  videoHeight: number;
}

async function captureCurrentFrame(
  videoElement: HTMLVideoElement,
  currentTime: number,
  fps: number
): Promise<FrameCaptureResult>
```

#### Task 2.2: Click Coordinate Handler
**File**: `frontend/src/components/VideoEditor/Pro/utils/coordinateUtils.ts` (new)

- [ ] Convert click position to video coordinates
- [ ] Handle video scaling and aspect ratio
- [ ] Account for letterboxing/pillarboxing
- [ ] Normalize coordinates to original video dimensions

```typescript
interface ClickCoordinates {
  x: number;  // Pixel X in original video dimensions
  y: number;  // Pixel Y in original video dimensions
}

function convertClickToVideoCoordinates(
  clickX: number,
  clickY: number,
  containerRect: DOMRect,
  videoNaturalWidth: number,
  videoNaturalHeight: number
): ClickCoordinates
```

---

### Phase 3: Frontend - Speaker Selection UI

#### Task 3.1: Speaker Selection Dialog Component
**File**: `frontend/src/components/VideoEditor/Pro/components/SpeakerSelectionDialog.tsx` (new)

- [ ] Modal dialog that appears when user needs to select speaker
- [ ] Display captured video frame as static image
- [ ] Clickable overlay to select face location
- [ ] Visual feedback showing selected point
- [ ] "Auto-detect" toggle option
- [ ] Confirm/Cancel buttons

```typescript
interface SpeakerSelectionDialogProps {
  open: boolean;
  onClose: () => void;
  frameDataUrl: string;
  frameNumber: number;
  videoWidth: number;
  videoHeight: number;
  onConfirm: (selection: SpeakerSelection) => void;
}

interface SpeakerSelection {
  autoDetect: boolean;
  frameNumber?: number;
  coordinates?: [number, number];
}
```

#### Task 3.2: Face Click Indicator Component
**File**: `frontend/src/components/VideoEditor/Pro/components/FaceClickIndicator.tsx` (new)

- [ ] Visual marker showing where user clicked
- [ ] Animated circle/crosshair at click position
- [ ] Color coding (e.g., green for valid face area)

#### Task 3.3: Speaker Selection State Management
**File**: `frontend/src/store/speakerSelectionStore.ts` (new)

- [ ] Zustand store for speaker selection state
- [ ] Store: `autoDetect`, `frameNumber`, `coordinates`
- [ ] Actions: `setAutoDetect`, `setManualSelection`, `clearSelection`
- [ ] Persist selection for current editing session

---

### Phase 4: Integration & UX Flow

#### Task 4.1: Add "Select Speaker" Button to Timeline/Header
**File**: `frontend/src/components/VideoEditor/Pro/components/SubmitHeader.tsx`

- [ ] Add "Select Speaker" button near segment controls
- [ ] Show current selection status (Auto / Manual: Frame #X)
- [ ] Visual indicator when speaker is selected

#### Task 4.2: Trigger Speaker Selection Before Submit
**File**: `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts`

- [ ] Check if video likely has multiple faces (optional heuristic)
- [ ] Prompt user for speaker selection if not set
- [ ] Include speaker selection in submission payload
- [ ] Handle validation: require selection for multi-face videos

#### Task 4.3: Update Submission Payload
**File**: `frontend/src/components/VideoEditor/Pro/hooks/useVideoSubmission.ts`

- [ ] Add `speakerSelection` to submission data
- [ ] Format for backend API:
  ```typescript
  speakerSelection: {
    auto_detect: boolean;
    frame_number?: number;
    coordinates?: [number, number];
  }
  ```

---

### Phase 5: Testing & Edge Cases

#### Task 5.1: Test Cases
- [ ] Single person video with auto-detect
- [ ] Two people video with manual selection
- [ ] Video with person entering/leaving frame
- [ ] Small face in frame (accuracy check)
- [ ] Different video resolutions (720p, 1080p, 4K)
- [ ] Different aspect ratios (16:9, 4:3, vertical)

#### Task 5.2: Error Handling
- [ ] Handle case when no face detected at clicked coordinates
- [ ] Retry mechanism with different frame
- [ ] Fallback to auto-detect with user confirmation
- [ ] Clear error messages for failed speaker detection

---

## API Request/Response Examples

### Request with Manual Selection

```json
{
  "model": "lipsync-2-pro",
  "input": [
    { "type": "video", "url": "https://s3.../video.mp4" },
    { "type": "audio", "url": "https://s3.../audio.wav", "refId": "audio-1" }
  ],
  "segments": [
    {
      "startTime": 0.0,
      "endTime": 15.0,
      "audioInput": { "refId": "audio-1" }
    }
  ],
  "options": {
    "sync_mode": "remap",
    "active_speaker_detection": {
      "auto_detect": false,
      "frame_number": 240,
      "coordinates": [640, 360]
    }
  }
}
```

### Request with Auto-Detect

```json
{
  "model": "lipsync-2-pro",
  "input": [...],
  "segments": [...],
  "options": {
    "sync_mode": "remap",
    "active_speaker_detection": {
      "auto_detect": true
    }
  }
}
```

---

## File Changes Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `frontend/.../utils/frameCapture.ts` | Video frame extraction |
| `frontend/.../utils/coordinateUtils.ts` | Click-to-video coordinate conversion |
| `frontend/.../components/SpeakerSelectionDialog.tsx` | UI for speaker selection |
| `frontend/.../components/FaceClickIndicator.tsx` | Visual click marker |
| `frontend/src/store/speakerSelectionStore.ts` | State management |
| `backend/api/schemas/speaker_selection.py` | Pydantic schemas |

### Existing Files to Modify

| File | Changes |
|------|---------|
| `backend/services/sync_segments_service.py` | Add speaker selection to API call |
| `frontend/.../hooks/useVideoSubmission.ts` | Include speaker selection in payload |
| `frontend/.../components/SubmitHeader.tsx` | Add "Select Speaker" button |

---

## Implementation Priority

### MVP (Minimum Viable Product)
1. Backend schema + service update (Task 1.1, 1.2, 1.3)
2. Frame capture utility (Task 2.1)
3. Coordinate conversion (Task 2.2)
4. Basic dialog UI (Task 3.1)
5. Submit integration (Task 4.3)

### Enhanced Version
1. Face click indicator (Task 3.2)
2. State management (Task 3.3)
3. UX improvements (Task 4.1, 4.2)
4. Comprehensive testing (Task 5.1, 5.2)

---

## Estimated Effort

| Phase | Tasks | Estimated Effort |
|-------|-------|------------------|
| Phase 1: Backend | 3 tasks | 2-3 hours |
| Phase 2: Frame Utils | 2 tasks | 3-4 hours |
| Phase 3: UI Components | 3 tasks | 4-6 hours |
| Phase 4: Integration | 3 tasks | 3-4 hours |
| Phase 5: Testing | 2 tasks | 2-3 hours |
| **Total** | **13 tasks** | **14-20 hours** |

---

## Questions to Clarify Before Implementation

1. **Should speaker selection be required or optional?**
   - Current thinking: Optional, with auto-detect as default

2. **Should we detect multiple faces and prompt user?**
   - Could add face detection to determine if prompt is needed

3. **Per-segment speaker selection or global?**
   - Current API supports global only; per-segment would need multiple API calls

4. **Should we store speaker selection for re-editing?**
   - Would need to add to segments_data in database

---

## References

- [Sync.so Speaker Selection Docs](https://docs.sync.so/developer-guides/speaker-selection)
- [Sync.so Segments API](https://docs.sync.so/developer-guides/segments)
- Current integration: `backend/services/sync_segments_service.py`
- Pro Editor: `frontend/src/components/VideoEditor/Pro/`

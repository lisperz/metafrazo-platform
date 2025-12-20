/**
 * Barrel export for Pro Video Editor hooks
 */

export { useVideoHandlers } from './useVideoHandlers';
export type { VideoHandlers } from './useVideoHandlers';

export { useSegmentHandlers } from './useSegmentHandlers';
export type { SegmentHandlers } from './useSegmentHandlers';

export { useEffectHandlers } from './useEffectHandlers';
export type { EffectHandlers } from './useEffectHandlers';

export { useKeyboardShortcuts } from './useKeyboardShortcuts';
export type { KeyboardShortcutsConfig } from './useKeyboardShortcuts';

export { useTimelineAudioDrop } from './useTimelineAudioDrop';

export { useAutoLogin } from './useAutoLogin';

// Legacy hooks (existing)
export { useEffectDrawing } from './useEffectDrawing';
export { useTimelineInteraction } from './useTimelineInteraction';
export { useVideoBounds } from './useVideoBounds';
export { useVideoPlayer } from './useVideoPlayer';
export { useVideoSubmission } from './useVideoSubmission';
export type { VideoSubmissionOptions, UseVideoSubmissionReturn } from './useVideoSubmission';
export { useVideoThumbnails } from './useVideoThumbnails';
export type { UseVideoThumbnailsReturn } from './useVideoThumbnails';

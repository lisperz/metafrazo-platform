/**
 * TypeScript interfaces for Pro Video Editor segment-based lip-sync
 */

export interface AudioInput {
  refId: string;                         // Unique ID for audio file mapping
  file?: File;                           // Audio file object (optional for re-editing with URL)
  url?: string;                          // S3 URL after upload (required for re-editing)
  fileName?: string;                     // Original filename for display (optional for re-editing)
  fileSize?: number;                     // File size in bytes (optional for re-editing)
  duration?: number;                     // Audio duration in seconds (if available)
  startTime?: number;                    // Optional crop start (seconds)
  endTime?: number;                      // Optional crop end (seconds)
}

export interface VideoSegment {
  id: string;                            // UUID for frontend tracking
  startTime: number;                     // Segment start time in seconds
  endTime: number;                       // Segment end time in seconds
  audioInput: AudioInput;                // Audio configuration for this segment
  label?: string;                        // Optional segment label for user reference
  color: string;                         // Timeline color for visualization
  createdAt: number;                     // Timestamp when segment was created
}

export interface ProEditorState {
  videoFile: File | null;                // Main video file
  videoUrl: string | null;               // Local video URL for preview
  videoDuration: number;                 // Total video duration in seconds
  segments: VideoSegment[];              // Array of video segments
  currentSegmentId: string | null;      // Currently selected segment ID
  isProcessing: boolean;                 // Processing status
  error: string | null;                  // Error message if any
}

export interface SegmentValidationResult {
  valid: boolean;                        // Whether segment is valid
  error?: string;                        // Error message if invalid
}

// API request types
export interface SyncApiSegmentRequest {
  startTime: number;
  endTime: number;
  audioInput: {
    refId: string;
    startTime?: number;
    endTime?: number;
  };
}

export interface ProSyncProcessRequest {
  videoFileId: string;
  segments: SyncApiSegmentRequest[];
  displayName?: string;
  effects?: string;                      // JSON string of text removal effects
}

// API response types
export interface ProSyncProcessResponse {
  job_id: string;
  sync_generation_id: string;
  segments_count: number;
  status: string;
  message: string;
}

export interface SegmentJobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  segments_data?: {
    total: number;
    completed: number;
    processing: number;
    failed: number;
  };
  sync_generation_id?: string;
  ghostcut_task_id?: string;
  final_output_url?: string;
  created_at: string;
  completed_at?: string;
}

// Constants
export const SEGMENT_COLORS = [
  '#f59e0b',  // Amber - Pro color (same as Add Segment button)
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
  '#f59e0b',  // Amber
];

export const MAX_SEGMENTS_PRO = 5;
export const MAX_SEGMENTS_ENTERPRISE = 10;
export const MAX_AUDIO_FILE_SIZE = 100 * 1024 * 1024;  // 100MB
export const ALLOWED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.aac'];

// Helper type for subscription tiers
export type SubscriptionTier = 'free' | 'pro' | 'enterprise';

export interface UserSubscriptionInfo {
  tier: SubscriptionTier;
  maxSegments: number;
  credits: number;
}

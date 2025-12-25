/**
 * Zustand store for Pro Video Editor segment management
 * Handles segment CRUD operations, validation, and state management
 */

import { create } from 'zustand';
import {
  VideoSegment,
  AudioInput,
  SegmentValidationResult,
  SEGMENT_COLORS
} from '../types/segments';

// Store uploaded audio files separately to enable reuse
export interface UploadedAudioFile {
  refId: string;
  file: File;
  fileName: string;
  fileSize: number;
  uploadedAt: number;
}

interface SegmentsStore {
  // State
  segments: VideoSegment[];
  videoDuration: number;
  currentSegmentId: string | null;
  videoFile: File | null;
  videoUrl: string | null;
  uploadedAudioFiles: UploadedAudioFile[];

  // Undo/Redo state
  history: VideoSegment[][];
  historyIndex: number;

  // Actions - Segment Management
  addSegment: (segment: VideoSegment) => void;
  updateSegment: (id: string, updates: Partial<VideoSegment>) => void;
  deleteSegment: (id: string) => void;
  clearAllSegments: () => void;
  setCurrentSegment: (id: string | null) => void;
  splitSegmentAtTime: (splitTime: number) => boolean;

  // Actions - Video Management
  setVideoFile: (file: File, url: string, duration: number) => void;
  clearVideo: () => void;

  // Actions - Audio File Management
  addAudioFile: (file: File) => UploadedAudioFile;
  getAudioFileByRefId: (refId: string) => UploadedAudioFile | undefined;
  getAllAudioFiles: () => UploadedAudioFile[];
  removeUnusedAudioFiles: () => void;

  // Undo/Redo actions
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // Validation
  validateSegmentTimes: (
    startTime: number,
    endTime: number,
    excludeId?: string
  ) => SegmentValidationResult;

  // Getters
  getSegmentById: (id: string) => VideoSegment | undefined;
  getSortedSegments: () => VideoSegment[];
  getTotalSegmentDuration: () => number;
  getSegmentCount: () => number;
  hasOverlap: (startTime: number, endTime: number, excludeId?: string) => boolean;
  getNextSegmentColor: () => string;
  getSegmentAtTime: (time: number) => VideoSegment | undefined;
  relabelSegmentsSequentially: () => void;
}

export const useSegmentsStore = create<SegmentsStore>((set, get) => ({
  // Initial state
  segments: [],
  videoDuration: 0,
  currentSegmentId: null,
  videoFile: null,
  videoUrl: null,
  uploadedAudioFiles: [],

  // Undo/Redo initial state
  history: [[]],
  historyIndex: 0,

  // Add a new segment with automatic sorting and history tracking
  addSegment: (segment) => {
    console.log('🔥 STORE: addSegment called with:', segment);
    set((state) => {
      const newSegments = [...state.segments, segment].sort(
        (a, b) => a.startTime - b.startTime
      );
      // Relabel segments sequentially
      const relabeledSegments = newSegments.map((seg, index) => ({
        ...seg,
        label: `Segment ${index + 1}`,
      }));
      const newHistory = [...state.history.slice(0, state.historyIndex + 1), relabeledSegments];
      console.log('🔥 STORE: New segments array:', relabeledSegments);
      console.log('🔥 STORE: Total segments count:', relabeledSegments.length);
      return {
        segments: relabeledSegments,
        history: newHistory.slice(-50), // Keep last 50 states
        historyIndex: Math.min(newHistory.length - 1, 49)
      };
    });
  },

  // Update an existing segment with history tracking
  updateSegment: (id, updates) => set((state) => {
    const newSegments = state.segments.map((seg) =>
      seg.id === id ? { ...seg, ...updates } : seg
    );
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), newSegments];
    return {
      segments: newSegments,
      history: newHistory.slice(-50),
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),

  // Delete a segment with history tracking
  deleteSegment: (id) => set((state) => {
    const newSegments = state.segments.filter((seg) => seg.id !== id);
    // Relabel segments sequentially after deletion
    const relabeledSegments = newSegments.map((seg, index) => ({
      ...seg,
      label: `Segment ${index + 1}`,
    }));
    const newHistory = [...state.history.slice(0, state.historyIndex + 1), relabeledSegments];
    return {
      segments: relabeledSegments,
      currentSegmentId: state.currentSegmentId === id ? null : state.currentSegmentId,
      history: newHistory.slice(-50),
      historyIndex: Math.min(newHistory.length - 1, 49)
    };
  }),

  // Clear all segments
  clearAllSegments: () => set({
    segments: [],
    currentSegmentId: null,
    history: [[]],
    historyIndex: 0,
  }),

  // Set currently selected segment
  setCurrentSegment: (id) => set({ currentSegmentId: id }),

  // Set video file and metadata
  setVideoFile: (file, url, duration) => set({
    videoFile: file,
    videoUrl: url,
    videoDuration: duration,
  }),

  // Clear video and all segments
  clearVideo: () => set({
    videoFile: null,
    videoUrl: null,
    videoDuration: 0,
    segments: [],
    currentSegmentId: null,
    uploadedAudioFiles: [],
  }),

  // Add audio file to the store (or return existing if already uploaded)
  addAudioFile: (file: File) => {
    const state = get();

    // Check if this exact file is already uploaded (by name and size)
    const existing = state.uploadedAudioFiles.find(
      (audio) => audio.fileName === file.name && audio.fileSize === file.size
    );

    if (existing) {
      console.log('🎵 Reusing existing audio file:', existing.fileName);
      return existing;
    }

    // Create new audio file entry
    const newAudioFile: UploadedAudioFile = {
      refId: `audio-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      fileName: file.name,
      fileSize: file.size,
      uploadedAt: Date.now(),
    };

    console.log('🎵 Adding new audio file to store:', newAudioFile.fileName);
    set((state) => ({
      uploadedAudioFiles: [...state.uploadedAudioFiles, newAudioFile],
    }));

    return newAudioFile;
  },

  // Get audio file by refId
  getAudioFileByRefId: (refId: string) => {
    return get().uploadedAudioFiles.find((audio) => audio.refId === refId);
  },

  // Get all uploaded audio files
  getAllAudioFiles: () => {
    return get().uploadedAudioFiles;
  },

  // Remove audio files that are not used in any segment
  removeUnusedAudioFiles: () => {
    const state = get();
    const usedRefIds = new Set(state.segments.map((seg) => seg.audioInput.refId));

    set((state) => ({
      uploadedAudioFiles: state.uploadedAudioFiles.filter((audio) =>
        usedRefIds.has(audio.refId)
      ),
    }));
  },

  // Undo/Redo implementations
  undo: () => set((state) => {
    if (state.historyIndex > 0) {
      const newIndex = state.historyIndex - 1;
      console.log('⏮️ Undoing segment change. New index:', newIndex);
      return {
        segments: [...state.history[newIndex]],
        historyIndex: newIndex,
        currentSegmentId: null, // Clear selection on undo
      };
    }
    return state;
  }),

  redo: () => set((state) => {
    if (state.historyIndex < state.history.length - 1) {
      const newIndex = state.historyIndex + 1;
      console.log('⏭️ Redoing segment change. New index:', newIndex);
      return {
        segments: [...state.history[newIndex]],
        historyIndex: newIndex,
        currentSegmentId: null, // Clear selection on redo
      };
    }
    return state;
  }),

  canUndo: () => {
    const state = get();
    return state.historyIndex > 0;
  },

  canRedo: () => {
    const state = get();
    return state.historyIndex < state.history.length - 1;
  },

  // Validate segment times
  validateSegmentTimes: (startTime, endTime, excludeId) => {
    const state = get();
    const { videoDuration, segments } = state;

    // Basic time validation
    if (startTime < 0) {
      return {
        valid: false,
        error: 'Start time cannot be negative',
      };
    }

    if (endTime > videoDuration) {
      return {
        valid: false,
        error: `End time cannot exceed video duration (${videoDuration.toFixed(2)}s)`,
      };
    }

    if (startTime >= endTime) {
      return {
        valid: false,
        error: 'Start time must be before end time',
      };
    }

    // Minimum segment duration (0.5 seconds)
    if (endTime - startTime < 0.5) {
      return {
        valid: false,
        error: 'Segment must be at least 0.5 seconds long',
      };
    }

    // Check for overlaps with existing segments
    const hasOverlap = segments.some((seg) => {
      if (excludeId && seg.id === excludeId) return false;

      // Two segments overlap if:
      // segment1.end > segment2.start AND segment1.start < segment2.end
      return endTime > seg.startTime && startTime < seg.endTime;
    });

    if (hasOverlap) {
      return {
        valid: false,
        error: 'Segment overlaps with an existing segment. Please adjust the time range.',
      };
    }

    return { valid: true };
  },

  // Get segment by ID
  getSegmentById: (id) => {
    return get().segments.find((seg) => seg.id === id);
  },

  // Get segments sorted by start time
  getSortedSegments: () => {
    return [...get().segments].sort((a, b) => a.startTime - b.startTime);
  },

  // Calculate total duration of all segments
  getTotalSegmentDuration: () => {
    return get().segments.reduce(
      (total, seg) => total + (seg.endTime - seg.startTime),
      0
    );
  },

  // Get total number of segments
  getSegmentCount: () => {
    return get().segments.length;
  },

  // Check if a time range overlaps with any existing segment
  hasOverlap: (startTime, endTime, excludeId) => {
    const segments = get().segments;
    return segments.some((seg) => {
      if (excludeId && seg.id === excludeId) return false;
      return endTime > seg.startTime && startTime < seg.endTime;
    });
  },

  // Get next available color for new segment
  getNextSegmentColor: () => {
    const segmentCount = get().segments.length;
    return SEGMENT_COLORS[segmentCount % SEGMENT_COLORS.length];
  },

  // Get segment at specific time
  getSegmentAtTime: (time: number) => {
    return get().segments.find(
      (seg) => time >= seg.startTime && time <= seg.endTime
    );
  },

  // Relabel all segments sequentially based on time order
  relabelSegmentsSequentially: () => {
    set((state) => {
      const sortedSegments = [...state.segments].sort(
        (a, b) => a.startTime - b.startTime
      );
      const relabeledSegments = sortedSegments.map((seg, index) => ({
        ...seg,
        label: `Segment ${index + 1}`,
      }));
      return { segments: relabeledSegments };
    });
  },

  // Split segment at specific time
  splitSegmentAtTime: (splitTime: number) => {
    const state = get();

    // Find segment containing the split time
    const segmentToSplit = state.segments.find(
      (seg) => splitTime > seg.startTime && splitTime < seg.endTime
    );

    if (!segmentToSplit) {
      console.warn('No segment found at time:', splitTime);
      return false;
    }

    console.log('✂️ Splitting segment:', segmentToSplit.id, 'at time:', splitTime);

    // CRITICAL: Audio crop times MUST match video segment times
    // This prevents mismatch issues during video processing

    // Create first half segment - audio times match video segment times
    const firstSegment: VideoSegment = {
      id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      startTime: segmentToSplit.startTime,
      endTime: splitTime,
      audioInput: {
        refId: segmentToSplit.audioInput.refId,
        file: segmentToSplit.audioInput.file,
        fileName: segmentToSplit.audioInput.fileName,
        fileSize: segmentToSplit.audioInput.fileSize,
        url: segmentToSplit.audioInput.url,
        duration: segmentToSplit.audioInput.duration,
        // ALWAYS set audio crop times to match video segment times
        startTime: segmentToSplit.startTime,
        endTime: splitTime,
      },
      label: 'Segment 1', // Will be relabeled
      color: segmentToSplit.color,
      createdAt: Date.now(),
    };

    // Create second half segment - audio times match video segment times
    const secondSegment: VideoSegment = {
      id: `segment-${Date.now() + 1}-${Math.random().toString(36).substr(2, 9)}`,
      startTime: splitTime,
      endTime: segmentToSplit.endTime,
      audioInput: {
        refId: segmentToSplit.audioInput.refId,
        file: segmentToSplit.audioInput.file,
        fileName: segmentToSplit.audioInput.fileName,
        fileSize: segmentToSplit.audioInput.fileSize,
        url: segmentToSplit.audioInput.url,
        duration: segmentToSplit.audioInput.duration,
        // ALWAYS set audio crop times to match video segment times
        startTime: splitTime,
        endTime: segmentToSplit.endTime,
      },
      label: 'Segment 2', // Will be relabeled
      color: state.getNextSegmentColor(),
      createdAt: Date.now() + 1,
    };

    // Remove old segment and add two new segments
    set((state) => {
      const newSegments = state.segments
        .filter((seg) => seg.id !== segmentToSplit.id)
        .concat([firstSegment, secondSegment])
        .sort((a, b) => a.startTime - b.startTime);

      // Relabel all segments sequentially
      const relabeledSegments = newSegments.map((seg, index) => ({
        ...seg,
        label: `Segment ${index + 1}`,
      }));

      const newHistory = [...state.history.slice(0, state.historyIndex + 1), relabeledSegments];

      console.log('✂️ Split complete. New segments:', relabeledSegments.length);

      return {
        segments: relabeledSegments,
        history: newHistory.slice(-50),
        historyIndex: Math.min(newHistory.length - 1, 49),
        currentSegmentId: null, // Clear selection after split
      };
    });

    return true;
  },
}));

// Utility function to create a new segment
export const createNewSegment = (
  startTime: number,
  endTime: number,
  audioInput: AudioInput,
  label?: string
): VideoSegment => {
  const store = useSegmentsStore.getState();

  return {
    id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    startTime,
    endTime,
    audioInput,
    label,
    color: store.getNextSegmentColor(),
    createdAt: Date.now(),
  };
};

// Utility function to format time as MM:SS
export const formatSegmentTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// Utility function to format time as HH:MM:SS
export const formatSegmentTimeLong = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

// Utility function to get segment duration
export const getSegmentDuration = (segment: VideoSegment): number => {
  return segment.endTime - segment.startTime;
};

// Utility function to check if audio file is valid
export const validateAudioFile = (file: File): { valid: boolean; error?: string } => {
  const maxSize = 100 * 1024 * 1024; // 100MB
  const allowedFormats = ['.mp3', '.wav', '.m4a', '.aac'];

  if (file.size > maxSize) {
    return {
      valid: false,
      error: `Audio file is too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 100MB.`,
    };
  }

  const extension = '.' + file.name.split('.').pop()?.toLowerCase();
  if (!allowedFormats.includes(extension)) {
    return {
      valid: false,
      error: `Invalid audio format. Allowed formats: ${allowedFormats.join(', ')}`,
    };
  }

  return { valid: true };
};

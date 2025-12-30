import React, { useState, useRef, useEffect } from 'react';
import ReactPlayer from 'react-player';
import { Box } from '@mui/material';
import { useEffectsStore } from '../../../store/effectsStore';
import { useNavigate } from 'react-router-dom';
import { useSegmentsStore } from '../../../store/segmentsStore';
import { VideoSegment, SEGMENT_COLORS } from '../../../types/segments';
import SegmentDialog from './SegmentDialog';
import {
  useVideoHandlers,
  useSegmentHandlers,
  useEffectHandlers,
  useKeyboardShortcuts,
  useVideoSubmission,
} from './hooks';
import {
  SubmitHeader,
  VideoPlayerSection,
  TimelineSection,
} from './components';

// Saved segment data structure for re-editing
interface SavedSegmentData {
  startTime: number;
  endTime: number;
  audioInput: {
    refId: string;
    url?: string;
    startTime: number;
    endTime: number;
  };
  label?: string;
}

// Saved effect data structure for re-editing
interface SavedEffectData {
  type: 'erasure' | 'protection' | 'text';
  startTime: number;
  endTime: number;
  region: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface ProVideoEditorProps {
  videoUrl: string;
  videoFile: File | null;
  onBack?: () => void;
  // Embedded mode props (for phraze.so integration)
  embeddedMode?: boolean;
  embeddedToken?: string;
  phrazeJobId?: string;
  callbackUrl?: string | null;
  // Re-editing support: restore saved segments and effects
  initialSegments?: SavedSegmentData[] | null;
  initialEffects?: SavedEffectData[] | null;
}

interface TimelineEffect {
  id: string;
  type: 'erasure' | 'protection' | 'text';
  startFrame: number;
  endFrame: number;
  color: string;
  label: string;
}

const ProVideoEditor: React.FC<ProVideoEditorProps> = ({
  videoUrl,
  videoFile,
  onBack,
  embeddedMode = false,
  embeddedToken,
  phrazeJobId,
  callbackUrl,
  initialSegments,
  initialEffects,
}) => {
  const navigate = useNavigate();
  const playerRef = useRef<ReactPlayer>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const frameStripRef = useRef<HTMLDivElement>(null);

  // Timeline interaction state
  const [isDraggingTimeline, setIsDraggingTimeline] = useState(false);
  const [timelineEffects, setTimelineEffects] = useState<TimelineEffect[]>([]);

  // Submission hook - pass embedded mode options
  const { isSubmitting, submissionProgress, handleSubmit } = useVideoSubmission({
    videoFile,
    videoUrl,
    embeddedMode,
    embeddedToken,
    phrazeJobId,
    callbackUrl,
  });

  // Get segments store with undo/redo
  const {
    segments,
    addSegment,
    setVideoFile: setStoreVideoFile,
    getSegmentCount,
    deleteSegment,
    updateSegment,
    currentSegmentId,
    undo: undoSegment,
    redo: redoSegment,
    canUndo: canUndoSegment,
    canRedo: canRedoSegment,
    splitSegmentAtTime,
    getSegmentAtTime,
    clearAllSegments,
  } = useSegmentsStore();

  // Get all state and actions from centralized store
  const {
    effects,
    addEffect,
    updateEffect,
    deleteEffect,
    currentTime,
    duration,
    isPlaying,
    zoomLevel: timelineZoom,
    setCurrentTime: setStoreTime,
    setDuration: setStoreDuration,
    setIsPlaying: setStoreIsPlaying,
    setZoomLevel: setTimelineZoom,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useEffectsStore();

  // Use custom hooks for handlers
  const videoHandlers = useVideoHandlers(
    playerRef as React.RefObject<ReactPlayer>,
    videoContainerRef as React.RefObject<HTMLDivElement>,
    videoUrl,
    duration
  );
  const segmentHandlers = useSegmentHandlers(currentTime, duration);
  const effectHandlers = useEffectHandlers(currentTime, duration);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    canUndo: canUndo(),
    canRedo: canRedo(),
    undo,
    redo,
    canUndoSegment: canUndoSegment(),
    canRedoSegment: canRedoSegment(),
    undoSegment,
    redoSegment,
    deleteSegment,
    deleteEffect,
    currentSegmentId,
    editingEffectId: effectHandlers.editingEffectId,
    handleSplitSegment: segmentHandlers.handleSplitSegment,
  });

  // Debug log for segments state
  useEffect(() => {
    console.log('=== SEGMENTS STATE CHANGED ===');
    console.log('Total segments:', segments.length);
    console.log('Segments:', segments);
  }, [segments]);

  // Track if initial segments have been restored to avoid re-running
  const [initialSegmentsRestored, setInitialSegmentsRestored] = useState(false);

  // Log once on mount
  useEffect(() => {
    console.log('[ProVideoEditor] Component mounted - checking initialSegments');
    console.log('  initialSegments:', initialSegments);
    console.log('  initialSegments length:', initialSegments?.length ?? 0);
  }, []); // Empty deps - only run on mount

  // Restore initial segments for re-editing (only once when component mounts)
  useEffect(() => {
    console.log('[ProVideoEditor] Segment restoration check:', {
      initialSegmentsRestored,
      hasInitialSegments: !!initialSegments,
      segmentsLength: initialSegments?.length ?? 0
    });

    if (initialSegmentsRestored) {
      console.log('[ProVideoEditor] Already restored, skipping');
      return;
    }

    if (!initialSegments || initialSegments.length === 0) {
      console.log('[ProVideoEditor] No initial segments to restore');
      return;
    }

    console.log('=== RESTORING INITIAL SEGMENTS ===');
    console.log('Initial segments to restore:', initialSegments.length);
    console.log('First segment:', JSON.stringify(initialSegments[0], null, 2));

    // Clear existing segments first
    clearAllSegments();

    // Convert saved segment data to full VideoSegment format
    initialSegments.forEach((savedSeg, index) => {
      const segment: VideoSegment = {
        id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        startTime: savedSeg.startTime,
        endTime: savedSeg.endTime,
        audioInput: {
          refId: savedSeg.audioInput.refId,
          url: savedSeg.audioInput.url,
          startTime: savedSeg.audioInput.startTime,
          endTime: savedSeg.audioInput.endTime,
          // Note: File objects are not available for re-editing - URLs are used instead
        },
        label: savedSeg.label || `Segment ${index + 1}`,
        color: SEGMENT_COLORS[index % SEGMENT_COLORS.length],
        createdAt: Date.now(),
      };
      addSegment(segment);
    });

    console.log('Initial segments restored successfully');
    setInitialSegmentsRestored(true);
  }, [initialSegments, initialSegmentsRestored, clearAllSegments, addSegment]);

  // Restore initial effects for re-editing
  useEffect(() => {
    if (!initialEffects || initialEffects.length === 0) {
      return;
    }

    console.log('=== RESTORING INITIAL EFFECTS ===');
    console.log('Initial effects to restore:', initialEffects.length);

    // Add each saved effect to the effects store
    initialEffects.forEach((savedEffect) => {
      addEffect({
        type: savedEffect.type,
        startTime: savedEffect.startTime,
        endTime: savedEffect.endTime,
        region: savedEffect.region,
      });
    });

    console.log('Initial effects restored successfully');
  }, []); // Only run once on mount

  // Synchronize timeline effects with main effects store (NOT including segments)
  useEffect(() => {
    // Map video effects (erasure, protection, text) - segments handled separately
    const syncedTimelineEffects: TimelineEffect[] = effects.map(effect => {
      const colors = {
        erasure: '#5B8FF9',
        protection: '#5AD8A6',
        text: '#5D7092',
      };

      const labels = {
        erasure: 'Erasure Area',
        protection: 'Protection Area',
        text: 'Erase Text',
      };

      return {
        id: effect.id,
        type: effect.type,
        // Use precise percentage calculation without rounding
        startFrame: (effect.startTime / duration) * 100,
        endFrame: (effect.endTime / duration) * 100,
        color: colors[effect.type],
        label: labels[effect.type],
      };
    });

    // Only set effects, not segments (segments passed separately to TimelineEffectsTrack)
    setTimelineEffects(syncedTimelineEffects);
  }, [effects, duration]); // Removed segments from dependencies

  // Initialize video in segments store when component mounts
  useEffect(() => {
    if (videoFile && videoUrl && duration > 0) {
      setStoreVideoFile(videoFile, videoUrl, duration);
    }
  }, [videoFile, videoUrl, duration, setStoreVideoFile]);

  // Force timeline update when video becomes ready
  useEffect(() => {
    if (videoHandlers.isVideoReady && playerRef.current && duration > 0) {
      const currentState = playerRef.current.getCurrentTime();
      if (currentState !== undefined && currentState !== currentTime) {
        setStoreTime(currentState);
      }
    }
  }, [videoHandlers.isVideoReady, duration, currentTime, setStoreTime]);

  return (
    <Box sx={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: '#f5f5f5',
      overflow: 'hidden'
    }}>
      {/* Header with Submit Button */}
      <SubmitHeader
        segments={segments}
        isSubmitting={isSubmitting}
        submissionProgress={submissionProgress}
        handleSubmit={handleSubmit}
        onBack={onBack}
        navigate={navigate}
      />

      {/* Main Content Area */}
      <Box sx={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden'
      }}>
        {/* Video and Timeline Section */}
        <Box sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          {/* Video Player Container */}
          <VideoPlayerSection
            playerRef={playerRef}
            videoContainerRef={videoContainerRef}
            videoUrl={videoUrl}
            isPlaying={isPlaying}
            currentTime={currentTime}
            duration={duration}
            effects={effects}
            videoHandlers={videoHandlers}
            effectHandlers={effectHandlers}
            updateEffect={updateEffect}
            deleteEffect={deleteEffect}
            setStoreTime={setStoreTime}
          />

          {/* Timeline Section */}
          <TimelineSection
            currentTime={currentTime}
            duration={duration}
            isPlaying={isPlaying}
            timelineZoom={timelineZoom}
            timelineEffects={timelineEffects}
            segments={segments}
            currentSegmentId={currentSegmentId}
            videoHandlers={videoHandlers}
            segmentHandlers={segmentHandlers}
            effectHandlers={effectHandlers}
            canUndo={canUndo()}
            canRedo={canRedo()}
            canUndoSegment={canUndoSegment()}
            canRedoSegment={canRedoSegment()}
            undo={undo}
            redo={redo}
            undoSegment={undoSegment}
            redoSegment={redoSegment}
            setTimelineZoom={setTimelineZoom}
            deleteSegment={deleteSegment}
            deleteEffect={deleteEffect}
            getSegmentAtTime={getSegmentAtTime}
            isDraggingTimeline={isDraggingTimeline}
            setIsDraggingTimeline={setIsDraggingTimeline}
          />
        </Box>
      </Box>

      {/* Segment Dialog */}
      <SegmentDialog
        open={segmentHandlers.isSegmentDialogOpen}
        onClose={segmentHandlers.handleCloseDialog}
        editingSegmentId={segmentHandlers.editingSegmentId}
        videoDuration={duration}
        currentTime={currentTime}
      />
    </Box>
  );
};

export default ProVideoEditor;

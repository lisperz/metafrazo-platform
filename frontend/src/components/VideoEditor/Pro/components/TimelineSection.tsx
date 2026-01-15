/**
 * Timeline Section Component
 *
 * Orchestrates the timeline area with:
 * - Control buttons (play, effects, segments, undo/redo)
 * - Time ruler with current time indicator
 * - Frame strip with thumbnails
 * - Effects track with segments and effects
 */

import React, { useRef } from 'react';
import { Box, IconButton, Button } from '@mui/material';
import { ContentCut, Undo, Redo, VolumeUp, VolumeOff } from '@mui/icons-material';
import TimelineControls from './TimelineControls';
import TimeRuler from './TimeRuler';
import FrameStrip from './FrameStrip';
import TimelineEffectsTrack from './TimelineEffectsTrack';
import { VideoHandlers } from '../hooks/useVideoHandlers';
import { SegmentHandlers } from '../hooks/useSegmentHandlers';
import { EffectHandlers } from '../hooks/useEffectHandlers';
import { useTimelineAudioDrop } from '../hooks/useTimelineAudioDrop';
import { calculateProgressPercentage, formatTime as formatTimeUtil, handleTimelineInteraction } from '../../../../utils/timelineUtils';
import { VideoSegment } from '../../../../types/segments';
import { detectOverlappingSegments } from '../../../../utils/segmentOverlapDetection';
import { useEffectsStore } from '../../../../store/effectsStore';

interface TimelineEffect {
  id: string;
  type: 'erasure' | 'protection' | 'text';
  startFrame: number;
  endFrame: number;
  color: string;
  label: string;
}

interface TimelineSectionProps {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  timelineZoom: number;
  timelineEffects: TimelineEffect[];
  segments: VideoSegment[];
  currentSegmentId: string | null;
  videoHandlers: VideoHandlers;
  segmentHandlers: SegmentHandlers;
  effectHandlers: EffectHandlers;
  canUndo: boolean;
  canRedo: boolean;
  canUndoSegment: boolean;
  canRedoSegment: boolean;
  undo: () => void;
  redo: () => void;
  undoSegment: () => void;
  redoSegment: () => void;
  setTimelineZoom: (zoom: number) => void;
  deleteSegment: (id: string) => void;
  deleteEffect: (id: string) => void;
  getSegmentAtTime: (time: number) => VideoSegment | undefined;
  isDraggingTimeline: boolean;
  setIsDraggingTimeline: (dragging: boolean) => void;
}

export const TimelineSection: React.FC<TimelineSectionProps> = ({
  currentTime,
  duration,
  isPlaying,
  timelineZoom,
  timelineEffects,
  segments,
  currentSegmentId,
  videoHandlers,
  segmentHandlers,
  effectHandlers,
  canUndo,
  canRedo,
  canUndoSegment,
  canRedoSegment,
  undo,
  redo,
  undoSegment,
  redoSegment,
  setTimelineZoom,
  deleteSegment,
  deleteEffect,
  getSegmentAtTime,
  isDraggingTimeline,
  setIsDraggingTimeline,
}) => {
  const frameStripRef = useRef<HTMLDivElement | null>(null);

  // Get speaker selection state from store
  const {
    globalSpeakerBox,
    isSpeakerSelectionMode,
    startSpeakerSelection,
  } = useEffectsStore();

  // Audio drop functionality
  const audioDropHandlers = useTimelineAudioDrop({
    duration,
    onError: (message) => {
      console.error('Audio drop error:', message);
      // Error is already shown in drop zone component
    },
  });

  const formatTime = (seconds: number, includeMs: boolean = false): string => {
    if (includeMs) {
      return formatTimeUtil(seconds);
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const progressPercentage = calculateProgressPercentage(currentTime, duration);

  // Detect overlapping segments
  const overlappingSegments = React.useMemo(() => {
    const overlaps = detectOverlappingSegments(segments);
    return new Set(overlaps.map(o => o.segmentId));
  }, [segments]);

  const handleTimelineEffectDrag = (
    e: React.MouseEvent,
    effectId: string,
    type: 'start' | 'end' | 'move'
  ) => {
    const isSegment = segments.some(seg => seg.id === effectId);
    if (isSegment) {
      segmentHandlers.handleSegmentDrag(e, effectId, type, frameStripRef as React.RefObject<HTMLDivElement>, timelineZoom);
    } else {
      effectHandlers.handleEffectDrag(e, effectId, type, frameStripRef as React.RefObject<HTMLDivElement>, timelineZoom);
    }
  };

  const handleDeleteTimelineEffect = (id: string) => {
    const isSegment = segments.some(seg => seg.id === id);
    if (isSegment) {
      deleteSegment(id);
      console.log('Deleted segment from timeline:', id);
    } else {
      deleteEffect(id);
      console.log('Deleted effect from timeline:', id);
    }
  };

  const handleEffectClick = (effectId: string, e: React.MouseEvent) => {
    const isSegment = segments.some(seg => seg.id === effectId);
    if (isSegment) {
      if ((e.target as HTMLElement).closest('[data-drag-handle]') ||
          (e.target as HTMLElement).closest('button')) {
        return;
      }
      const { setCurrentSegment } = require('../../../../store/segmentsStore').useSegmentsStore.getState();
      setCurrentSegment(effectId);
      console.log('Selected segment for keyboard operations:', effectId);
    } else {
      effectHandlers.handleEffectClick(effectId, e);
    }
  };

  const handleTimelineDragStart = (e: React.MouseEvent, timelineContainer: HTMLElement) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingTimeline(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const newTime = handleTimelineInteraction(
        moveEvent,
        timelineContainer,
        duration,
        timelineZoom
      );
      videoHandlers.handleSeek(newTime);
    };

    const handleMouseUp = () => {
      setIsDraggingTimeline(false);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleTimelineClick = (e: React.MouseEvent | MouseEvent, container: HTMLElement) => {
    const newTime = handleTimelineInteraction(
      e,
      container,
      duration,
      timelineZoom
    );
    videoHandlers.handleSeek(newTime);
  };

  return (
    <Box sx={{
      flex: 1,
      bgcolor: 'white',
      display: 'flex',
      flexDirection: 'column',
      borderTop: '2px solid #e0e0e0',
      overflow: 'auto',
      minHeight: '45%',
      maxHeight: '45%'
    }}>
      {/* Control Buttons with Undo/Redo */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        p: 1,
        borderBottom: '1px solid #f0f0f0',
        bgcolor: 'white',
        flexWrap: 'wrap',
        minHeight: '50px'
      }}>
        {/* Undo/Redo Controls */}
        <IconButton
          onClick={() => {
            if (canUndoSegment) {
              undoSegment();
            } else if (canUndo) {
              undo();
            }
          }}
          disabled={!canUndoSegment && !canUndo}
          size="small"
          sx={{
            color: (canUndoSegment || canUndo) ? '#333' : '#ccc',
            '&:hover': {
              bgcolor: (canUndoSegment || canUndo) ? 'rgba(0,0,0,0.08)' : 'transparent'
            }
          }}
          title="Undo (Ctrl+Z) - Segments & Effects"
        >
          <Undo />
        </IconButton>

        <IconButton
          onClick={() => {
            if (canRedoSegment) {
              redoSegment();
            } else if (canRedo) {
              redo();
            }
          }}
          disabled={!canRedoSegment && !canRedo}
          size="small"
          sx={{
            color: (canRedoSegment || canRedo) ? '#333' : '#ccc',
            '&:hover': {
              bgcolor: (canRedoSegment || canRedo) ? 'rgba(0,0,0,0.08)' : 'transparent'
            }
          }}
          title="Redo (Ctrl+Y) - Segments & Effects"
        >
          <Redo />
        </IconButton>

        {/* Separator */}
        <Box sx={{
          width: '1px',
          height: '20px',
          bgcolor: '#e0e0e0',
          mx: 1
        }} />

        {/* Play, Add Effects, Add Segment buttons */}
        <TimelineControls
          isPlaying={isPlaying}
          isMuted={videoHandlers.isMuted}
          currentTime={currentTime}
          duration={duration}
          timelineZoom={timelineZoom}
          canUndo={canUndo || canUndoSegment}
          canRedo={canRedo || canRedoSegment}
          segmentCount={segments.length}
          hasSpeakerBox={globalSpeakerBox !== null}
          isSpeakerSelectionMode={isSpeakerSelectionMode}
          onPlayPause={videoHandlers.handlePlayPause}
          onVolumeToggle={videoHandlers.handleVolumeToggle}
          onUndo={() => {}}
          onRedo={() => {}}
          onZoomChange={setTimelineZoom}
          onAddEffect={effectHandlers.handleAddEffect}
          onAddSegment={segmentHandlers.handleAddSegment}
          onSelectSpeaker={startSpeakerSelection}
          formatTime={formatTime}
        />

        {/* Split Segment Button - right after Add Segment */}
        <Button
          variant="contained"
          size="small"
          onClick={segmentHandlers.handleSplitSegment}
          disabled={!getSegmentAtTime(currentTime)}
          startIcon={<ContentCut />}
          title="Split segment at current time (Ctrl+K)"
          sx={{
            bgcolor: '#8b5cf6',
            color: 'white',
            border: 'none',
            fontSize: '13px',
            textTransform: 'none',
            fontWeight: 600,
            '&:hover': {
              bgcolor: '#7c3aed',
            },
            '&:disabled': {
              background: '#d9d9d9',
              color: '#999'
            }
          }}
        >
          Split Segment
        </Button>

        {/* Spacer to push time/volume/zoom to far right */}
        <Box sx={{ flex: 1 }} />

        {/* Time Display */}
        <Box sx={{ fontSize: '13px', color: '#666', fontFamily: 'monospace' }}>
          {formatTime(currentTime, true)} / {formatTime(duration, true)}
        </Box>

        {/* Volume Control */}
        <IconButton
          size="small"
          onClick={videoHandlers.handleVolumeToggle}
          sx={{
            color: videoHandlers.isMuted ? '#ff4d4f' : '#666',
            '&:hover': {
              bgcolor: 'rgba(0,0,0,0.08)'
            }
          }}
        >
          {videoHandlers.isMuted ? <VolumeOff fontSize="small" /> : <VolumeUp fontSize="small" />}
        </IconButton>

        {/* Timeline Zoom Controls */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          ml: 2,
          minWidth: 150
        }}>
          <Box sx={{ fontSize: '11px', color: '#666', whiteSpace: 'nowrap' }}>
            Zoom
          </Box>
          <Box
            component="input"
            type="range"
            value={timelineZoom}
            onChange={(e: any) => setTimelineZoom(parseFloat(e.target.value))}
            min={0.5}
            max={5}
            step={0.1}
            sx={{
              width: 80,
              height: 4,
              cursor: 'pointer',
              '&::-webkit-slider-thumb': {
                width: 16,
                height: 16,
                borderRadius: '50%',
                bgcolor: '#1890ff',
              }
            }}
          />
          <Box
            component="button"
            onClick={() => setTimelineZoom(1)}
            sx={{
              minWidth: 'auto',
              px: 1,
              py: 0.25,
              fontSize: '10px',
              height: 20,
              bgcolor: timelineZoom === 1 ? '#1890ff' : 'transparent',
              color: timelineZoom === 1 ? 'white' : '#666',
              border: '1px solid #d9d9d9',
              borderRadius: '4px',
              cursor: 'pointer',
              '&:hover': {
                bgcolor: timelineZoom === 1 ? '#40a9ff' : 'rgba(24, 144, 255, 0.1)',
                borderColor: '#1890ff'
              }
            }}
          >
            1:1
          </Box>
        </Box>
      </Box>

      {/* Timeline Content Area - Unified Scroll Container */}
      <Box sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'white',
        overflow: 'hidden',
        minHeight: '300px',
        position: 'relative'
      }}>
        {/* Single Horizontal + Vertical Scroll Container */}
        <Box
          id="timeline-scroll-container"
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflowX: 'auto',
            overflowY: 'auto',
            '&::-webkit-scrollbar': {
              height: '10px',
              width: '10px',
            },
            '&::-webkit-scrollbar-track': {
              backgroundColor: '#f5f5f5',
            },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: '#bfbfbf',
              borderRadius: '5px',
              '&:hover': {
                backgroundColor: '#999',
              },
            },
            '&::-webkit-scrollbar-corner': {
              backgroundColor: '#f5f5f5',
            },
          }}
        >
          {/* Timeline Wrapper - All components share this width */}
          <Box sx={{
            minWidth: `${100 * timelineZoom}%`,
            width: `${100 * timelineZoom}%`,
            display: 'flex',
            flexDirection: 'column',
            position: 'relative'
          }}>
            {/* Time Ruler */}
            <TimeRuler
              duration={duration}
              currentTime={currentTime}
              progressPercentage={progressPercentage}
              timelineZoom={timelineZoom}
              isDragging={isDraggingTimeline}
              formatTime={formatTime}
              calculateProgressPercentage={calculateProgressPercentage}
              onSeek={(time) => videoHandlers.handleSeek(time)}
              onDragStart={(e) => {
                const timelineContainer = e.currentTarget as HTMLElement;
                handleTimelineDragStart(e, timelineContainer);
              }}
            />

            {/* Frame Strip */}
            <FrameStrip
              thumbnails={videoHandlers.thumbnails}
              duration={duration}
              currentTime={currentTime}
              progressPercentage={progressPercentage}
              timelineZoom={timelineZoom}
              isDragging={isDraggingTimeline}
              frameStripRef={frameStripRef}
              onSeek={(time) => videoHandlers.handleSeek(time)}
              onDragStart={(e) => {
                const frameStripContainer = e.currentTarget.closest('[data-frame-strip]') as HTMLElement;
                if (frameStripContainer) {
                  handleTimelineDragStart(e, frameStripContainer);
                }
              }}
            />

            {/* Timeline Effects Track */}
            <TimelineEffectsTrack
              timelineEffects={timelineEffects}
              segments={segments}
              duration={duration}
              currentTime={currentTime}
              progressPercentage={progressPercentage}
              timelineZoom={timelineZoom}
              editingEffectId={effectHandlers.editingEffectId}
              formatTime={formatTime}
              onEffectDrag={handleTimelineEffectDrag}
              onEffectClick={handleEffectClick}
              onEffectDelete={handleDeleteTimelineEffect}
              overlappingSegmentIds={overlappingSegments}
              showDropZone={segments.length === 0}
              dropZoneProps={{
                isDragging: audioDropHandlers.isDragging,
                isOver: audioDropHandlers.isOver,
                error: audioDropHandlers.error,
                onDragEnter: audioDropHandlers.handleDragEnter,
                onDragOver: audioDropHandlers.handleDragOver,
                onDragLeave: audioDropHandlers.handleDragLeave,
                onDrop: audioDropHandlers.handleDrop,
                onFileSelect: audioDropHandlers.handleFileSelect,
                onClearError: audioDropHandlers.clearError,
              }}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

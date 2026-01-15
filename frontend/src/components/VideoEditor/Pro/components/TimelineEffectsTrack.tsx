import React from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import { Delete, Warning, Face } from '@mui/icons-material';
import { EmptyTimelineDropZone } from './EmptyTimelineDropZone';

interface TimelineEffect {
  id: string;
  type: 'erasure' | 'protection' | 'text';
  startFrame: number;
  endFrame: number;
  color: string;
  label: string;
}

interface SpeakerBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface VideoSegment {
  id: string;
  startTime: number;
  endTime: number;
  color: string;
  label?: string;
  speakerBox?: SpeakerBox | null;  // Per-segment speaker box
}

interface TimelineEffectsTrackProps {
  timelineEffects: TimelineEffect[];
  segments: VideoSegment[];
  duration: number;
  currentTime: number;
  progressPercentage: number;
  timelineZoom?: number;
  editingEffectId: string | null;
  formatTime: (seconds: number, includeMs?: boolean) => string;
  onEffectDrag: (e: React.MouseEvent, effectId: string, type: 'start' | 'end' | 'move') => void;
  onEffectClick: (effectId: string, e: React.MouseEvent) => void;
  onEffectDelete: (id: string) => void;
  overlappingSegmentIds?: Set<string>;
  // Audio drop zone props
  showDropZone?: boolean;
  dropZoneProps?: {
    isDragging: boolean;
    isOver: boolean;
    error: string | null;
    onDragEnter: (e: React.DragEvent) => void;
    onDragOver: (e: React.DragEvent) => void;
    onDragLeave: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent) => void;
    onFileSelect: (file: File) => void;
    onClearError: () => void;
  };
}

const TimelineEffectsTrack: React.FC<TimelineEffectsTrackProps> = ({
  timelineEffects,
  segments,
  duration,
  currentTime,
  progressPercentage,
  timelineZoom = 1,
  editingEffectId,
  formatTime,
  onEffectDrag,
  onEffectClick,
  onEffectDelete,
  overlappingSegmentIds = new Set(),
  showDropZone = false,
  dropZoneProps,
}) => {
  // Calculate total tracks needed: 1 for segments + N for effects
  const totalTracks = (segments.length > 0 ? 1 : 0) + timelineEffects.length;
  return (
    <Box sx={{
      position: 'relative',
      flex: 1,
      minHeight: 200,
      maxHeight: 300,
      width: '100%',
      bgcolor: 'white',
      borderRadius: '6px',
      border: '1px solid #d9d9d9',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      overflow: 'hidden'
    }}>
      {/* Timeline Indicator */}
      {duration > 0 && (
        <Box
          sx={{
            position: 'absolute',
            left: `${progressPercentage}%`,
            top: 0,
            bottom: 0,
            width: '2px',
            bgcolor: '#ff4d4f',
            zIndex: 100,
            pointerEvents: 'none',
            boxShadow: '0 0 6px rgba(255, 77, 79, 0.6)',
            transform: 'translateX(-1px)',
          }}
        />
      )}

      {/* Header */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        pb: 1,
        borderBottom: '1px solid #e9ecef'
      }}>
        <Typography sx={{ fontSize: '12px', color: '#666', fontWeight: 500 }}>
          Effect Track
        </Typography>
        <Typography sx={{ fontSize: '11px', color: '#999' }}>
          Segments ({segments.length}) | Effects ({timelineEffects.length})
        </Typography>
      </Box>

      {/* Show Drop Zone when no segments exist - at the TOP */}
      {showDropZone && dropZoneProps && (
        <Box sx={{ px: 2, py: 0.5, width: '100%' }}>
          <EmptyTimelineDropZone {...dropZoneProps} />
        </Box>
      )}

      {/* Effect Bars */}
      <Box sx={{
        position: 'relative',
        flex: 1,
        minHeight: '150px',
        maxHeight: '220px',
        overflowY: 'auto',
        overflowX: 'hidden',
        '&::-webkit-scrollbar': {
          width: '6px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: '#f5f5f5',
          borderRadius: '3px',
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: '#d9d9d9',
          borderRadius: '3px',
          '&:hover': {
            backgroundColor: '#bfbfbf',
          },
        },
      }}>
        <Box sx={{
          position: 'relative',
          height: `${Math.max(50, totalTracks * 40)}px`,
          width: '100%',
        }}>
          {/* Render all segments on track 0 (same row) */}
          {segments.map((segment, index) => {
            const trackTop = 5; // All segments on the same row (track 0)
            const segmentLeft = (segment.startTime / duration) * 100;
            const segmentWidth = ((segment.endTime - segment.startTime) / duration) * 100;
            const isOverlapping = overlappingSegmentIds.has(segment.id);

            return (
              <Box
                key={segment.id}
                sx={{
                  position: 'absolute',
                  left: `${segmentLeft}%`,
                  width: `${segmentWidth}%`,
                  top: `${trackTop}px`,
                  height: '30px',
                  bgcolor: segment.color,
                  borderRadius: '4px',
                  cursor: 'move',
                  display: 'flex',
                  alignItems: 'center',
                  px: 1,
                  opacity: 0.85,
                  zIndex: 15,
                  border: isOverlapping
                    ? '2px solid #ff4d4f'
                    : '1px solid rgba(255,255,255,0.3)',
                  boxShadow: isOverlapping
                    ? '0 0 8px rgba(255, 77, 79, 0.6)'
                    : '0 1px 3px rgba(0,0,0,0.1)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    opacity: 1,
                    transform: 'translateY(-1px)',
                    boxShadow: isOverlapping
                      ? '0 0 12px rgba(255, 77, 79, 0.8)'
                      : '0 2px 6px rgba(0,0,0,0.15)',
                    '& [data-drag-handle="true"]': {
                      opacity: 1
                    }
                  }
                }}
                onMouseDown={(e) => onEffectDrag(e, segment.id, 'move')}
                onClick={(e) => onEffectClick(segment.id, e)}
              >
                {/* Start Handle */}
                <Box
                  data-drag-handle="true"
                  sx={{
                    position: 'absolute',
                    left: -2,
                    top: 0,
                    bottom: 0,
                    width: '6px',
                    bgcolor: 'rgba(255,255,255,0.8)',
                    cursor: 'ew-resize',
                    borderRadius: '2px 0 0 2px',
                    opacity: 0,
                    transition: 'opacity 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,1)',
                      opacity: 1,
                    }
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    onEffectDrag(e, segment.id, 'start');
                  }}
                />

                {/* Label with time range */}
                <Box sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 0.25,
                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {isOverlapping && (
                      <Warning
                        sx={{
                          fontSize: 11,
                          color: '#fff',
                          filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.5))',
                        }}
                      />
                    )}
                    {segment.speakerBox && (
                      <Face
                        sx={{
                          fontSize: 11,
                          color: '#f59e0b',
                          filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.5))',
                        }}
                        titleAccess="Speaker box set for this segment"
                      />
                    )}
                    <Typography sx={{
                      color: 'white',
                      fontSize: '9px',
                      fontWeight: 600,
                      userSelect: 'none',
                      textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                    }}>
                      {segment.label || `Segment ${index + 1}`}
                    </Typography>
                  </Box>
                  <Typography sx={{
                    color: 'rgba(255, 255, 255, 0.9)',
                    fontSize: '8px',
                    fontFamily: 'monospace',
                    userSelect: 'none',
                    textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                  }}>
                    {formatTime(segment.startTime, true)} - {formatTime(segment.endTime, true)}
                  </Typography>
                </Box>

                {/* Delete Button */}
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEffectDelete(segment.id);
                  }}
                  sx={{
                    p: 0.25,
                    color: 'rgba(255,255,255,0.9)',
                    opacity: 0.8,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.2)',
                      opacity: 1,
                      transform: 'scale(1.1)'
                    }
                  }}
                >
                  <Delete sx={{ fontSize: 12 }} />
                </IconButton>

                {/* End Handle */}
                <Box
                  data-drag-handle="true"
                  sx={{
                    position: 'absolute',
                    right: -2,
                    top: 0,
                    bottom: 0,
                    width: '6px',
                    bgcolor: 'rgba(255,255,255,0.8)',
                    cursor: 'ew-resize',
                    borderRadius: '0 2px 2px 0',
                    opacity: 0,
                    transition: 'opacity 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,1)',
                      opacity: 1,
                    }
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    onEffectDrag(e, segment.id, 'end');
                  }}
                />
              </Box>
            );
          })}

          {/* Render effects on subsequent tracks (starting from track 1 if segments exist) */}
          {timelineEffects.map((effect, index) => {
            const trackOffset = segments.length > 0 ? 1 : 0; // Offset by 1 if segments exist
            const trackTop = (trackOffset + index) * 40 + 5;
            const effectLeft = effect.startFrame;
            const effectWidth = effect.endFrame - effect.startFrame;
            const isOverlapping = overlappingSegmentIds.has(effect.id);

            return (
              <Box
                key={effect.id}
                sx={{
                  position: 'absolute',
                  left: `${effectLeft}%`,
                  width: `${effectWidth}%`,
                  top: `${trackTop}px`,
                  height: '30px',
                  bgcolor: effect.color,
                  borderRadius: '4px',
                  cursor: 'move',
                  display: 'flex',
                  alignItems: 'center',
                  px: 1,
                  opacity: editingEffectId === effect.id ? 1 : 0.85,
                  zIndex: 15,
                  border: isOverlapping
                    ? '2px solid #ff4d4f'
                    : editingEffectId === effect.id
                      ? '2px solid #1890ff'
                      : '1px solid rgba(255,255,255,0.3)',
                  boxShadow: isOverlapping
                    ? '0 0 8px rgba(255, 77, 79, 0.6)'
                    : editingEffectId === effect.id
                      ? '0 2px 8px rgba(24,144,255,0.4)'
                      : '0 1px 3px rgba(0,0,0,0.1)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    opacity: 1,
                    transform: 'translateY(-1px)',
                    boxShadow: isOverlapping
                      ? '0 0 12px rgba(255, 77, 79, 0.8)'
                      : '0 2px 6px rgba(0,0,0,0.15)',
                    '& [data-drag-handle="true"]': {
                      opacity: 1
                    }
                  }
                }}
                onMouseDown={(e) => onEffectDrag(e, effect.id, 'move')}
                onClick={(e) => onEffectClick(effect.id, e)}
              >
                {/* Start Handle */}
                <Box
                  data-drag-handle="true"
                  sx={{
                    position: 'absolute',
                    left: -2,
                    top: 0,
                    bottom: 0,
                    width: '6px',
                    bgcolor: 'rgba(255,255,255,0.8)',
                    cursor: 'ew-resize',
                    borderRadius: '2px 0 0 2px',
                    opacity: 0,
                    transition: 'opacity 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,1)',
                      opacity: 1,
                    }
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    onEffectDrag(e, effect.id, 'start');
                  }}
                />

                {/* Label with time range */}
                <Box sx={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 0.25,
                }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {isOverlapping && (
                      <Warning
                        sx={{
                          fontSize: 11,
                          color: '#fff',
                          filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.5))',
                        }}
                      />
                    )}
                    <Typography sx={{
                      color: 'white',
                      fontSize: '9px',
                      fontWeight: 600,
                      userSelect: 'none',
                      textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                    }}>
                      {effect.label}
                    </Typography>
                  </Box>
                  <Typography sx={{
                    color: 'rgba(255, 255, 255, 0.9)',
                    fontSize: '8px',
                    fontFamily: 'monospace',
                    userSelect: 'none',
                    textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                  }}>
                    {(() => {
                      const startTime = (effect.startFrame / 100) * duration;
                      const endTime = (effect.endFrame / 100) * duration;
                      return `${formatTime(startTime, true)} - ${formatTime(endTime, true)}`;
                    })()}
                  </Typography>
                </Box>

                {/* Delete Button */}
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEffectDelete(effect.id);
                  }}
                  sx={{
                    p: 0.25,
                    color: 'rgba(255,255,255,0.9)',
                    opacity: 0.8,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,0.2)',
                      opacity: 1,
                      transform: 'scale(1.1)'
                    }
                  }}
                >
                  <Delete sx={{ fontSize: 12 }} />
                </IconButton>

                {/* End Handle */}
                <Box
                  data-drag-handle="true"
                  sx={{
                    position: 'absolute',
                    right: -2,
                    top: 0,
                    bottom: 0,
                    width: '6px',
                    bgcolor: 'rgba(255,255,255,0.8)',
                    cursor: 'ew-resize',
                    borderRadius: '0 2px 2px 0',
                    opacity: 0,
                    transition: 'opacity 0.2s ease',
                    '&:hover': {
                      bgcolor: 'rgba(255,255,255,1)',
                      opacity: 1,
                    }
                  }}
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    onEffectDrag(e, effect.id, 'end');
                  }}
                />
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
};

export default TimelineEffectsTrack;

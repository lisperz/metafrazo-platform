/**
 * Video Player Section Component
 *
 * Contains the video player with overlays for:
 * - Drawing rectangles (effects)
 * - Existing effects (erasure, protection, text)
 * - Draggable and resizable effect regions
 * - Speaker selection bounding box
 */

import React from 'react';
import ReactPlayer from 'react-player';
import { Rnd } from 'react-rnd';
import { Box, Typography, Button, IconButton } from '@mui/material';
import { Close } from '@mui/icons-material';
import { VideoEffect, useEffectsStore, GlobalSpeakerBox } from '../../../../store/effectsStore';
import { VideoHandlers } from '../hooks/useVideoHandlers';
import { EffectHandlers } from '../hooks/useEffectHandlers';
import { formatTime as formatTimeUtil } from '../../../../utils/timelineUtils';

interface VideoPlayerSectionProps {
  playerRef: React.RefObject<ReactPlayer | null>;
  videoContainerRef: React.RefObject<HTMLDivElement | null>;
  videoUrl: string;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  effects: VideoEffect[];
  videoHandlers: VideoHandlers;
  effectHandlers: EffectHandlers;
  updateEffect: (id: string, updates: Partial<VideoEffect>) => void;
  deleteEffect: (id: string) => void;
  setStoreTime: (time: number) => void;
}

export const VideoPlayerSection: React.FC<VideoPlayerSectionProps> = ({
  playerRef,
  videoContainerRef,
  videoUrl,
  isPlaying,
  currentTime,
  duration,
  effects,
  videoHandlers,
  effectHandlers,
  updateEffect,
  deleteEffect,
  setStoreTime,
}) => {
  // Get speaker selection state from store
  const {
    globalSpeakerBox,
    isSpeakerSelectionMode,
    setGlobalSpeakerBox,
    confirmSpeakerSelection,
    cancelSpeakerSelection,
    clearSpeakerBox,
  } = useEffectsStore();

  const formatTime = (seconds: number, includeMs: boolean = false): string => {
    if (includeMs) {
      return formatTimeUtil(seconds);
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStopEditing = () => {
    effectHandlers.handleStopEditing();
  };

  // Handle speaker box drag
  const handleSpeakerBoxDrag = (d: { x: number; y: number }) => {
    if (!videoHandlers.videoBounds || !globalSpeakerBox) return;

    const width = globalSpeakerBox.x2 - globalSpeakerBox.x1;
    const height = globalSpeakerBox.y2 - globalSpeakerBox.y1;
    const newX1 = (d.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width;
    const newY1 = (d.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height;

    setGlobalSpeakerBox({
      x1: Math.max(0, Math.min(1 - width, newX1)),
      y1: Math.max(0, Math.min(1 - height, newY1)),
      x2: Math.max(0, Math.min(1, newX1 + width)),
      y2: Math.max(0, Math.min(1, newY1 + height)),
    });
  };

  // Handle speaker box resize
  const handleSpeakerBoxResize = (
    ref: HTMLElement,
    position: { x: number; y: number }
  ) => {
    if (!videoHandlers.videoBounds) return;

    const newX1 = (position.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width;
    const newY1 = (position.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height;
    const newWidth = parseInt(ref.style.width) / videoHandlers.videoBounds.width;
    const newHeight = parseInt(ref.style.height) / videoHandlers.videoBounds.height;

    setGlobalSpeakerBox({
      x1: Math.max(0, Math.min(1, newX1)),
      y1: Math.max(0, Math.min(1, newY1)),
      x2: Math.max(0, Math.min(1, newX1 + newWidth)),
      y2: Math.max(0, Math.min(1, newY1 + newHeight)),
    });
  };

  return (
    <Box sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '55%',
      bgcolor: '#000',
      p: 2
    }}>
      <Box
        ref={videoContainerRef}
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            effectHandlers.handleStopEditing();
          }
        }}
        sx={{
          width: '100%',
          maxWidth: '900px',
          height: '100%',
          bgcolor: 'black',
          position: 'relative',
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        <ReactPlayer
          ref={playerRef}
          url={videoUrl}
          playing={isPlaying}
          muted={videoHandlers.isMuted}
          width="100%"
          height="100%"
          onReady={videoHandlers.handleReady}
          onProgress={videoHandlers.handleProgress}
          onDuration={videoHandlers.handleDuration}
          onSeek={(seconds: number) => {
            setStoreTime(seconds);
          }}
          onError={(error: any) => {
            console.error('Video playback error:', error);
          }}
          progressInterval={50}
          controls={false}
        />

        {/* Video bounds container for proper constraint */}
        {videoHandlers.videoBounds && (
          <Box
            className="video-bounds-container"
            sx={{
              position: 'absolute',
              left: videoHandlers.videoBounds.x,
              top: videoHandlers.videoBounds.y,
              width: videoHandlers.videoBounds.width,
              height: videoHandlers.videoBounds.height,
              pointerEvents: 'none',
              zIndex: 1,
            }}
          />
        )}

        {/* Drawing Rectangle Overlay */}
        {effectHandlers.isDrawingMode && effectHandlers.currentRect && videoHandlers.videoBounds && (
          <Rnd
            default={{
              x: videoHandlers.videoBounds.x + (effectHandlers.currentRect.x * videoHandlers.videoBounds.width),
              y: videoHandlers.videoBounds.y + (effectHandlers.currentRect.y * videoHandlers.videoBounds.height),
              width: effectHandlers.currentRect.width * videoHandlers.videoBounds.width,
              height: effectHandlers.currentRect.height * videoHandlers.videoBounds.height,
            }}
            bounds=".video-bounds-container"
            onDragStop={(e, d) => {
              if (videoHandlers.videoBounds) {
                effectHandlers.setCurrentRect({
                  x: (d.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width,
                  y: (d.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height,
                  width: effectHandlers.currentRect.width,
                  height: effectHandlers.currentRect.height,
                });
              }
            }}
            onResizeStop={(e, direction, ref, delta, position) => {
              if (videoHandlers.videoBounds) {
                effectHandlers.setCurrentRect({
                  x: (position.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width,
                  y: (position.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height,
                  width: parseInt(ref.style.width) / videoHandlers.videoBounds.width,
                  height: parseInt(ref.style.height) / videoHandlers.videoBounds.height,
                });
              }
            }}
            style={{
              border: `3px solid ${effectHandlers.selectedType === 'erasure' ? '#5B8FF9' : effectHandlers.selectedType === 'protection' ? '#5AD8A6' : '#5D7092'}`,
              backgroundColor: `${effectHandlers.selectedType === 'erasure' ? 'rgba(91, 143, 249, 0.15)' : effectHandlers.selectedType === 'protection' ? 'rgba(90, 216, 166, 0.15)' : 'rgba(93, 112, 146, 0.15)'}`,
              position: 'absolute',
              zIndex: 10,
              boxShadow: '0 0 10px rgba(0, 0, 0, 0.3)',
            }}
          >
            {/* Corner dots for drawing */}
            {(() => {
              const dotColor = effectHandlers.selectedType === 'erasure' ? '#5B8FF9' :
                             effectHandlers.selectedType === 'protection' ? '#5AD8A6' : '#5D7092';
              const hoverColor = effectHandlers.selectedType === 'erasure' ? '#40a9ff' :
                               effectHandlers.selectedType === 'protection' ? '#52c41a' : '#434c5e';

              return (
                <>
                  {[
                    { position: { left: -4, top: -4 }, cursor: 'nw-resize' },
                    { position: { right: -4, top: -4 }, cursor: 'ne-resize' },
                    { position: { left: -4, bottom: -4 }, cursor: 'sw-resize' },
                    { position: { right: -4, bottom: -4 }, cursor: 'se-resize' },
                  ].map((corner, index) => (
                    <Box
                      key={index}
                      sx={{
                        position: 'absolute',
                        ...corner.position,
                        width: 8,
                        height: 8,
                        backgroundColor: dotColor,
                        border: '2px solid white',
                        borderRadius: '50%',
                        cursor: corner.cursor,
                        pointerEvents: 'auto',
                        '&:hover': {
                          backgroundColor: hoverColor,
                          transform: 'scale(1.2)',
                        }
                      }}
                    />
                  ))}
                </>
              );
            })()}

            <Box sx={{
              position: 'absolute',
              top: -50,
              left: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
            }}>
              <Typography sx={{
                fontSize: '10px',
                color: '#fff',
                bgcolor: 'rgba(0, 0, 0, 0.7)',
                px: 1,
                py: 0.5,
                borderRadius: '3px',
                fontFamily: 'monospace',
                whiteSpace: 'nowrap'
              }}>
                {formatTime(currentTime, true)} - {formatTime(Math.min(currentTime + 5, duration), true)}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  onClick={effectHandlers.handleSaveRect}
                  sx={{
                    fontSize: '11px',
                    minWidth: 'auto',
                    px: 1,
                    py: 0.5,
                    bgcolor: '#52c41a',
                    '&:hover': { bgcolor: '#73d13d' }
                  }}
                >
                  Confirm
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={effectHandlers.handleCancelDrawing}
                  sx={{
                    fontSize: '11px',
                    minWidth: 'auto',
                    px: 1,
                    py: 0.5,
                    borderColor: '#ff4d4f',
                    color: '#ff4d4f',
                    '&:hover': {
                      borderColor: '#ff7875',
                      color: '#ff7875'
                    }
                  }}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          </Rnd>
        )}

        {/* Display existing rectangles - Sort by area to show smaller ones on top */}
        {effects.filter(e =>
          currentTime >= e.startTime && currentTime <= e.endTime
        ).sort((a, b) => {
          const areaA = a.region.width * a.region.height;
          const areaB = b.region.width * b.region.height;
          return areaB - areaA;
        }).map((effect, index) => {
          const isEditing = effectHandlers.editingEffectId === effect.id;

          if (isEditing && videoHandlers.videoBounds) {
            return (
              <Rnd
                key={effect.id}
                default={{
                  x: videoHandlers.videoBounds.x + (effect.region.x * videoHandlers.videoBounds.width),
                  y: videoHandlers.videoBounds.y + (effect.region.y * videoHandlers.videoBounds.height),
                  width: effect.region.width * videoHandlers.videoBounds.width,
                  height: effect.region.height * videoHandlers.videoBounds.height,
                }}
                bounds=".video-bounds-container"
                onDragStop={(e, d) => {
                  if (videoHandlers.videoBounds) {
                    const newRegion = {
                      x: (d.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width,
                      y: (d.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height,
                      width: effect.region.width,
                      height: effect.region.height,
                    };
                    updateEffect(effect.id, { region: newRegion });
                  }
                }}
                onResizeStop={(e, direction, ref, delta, position) => {
                  if (videoHandlers.videoBounds) {
                    const newRegion = {
                      x: (position.x - videoHandlers.videoBounds.x) / videoHandlers.videoBounds.width,
                      y: (position.y - videoHandlers.videoBounds.y) / videoHandlers.videoBounds.height,
                      width: parseInt(ref.style.width) / videoHandlers.videoBounds.width,
                      height: parseInt(ref.style.height) / videoHandlers.videoBounds.height,
                    };
                    updateEffect(effect.id, { region: newRegion });
                  }
                }}
                style={{
                  border: `2px solid ${
                    effect.type === 'erasure' ? '#5B8FF9' :
                    effect.type === 'protection' ? '#5AD8A6' : '#5D7092'
                  }`,
                  backgroundColor: `${
                    effect.type === 'erasure' ? 'rgba(91, 143, 249, 0.1)' :
                    effect.type === 'protection' ? 'rgba(90, 216, 166, 0.1)' :
                    'rgba(93, 112, 146, 0.1)'
                  }`,
                  position: 'absolute',
                  zIndex: 20 - index,
                  outline: '2px dashed #fff',
                  outlineOffset: '4px',
                }}
              >
                {/* Corner dots and controls for editing */}
                <>
                  {(() => {
                    const dotColor = effect.type === 'erasure' ? '#5B8FF9' :
                                   effect.type === 'protection' ? '#5AD8A6' : '#5D7092';
                    const hoverColor = effect.type === 'erasure' ? '#40a9ff' :
                                     effect.type === 'protection' ? '#52c41a' : '#434c5e';

                    return (
                      <>
                        {[
                          { position: { left: -4, top: -4 }, cursor: 'nw-resize' },
                          { position: { right: -4, top: -4 }, cursor: 'ne-resize' },
                          { position: { left: -4, bottom: -4 }, cursor: 'sw-resize' },
                          { position: { right: -4, bottom: -4 }, cursor: 'se-resize' },
                        ].map((corner, cornerIndex) => (
                          <Box
                            key={cornerIndex}
                            sx={{
                              position: 'absolute',
                              ...corner.position,
                              width: 8,
                              height: 8,
                              backgroundColor: dotColor,
                              border: '2px solid white',
                              borderRadius: '50%',
                              cursor: corner.cursor,
                              pointerEvents: 'auto',
                              '&:hover': {
                                backgroundColor: hoverColor,
                                transform: 'scale(1.2)',
                              }
                            }}
                          />
                        ))}
                      </>
                    );
                  })()}
                </>

                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteEffect(effect.id);
                    effectHandlers.handleStopEditing();
                  }}
                  sx={{
                    position: 'absolute',
                    top: '50%',
                    right: -30,
                    transform: 'translateY(-50%)',
                    width: 24,
                    height: 24,
                    bgcolor: '#ff4d4f',
                    color: 'white',
                    '&:hover': {
                      bgcolor: '#ff7875',
                      transform: 'translateY(-50%) scale(1.1)',
                    },
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    zIndex: 20,
                  }}
                >
                  <Close sx={{ fontSize: 14 }} />
                </IconButton>

                <Box sx={{
                  position: 'absolute',
                  top: -30,
                  left: 0,
                  display: 'flex',
                  gap: 1,
                }}>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={handleStopEditing}
                    sx={{
                      fontSize: '11px',
                      minWidth: 'auto',
                      px: 1,
                      py: 0.5,
                      bgcolor: '#52c41a',
                      '&:hover': { bgcolor: '#73d13d' }
                    }}
                  >
                    Done
                  </Button>
                </Box>
              </Rnd>
            );
          }

          if (!videoHandlers.videoBounds) return null;

          return (
            <Box
              key={effect.id}
              sx={{
                position: 'absolute',
                left: `${videoHandlers.videoBounds.x + (effect.region.x * videoHandlers.videoBounds.width)}px`,
                top: `${videoHandlers.videoBounds.y + (effect.region.y * videoHandlers.videoBounds.height)}px`,
                width: `${effect.region.width * videoHandlers.videoBounds.width}px`,
                height: `${effect.region.height * videoHandlers.videoBounds.height}px`,
                border: `2px solid ${
                  effect.type === 'erasure' ? '#5B8FF9' :
                  effect.type === 'protection' ? '#5AD8A6' : '#5D7092'
                }`,
                backgroundColor: `${
                  effect.type === 'erasure' ? 'rgba(91, 143, 249, 0.1)' :
                  effect.type === 'protection' ? 'rgba(90, 216, 166, 0.1)' :
                  'rgba(93, 112, 146, 0.1)'
                }`,
                pointerEvents: 'auto',
                cursor: 'pointer',
                zIndex: 15 - index,
                '&:hover': {
                  opacity: 0.8,
                  '& .delete-button': {
                    opacity: 1,
                  }
                }
              }}
              onClick={() => effectHandlers.handleEffectClick(effect.id, {} as React.MouseEvent)}
            >
              <IconButton
                className="delete-button"
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteEffect(effect.id);
                }}
                sx={{
                  position: 'absolute',
                  top: '50%',
                  right: -30,
                  transform: 'translateY(-50%)',
                  width: 24,
                  height: 24,
                  bgcolor: '#ff4d4f',
                  color: 'white',
                  opacity: 0,
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: '#ff7875',
                    transform: 'translateY(-50%) scale(1.1)',
                    opacity: '1 !important',
                  },
                  boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                  zIndex: 20,
                }}
              >
                <Close sx={{ fontSize: 14 }} />
              </IconButton>
            </Box>
          );
        })}

        {/* Speaker Selection Bounding Box Overlay */}
        {isSpeakerSelectionMode && globalSpeakerBox && videoHandlers.videoBounds && (
          <Rnd
            position={{
              x: videoHandlers.videoBounds.x + (globalSpeakerBox.x1 * videoHandlers.videoBounds.width),
              y: videoHandlers.videoBounds.y + (globalSpeakerBox.y1 * videoHandlers.videoBounds.height),
            }}
            size={{
              width: (globalSpeakerBox.x2 - globalSpeakerBox.x1) * videoHandlers.videoBounds.width,
              height: (globalSpeakerBox.y2 - globalSpeakerBox.y1) * videoHandlers.videoBounds.height,
            }}
            bounds=".video-bounds-container"
            onDragStop={(e, d) => handleSpeakerBoxDrag(d)}
            onResizeStop={(e, direction, ref, delta, position) => {
              handleSpeakerBoxResize(ref, position);
            }}
            style={{
              border: '3px solid #f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.15)',
              position: 'absolute',
              zIndex: 25,
              boxShadow: '0 0 10px rgba(245, 158, 11, 0.5)',
            }}
          >
            {/* Corner dots for speaker box */}
            {[
              { position: { left: -4, top: -4 }, cursor: 'nw-resize' },
              { position: { right: -4, top: -4 }, cursor: 'ne-resize' },
              { position: { left: -4, bottom: -4 }, cursor: 'sw-resize' },
              { position: { right: -4, bottom: -4 }, cursor: 'se-resize' },
            ].map((corner, index) => (
              <Box
                key={index}
                sx={{
                  position: 'absolute',
                  ...corner.position,
                  width: 8,
                  height: 8,
                  backgroundColor: '#f59e0b',
                  border: '2px solid white',
                  borderRadius: '50%',
                  cursor: corner.cursor,
                  pointerEvents: 'auto',
                  '&:hover': {
                    backgroundColor: '#d97706',
                    transform: 'scale(1.2)',
                  }
                }}
              />
            ))}

            {/* Speaker box label and controls */}
            <Box sx={{
              position: 'absolute',
              top: -55,
              left: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
            }}>
              <Typography sx={{
                fontSize: '11px',
                color: '#fff',
                bgcolor: 'rgba(245, 158, 11, 0.9)',
                px: 1,
                py: 0.5,
                borderRadius: '3px',
                fontWeight: 600,
                whiteSpace: 'nowrap'
              }}>
                Speaker Face Region
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  onClick={() => confirmSpeakerSelection(globalSpeakerBox)}
                  sx={{
                    fontSize: '11px',
                    minWidth: 'auto',
                    px: 1,
                    py: 0.5,
                    bgcolor: '#52c41a',
                    '&:hover': { bgcolor: '#73d13d' }
                  }}
                >
                  Confirm
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={cancelSpeakerSelection}
                  sx={{
                    fontSize: '11px',
                    minWidth: 'auto',
                    px: 1,
                    py: 0.5,
                    borderColor: '#ff4d4f',
                    color: '#ff4d4f',
                    '&:hover': {
                      borderColor: '#ff7875',
                      color: '#ff7875'
                    }
                  }}
                >
                  Cancel
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={clearSpeakerBox}
                  sx={{
                    fontSize: '11px',
                    minWidth: 'auto',
                    px: 1,
                    py: 0.5,
                    borderColor: '#666',
                    color: '#fff',
                    bgcolor: 'rgba(0,0,0,0.5)',
                    '&:hover': {
                      borderColor: '#999',
                      bgcolor: 'rgba(0,0,0,0.7)'
                    }
                  }}
                >
                  Clear
                </Button>
              </Box>
            </Box>
          </Rnd>
        )}

        {/* Display confirmed speaker box (when not in selection mode) */}
        {!isSpeakerSelectionMode && globalSpeakerBox && videoHandlers.videoBounds && (
          <Box
            sx={{
              position: 'absolute',
              left: `${videoHandlers.videoBounds.x + (globalSpeakerBox.x1 * videoHandlers.videoBounds.width)}px`,
              top: `${videoHandlers.videoBounds.y + (globalSpeakerBox.y1 * videoHandlers.videoBounds.height)}px`,
              width: `${(globalSpeakerBox.x2 - globalSpeakerBox.x1) * videoHandlers.videoBounds.width}px`,
              height: `${(globalSpeakerBox.y2 - globalSpeakerBox.y1) * videoHandlers.videoBounds.height}px`,
              border: '2px dashed #f59e0b',
              backgroundColor: 'rgba(245, 158, 11, 0.05)',
              pointerEvents: 'none',
              zIndex: 5,
            }}
          >
            <Typography sx={{
              position: 'absolute',
              top: -20,
              left: 0,
              fontSize: '10px',
              color: '#f59e0b',
              bgcolor: 'rgba(0,0,0,0.7)',
              px: 0.5,
              py: 0.25,
              borderRadius: '2px',
              whiteSpace: 'nowrap'
            }}>
              Speaker
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

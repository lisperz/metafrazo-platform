/**
 * SpeakerBoxDrawer - Component for drawing speaker bounding box on video frame
 * Uses react-rnd for drag/resize functionality
 * Coordinates are normalized (0-1) relative to video dimensions
 */

import React from 'react';
import { Rnd } from 'react-rnd';
import { Box, Typography, Button } from '@mui/material';
import { SpeakerBox } from '../../../../types/segments';

interface VideoBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface SpeakerBoxDrawerProps {
  /** Whether the drawer is active */
  isActive: boolean;
  /** Current speaker box (normalized coordinates 0-1) */
  speakerBox: SpeakerBox | null;
  /** Video bounds in screen pixels */
  videoBounds: VideoBounds | null;
  /** Callback when box is updated */
  onBoxUpdate: (box: SpeakerBox) => void;
  /** Callback to save the box */
  onSave: () => void;
  /** Callback to cancel/clear the box */
  onCancel: () => void;
  /** Callback to clear existing box */
  onClear?: () => void;
}

const SpeakerBoxDrawer: React.FC<SpeakerBoxDrawerProps> = ({
  isActive,
  speakerBox,
  videoBounds,
  onBoxUpdate,
  onSave,
  onCancel,
  onClear,
}) => {
  if (!isActive || !videoBounds) {
    return null;
  }

  // Default box position (center of video, 20% size)
  const defaultBox: SpeakerBox = {
    x1: 0.4,
    y1: 0.3,
    x2: 0.6,
    y2: 0.7,
    method: 'manual',
  };

  const box = speakerBox || defaultBox;

  // Convert normalized coordinates to screen pixels
  const screenX = videoBounds.x + box.x1 * videoBounds.width;
  const screenY = videoBounds.y + box.y1 * videoBounds.height;
  const screenWidth = (box.x2 - box.x1) * videoBounds.width;
  const screenHeight = (box.y2 - box.y1) * videoBounds.height;

  // Colors for speaker box (distinct from erasure/protection)
  const colors = {
    border: '#f59e0b',  // Amber - matches Pro theme
    bg: 'rgba(245, 158, 11, 0.2)',
    dot: '#f59e0b',
    hover: '#d97706',
  };

  const renderCornerDot = (position: 'tl' | 'tr' | 'bl' | 'br') => {
    const positionStyles = {
      tl: { left: -5, top: -5, cursor: 'nw-resize' },
      tr: { right: -5, top: -5, cursor: 'ne-resize' },
      bl: { left: -5, bottom: -5, cursor: 'sw-resize' },
      br: { right: -5, bottom: -5, cursor: 'se-resize' },
    };

    return (
      <Box
        sx={{
          position: 'absolute',
          ...positionStyles[position],
          width: 10,
          height: 10,
          backgroundColor: colors.dot,
          border: '2px solid white',
          borderRadius: '50%',
          pointerEvents: 'auto',
          '&:hover': {
            backgroundColor: colors.hover,
            transform: 'scale(1.2)',
          },
        }}
      />
    );
  };

  const handleDragStop = (_e: unknown, d: { x: number; y: number }) => {
    const newX1 = (d.x - videoBounds.x) / videoBounds.width;
    const newY1 = (d.y - videoBounds.y) / videoBounds.height;
    const width = box.x2 - box.x1;
    const height = box.y2 - box.y1;

    onBoxUpdate({
      x1: Math.max(0, Math.min(1 - width, newX1)),
      y1: Math.max(0, Math.min(1 - height, newY1)),
      x2: Math.max(0, Math.min(1, newX1 + width)),
      y2: Math.max(0, Math.min(1, newY1 + height)),
      method: 'manual',
    });
  };

  const handleResizeStop = (
    _e: unknown,
    _direction: unknown,
    ref: HTMLElement,
    _delta: unknown,
    position: { x: number; y: number }
  ) => {
    const newX1 = (position.x - videoBounds.x) / videoBounds.width;
    const newY1 = (position.y - videoBounds.y) / videoBounds.height;
    const newWidth = parseInt(ref.style.width) / videoBounds.width;
    const newHeight = parseInt(ref.style.height) / videoBounds.height;

    onBoxUpdate({
      x1: Math.max(0, Math.min(1, newX1)),
      y1: Math.max(0, Math.min(1, newY1)),
      x2: Math.max(0, Math.min(1, newX1 + newWidth)),
      y2: Math.max(0, Math.min(1, newY1 + newHeight)),
      method: 'manual',
    });
  };

  return (
    <Rnd
      position={{ x: screenX, y: screenY }}
      size={{ width: screenWidth, height: screenHeight }}
      bounds="parent"
      onDragStop={handleDragStop}
      onResizeStop={handleResizeStop}
      minWidth={30}
      minHeight={30}
      style={{
        border: `3px solid ${colors.border}`,
        backgroundColor: colors.bg,
        position: 'absolute',
        zIndex: 100,
        boxShadow: '0 0 15px rgba(245, 158, 11, 0.5)',
      }}
    >
      {/* Corner dots for resize handles */}
      {renderCornerDot('tl')}
      {renderCornerDot('tr')}
      {renderCornerDot('bl')}
      {renderCornerDot('br')}

      {/* Label */}
      <Box
        sx={{
          position: 'absolute',
          top: -28,
          left: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
        }}
      >
        <Typography
          sx={{
            fontSize: '11px',
            color: '#fff',
            bgcolor: 'rgba(245, 158, 11, 0.9)',
            px: 1,
            py: 0.3,
            borderRadius: '3px',
            fontWeight: 600,
            whiteSpace: 'nowrap',
          }}
        >
          Speaker Face
        </Typography>
      </Box>

      {/* Action buttons */}
      <Box
        sx={{
          position: 'absolute',
          bottom: -36,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: 1,
        }}
      >
        <Button
          size="small"
          variant="contained"
          onClick={onSave}
          sx={{
            fontSize: '11px',
            minWidth: 'auto',
            px: 1.5,
            py: 0.5,
            bgcolor: '#10b981',
            '&:hover': { bgcolor: '#059669' },
          }}
        >
          Confirm
        </Button>
        {onClear && speakerBox && (
          <Button
            size="small"
            variant="outlined"
            onClick={onClear}
            sx={{
              fontSize: '11px',
              minWidth: 'auto',
              px: 1.5,
              py: 0.5,
              borderColor: '#6b7280',
              color: '#fff',
              bgcolor: 'rgba(107, 114, 128, 0.5)',
              '&:hover': {
                borderColor: '#9ca3af',
                bgcolor: 'rgba(107, 114, 128, 0.7)',
              },
            }}
          >
            Clear
          </Button>
        )}
        <Button
          size="small"
          variant="outlined"
          onClick={onCancel}
          sx={{
            fontSize: '11px',
            minWidth: 'auto',
            px: 1.5,
            py: 0.5,
            borderColor: '#ef4444',
            color: '#fff',
            bgcolor: 'rgba(239, 68, 68, 0.5)',
            '&:hover': {
              borderColor: '#f87171',
              bgcolor: 'rgba(239, 68, 68, 0.7)',
            },
          }}
        >
          Cancel
        </Button>
      </Box>
    </Rnd>
  );
};

export default SpeakerBoxDrawer;

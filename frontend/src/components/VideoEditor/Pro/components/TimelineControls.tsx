import React from 'react';
import { Box, Typography, Button, IconButton, Slider } from '@mui/material';
import { PlayArrow, Pause, Undo, Redo, VolumeUp, VolumeOff, Add, Face } from '@mui/icons-material';

interface TimelineControlsProps {
  isPlaying: boolean;
  isMuted: boolean;
  currentTime: number;
  duration: number;
  timelineZoom: number;
  canUndo: boolean;
  canRedo: boolean;
  segmentCount: number;
  hasSpeakerBox?: boolean;
  isSpeakerSelectionMode?: boolean;
  onPlayPause: () => void;
  onVolumeToggle: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onZoomChange: (zoom: number) => void;
  onAddEffect: (type: 'erasure' | 'protection' | 'text') => void;
  onAddSegment: () => void;
  onSelectSpeaker?: () => void;
  formatTime: (seconds: number, includeMs?: boolean) => string;
}

const TimelineControls: React.FC<TimelineControlsProps> = ({
  isPlaying,
  isMuted,
  currentTime,
  duration,
  timelineZoom,
  canUndo,
  canRedo,
  segmentCount,
  hasSpeakerBox = false,
  isSpeakerSelectionMode = false,
  onPlayPause,
  onVolumeToggle,
  onUndo,
  onRedo,
  onZoomChange,
  onAddEffect,
  onAddSegment,
  onSelectSpeaker,
  formatTime,
}) => {
  const renderColorButton = (
    label: string,
    color: string,
    type: 'erasure' | 'protection' | 'text'
  ) => (
    <Button
      variant="contained"
      size="small"
      onClick={() => onAddEffect(type)}
      startIcon={
        <Box sx={{
          width: 16,
          height: 16,
          borderRadius: '50%',
          bgcolor: color
        }} />
      }
      sx={{
        bgcolor: 'white',
        color: '#333',
        border: '1px solid #d9d9d9',
        fontSize: '13px',
        textTransform: 'none',
        '&:hover': {
          bgcolor: '#fafafa',
          borderColor: type === 'erasure' ? '#40a9ff' : type === 'protection' ? '#52c41a' : '#666'
        }
      }}
    >
      {label}
    </Button>
  );

  return (
    <>
      <IconButton
        onClick={onPlayPause}
        sx={{
          bgcolor: '#1890ff',
          color: 'white',
          '&:hover': { bgcolor: '#40a9ff' }
        }}
      >
        {isPlaying ? <Pause /> : <PlayArrow />}
      </IconButton>

      {renderColorButton('Add Erasure Area', '#5B8FF9', 'erasure')}
      {renderColorButton('Add Protection Area', '#5AD8A6', 'protection')}
      {renderColorButton('Erase Text', '#5D7092', 'text')}

      {/* Add Segment Button - Pro Feature */}
      <Button
        variant="contained"
        size="small"
        onClick={onAddSegment}
        disabled={segmentCount >= 10}
        startIcon={<Add />}
        sx={{
          bgcolor: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
          background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
          color: 'white',
          border: 'none',
          fontSize: '13px',
          textTransform: 'none',
          fontWeight: 600,
          '&:hover': {
            background: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)',
          },
          '&:disabled': {
            background: '#d9d9d9',
            color: '#999'
          }
        }}
      >
        Add Segment
      </Button>

      {/* Select Speaker Button - For multi-person videos */}
      {onSelectSpeaker && (
        <Button
          variant="contained"
          size="small"
          onClick={onSelectSpeaker}
          startIcon={<Face />}
          sx={{
            bgcolor: isSpeakerSelectionMode
              ? '#10b981'
              : hasSpeakerBox
                ? '#059669'
                : '#6366f1',
            color: 'white',
            border: 'none',
            fontSize: '13px',
            textTransform: 'none',
            fontWeight: 600,
            '&:hover': {
              bgcolor: isSpeakerSelectionMode
                ? '#059669'
                : hasSpeakerBox
                  ? '#047857'
                  : '#4f46e5',
            },
          }}
        >
          {isSpeakerSelectionMode
            ? 'Drawing...'
            : hasSpeakerBox
              ? 'Speaker Set ✓'
              : 'Select Speaker'}
        </Button>
      )}
    </>
  );
};

export default TimelineControls;

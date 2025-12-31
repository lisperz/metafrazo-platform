/**
 * Segment Manager - Displays list of video segments with edit/delete actions
 */

import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Stack,
  Button,
} from '@mui/material';
import {
  Edit,
  Delete,
  AudioFile,
} from '@mui/icons-material';
import { VideoSegment } from '../../../types/segments';
import { useSegmentsStore, formatSegmentTime, getSegmentDuration } from '../../../store/segmentsStore';

interface SegmentManagerProps {
  segments: VideoSegment[];
  currentTime: number;
  onEditSegment: (segmentId: string) => void;
}

const SegmentManager: React.FC<SegmentManagerProps> = ({
  segments,
  currentTime,
  onEditSegment,
}) => {
  const { deleteSegment } = useSegmentsStore();

  const handleDelete = (segmentId: string) => {
    if (window.confirm('Are you sure you want to delete this segment?')) {
      deleteSegment(segmentId);
    }
  };

  // Check if current time is within a segment
  const isSegmentActive = (segment: VideoSegment) => {
    return currentTime >= segment.startTime && currentTime <= segment.endTime;
  };

  if (segments.length === 0) {
    return (
      <Box sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        textAlign: 'center',
        color: 'text.secondary',
      }}>
        <Typography variant="h6" gutterBottom>
          No segments yet
        </Typography>
        <Typography variant="body2">
          Click "Add Segment" to create your first segment with custom audio
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      {segments.map((segment, index) => {
        const isActive = isSegmentActive(segment);
        const segmentDuration = getSegmentDuration(segment);

        return (
          <Card
            key={segment.id}
            sx={{
              borderLeft: `4px solid ${segment.color}`,
              transition: 'all 0.2s ease',
              ...(isActive && {
                boxShadow: `0 4px 12px ${segment.color}40`,
                transform: 'scale(1.02)',
              }),
            }}
          >
            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              {/* Segment Header */}
              <Box sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: 1.5,
              }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={`Segment ${index + 1}`}
                    size="small"
                    sx={{
                      bgcolor: segment.color,
                      color: 'white',
                      fontWeight: 600,
                    }}
                  />
                  {isActive && (
                    <Chip
                      label="Playing"
                      size="small"
                      color="success"
                      sx={{ fontWeight: 600 }}
                    />
                  )}
                </Box>

                <Box>
                  <IconButton
                    size="small"
                    onClick={() => onEditSegment(segment.id)}
                    sx={{ color: 'primary.main' }}
                  >
                    <Edit fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(segment.id)}
                    sx={{ color: 'error.main' }}
                  >
                    <Delete fontSize="small" />
                  </IconButton>
                </Box>
              </Box>

              {/* Time Range */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  ⏱️ Time Range
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {formatSegmentTime(segment.startTime)} → {formatSegmentTime(segment.endTime)}
                  {' '}({formatSegmentTime(segmentDuration)})
                </Typography>
              </Box>

              {/* Audio Info */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  🎵 Audio
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AudioFile fontSize="small" color="action" />
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {segment.audioInput.fileName}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {((segment.audioInput.fileSize ?? 0) / 1024 / 1024).toFixed(2)} MB
                </Typography>
              </Box>

              {/* Label (if exists) */}
              {segment.label && (
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    📝 Label
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {segment.label}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
};

export default SegmentManager;

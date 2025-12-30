/**
 * Segment Dialog - Add or edit video segment with audio input
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  Alert,
  IconButton,
  Paper,
  Checkbox,
  FormControlLabel,
  Collapse,
  Radio,
  RadioGroup,
  Chip,
  Divider,
} from '@mui/material';
import {
  Close,
  CloudUpload,
  CheckCircle,
  ContentCut,
  AudioFile,
  Refresh,
} from '@mui/icons-material';
import {
  useSegmentsStore,
  createNewSegment,
  validateAudioFile,
  formatSegmentTime,
} from '../../../store/segmentsStore';
import { AudioInput, VideoSegment } from '../../../types/segments';
import { getSegmentOverlaps, formatOverlapWarning } from '../../../utils/segmentOverlapDetection';

interface SegmentDialogProps {
  open: boolean;
  onClose: () => void;
  editingSegmentId: string | null;
  videoDuration: number;
  currentTime: number;
}

const SegmentDialog: React.FC<SegmentDialogProps> = ({
  open,
  onClose,
  editingSegmentId,
  videoDuration,
  currentTime,
}) => {
  const {
    addSegment,
    updateSegment,
    getSegmentById,
    validateSegmentTimes,
    getAllAudioFiles,
    addAudioFile,
    getAudioFileByRefId,
    segments,
  } = useSegmentsStore();

  // Form state
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(0);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [selectedAudioRefId, setSelectedAudioRefId] = useState<string | null>(null);
  const [audioSelectionMode, setAudioSelectionMode] = useState<'existing' | 'upload'>('upload');
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Audio crop state (optional)
  const [enableAudioCrop, setEnableAudioCrop] = useState(false);
  const [audioStartTime, setAudioStartTime] = useState<number | null>(null);
  const [audioEndTime, setAudioEndTime] = useState<number | null>(null);

  // Initialize form when dialog opens
  useEffect(() => {
    if (open) {
      const existingAudioFiles = getAllAudioFiles();

      if (editingSegmentId) {
        // Edit mode - load existing segment
        const segment = getSegmentById(editingSegmentId);
        if (segment) {
          setStartTime(segment.startTime);
          setEndTime(segment.endTime);
          setLabel(segment.label || '');
          setSelectedAudioRefId(segment.audioInput.refId);
          setAudioFile(segment.audioInput.file ?? null);
          setAudioSelectionMode('existing');

          // Load audio crop settings if they exist
          const hasAudioCrop = segment.audioInput.startTime !== null || segment.audioInput.startTime !== undefined ||
                               segment.audioInput.endTime !== null || segment.audioInput.endTime !== undefined;
          setEnableAudioCrop(hasAudioCrop);
          setAudioStartTime(segment.audioInput.startTime ?? null);
          setAudioEndTime(segment.audioInput.endTime ?? null);
        }
      } else {
        // Add mode - use current time as start
        const suggestedStart = Math.floor(currentTime);
        const suggestedEnd = Math.min(suggestedStart + 15, Math.floor(videoDuration));
        setStartTime(suggestedStart);
        setEndTime(suggestedEnd);
        setLabel('');
        setAudioFile(null);
        setSelectedAudioRefId(null);
        setEnableAudioCrop(false);
        setAudioStartTime(null);
        setAudioEndTime(null);

        // If there are existing audio files, default to using existing mode
        if (existingAudioFiles.length > 0) {
          setAudioSelectionMode('existing');
          setSelectedAudioRefId(existingAudioFiles[0].refId);
          setAudioFile(existingAudioFiles[0].file);
        } else {
          setAudioSelectionMode('upload');
        }
      }
      setError(null);
    }
  }, [open, editingSegmentId, currentTime, videoDuration, getSegmentById, getAllAudioFiles]);

  const handleAudioFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validation = validateAudioFile(file);
      if (!validation.valid) {
        setError(validation.error || 'Invalid audio file');
        return;
      }
      setAudioFile(file);
      setSelectedAudioRefId(null); // Clear refId when uploading new file
      setError(null);
    }
  };

  const handleExistingAudioSelect = (refId: string) => {
    const audioFileData = getAudioFileByRefId(refId);
    if (audioFileData) {
      setSelectedAudioRefId(refId);
      setAudioFile(audioFileData.file);
      setError(null);
    }
  };

  const handleSubmit = () => {
    console.log('=== SEGMENT DIALOG SUBMIT ===');
    console.log('Audio file:', audioFile);
    console.log('Editing segment ID:', editingSegmentId);
    console.log('Start time:', startTime);
    console.log('End time:', endTime);
    console.log('Label:', label);

    // Validate audio file is selected
    if (!audioFile && !editingSegmentId) {
      console.error('No audio file selected!');
      setError('Please select an audio file');
      return;
    }

    // Validate time range
    const validation = validateSegmentTimes(startTime, endTime, editingSegmentId || undefined);
    if (!validation.valid) {
      console.error('Validation failed:', validation.error);
      setError(validation.error || 'Invalid time range');
      return;
    }

    // Validate audio crop times if enabled
    if (enableAudioCrop) {
      if (audioStartTime !== null && audioEndTime !== null && audioStartTime >= audioEndTime) {
        setError('Audio start time must be before end time');
        return;
      }
      if (audioStartTime !== null && audioStartTime < 0) {
        setError('Audio start time cannot be negative');
        return;
      }
      // If audio crop is enabled, ensure both start and end times are set
      if (audioStartTime === null || audioEndTime === null) {
        setError('When using audio crop, both start time and end time must be set');
        return;
      }
    }

    // Validate segment duration doesn't exceed audio duration
    if (audioFile || (editingSegmentId && selectedAudioRefId)) {
      // Get audio file (either new or existing)
      let fileToValidate = audioFile;

      if (!fileToValidate && editingSegmentId && selectedAudioRefId) {
        // Get existing audio file
        const existingAudioFile = getAudioFileByRefId(selectedAudioRefId);
        if (existingAudioFile) {
          fileToValidate = existingAudioFile.file;
        }
      }

      if (fileToValidate) {
        // Get audio duration from HTML5 Audio API
        const audio = new Audio();
        const objectUrl = URL.createObjectURL(fileToValidate);

        audio.addEventListener('loadedmetadata', () => {
          const audioDuration = audio.duration;
          URL.revokeObjectURL(objectUrl);

          // Calculate available audio duration after crop
          const audioStart = enableAudioCrop ? (audioStartTime ?? 0) : 0;
          const audioEnd = enableAudioCrop ? (audioEndTime ?? audioDuration) : audioDuration;
          const availableAudioDuration = audioEnd - audioStart;

          const segmentDuration = endTime - startTime;

          if (segmentDuration > availableAudioDuration) {
            setError(
              `Segment duration (${segmentDuration.toFixed(2)}s) exceeds available audio duration (${availableAudioDuration.toFixed(2)}s). ` +
              `Please reduce the segment end time or adjust audio crop settings.`
            );
            return;
          }

          // Continue with submission
          proceedWithSubmit();
        });

        audio.addEventListener('error', () => {
          URL.revokeObjectURL(objectUrl);
          setError('Failed to load audio file. Please try again.');
        });

        audio.src = objectUrl;
        return; // Wait for audio metadata to load
      }
    }

    // If no audio file (shouldn't happen), proceed directly
    proceedWithSubmit();
  };

  const proceedWithSubmit = () => {

    // Determine the refId to use
    let finalRefId: string;

    if (audioSelectionMode === 'existing' && selectedAudioRefId) {
      // Reuse existing audio file refId
      finalRefId = selectedAudioRefId;
      console.log('🔄 Reusing existing audio file with refId:', finalRefId);
    } else {
      // Upload new audio file and get its refId
      const uploadedAudioFile = addAudioFile(audioFile!);
      finalRefId = uploadedAudioFile.refId;
      console.log('📤 Uploaded new audio file with refId:', finalRefId);
    }

    if (editingSegmentId) {
      // Update existing segment
      const updates: any = {
        startTime,
        endTime,
        label,
      };
      if (audioFile) {
        const audioInput: AudioInput = {
          refId: finalRefId,
          file: audioFile,
          fileName: audioFile.name,
          fileSize: audioFile.size,
          startTime: enableAudioCrop ? audioStartTime ?? undefined : undefined,
          endTime: enableAudioCrop ? audioEndTime ?? undefined : undefined,
        };
        updates.audioInput = audioInput;
      }
      updateSegment(editingSegmentId, updates);
    } else {
      // Create new segment
      console.log('DEBUG: enableAudioCrop=', enableAudioCrop);
      console.log('DEBUG: audioStartTime=', audioStartTime);
      console.log('DEBUG: audioEndTime=', audioEndTime);
      console.log('DEBUG: segment startTime=', startTime);
      console.log('DEBUG: segment endTime=', endTime);

      const audioInput: AudioInput = {
        refId: finalRefId,
        file: audioFile!,
        fileName: audioFile!.name,
        fileSize: audioFile!.size,
        startTime: enableAudioCrop ? audioStartTime ?? undefined : undefined,
        endTime: enableAudioCrop ? audioEndTime ?? undefined : undefined,
      };

      console.log('DEBUG: audioInput created:', JSON.stringify(audioInput, null, 2));
      const newSegment = createNewSegment(startTime, endTime, audioInput, label);
      console.log('Created new segment:', JSON.stringify(newSegment, null, 2));
      addSegment(newSegment);
      console.log('Segment added to store');
    }

    onClose();
  };

  const duration = endTime - startTime;

  // Check for overlaps if editing an existing segment
  const overlapInfo = React.useMemo(() => {
    if (!editingSegmentId) return null;
    const overlap = getSegmentOverlaps(editingSegmentId, segments);
    if (!overlap) return null;

    const currentSegment = getSegmentById(editingSegmentId);
    if (!currentSegment) return null;

    const overlappingLabels = overlap.overlappingWithIds
      .map(id => getSegmentById(id)?.label || id)
      .filter(Boolean);

    return {
      message: formatOverlapWarning(currentSegment.label || 'This segment', overlappingLabels),
      count: overlappingLabels.length,
    };
  }, [editingSegmentId, segments, getSegmentById]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {editingSegmentId ? 'Edit Segment' : 'Add New Segment'}
        </Typography>
        <IconButton onClick={onClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {/* Overlap Warning */}
        {overlapInfo && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              ⚠️ Segment Overlap Detected
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              {overlapInfo.message}
            </Typography>
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Time Range Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
            ⏱️ Segment Time Range
          </Typography>

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 1 }}>
            <TextField
              label="Start Time (seconds)"
              type="number"
              value={startTime}
              onChange={(e) => setStartTime(Math.max(0, parseFloat(e.target.value) || 0))}
              inputProps={{ min: 0, max: videoDuration, step: 0.1 }}
              size="small"
              fullWidth
            />
            <TextField
              label="End Time (seconds)"
              type="number"
              value={endTime}
              onChange={(e) => setEndTime(Math.min(videoDuration, parseFloat(e.target.value) || 0))}
              inputProps={{ min: 0, max: videoDuration, step: 0.1 }}
              size="small"
              fullWidth
            />
          </Box>

          <Typography variant="caption" color="text.secondary">
            Duration: {formatSegmentTime(duration)} • Video Length: {formatSegmentTime(videoDuration)}
          </Typography>
        </Box>

        {/* Audio Upload Section */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
            🎵 Audio File
          </Typography>

          {(() => {
            const existingAudioFiles = getAllAudioFiles();

            if (existingAudioFiles.length > 0) {
              return (
                <Box>
                  {/* Show info message */}
                  <Alert severity="info" sx={{ mb: 2, py: 0.5 }}>
                    <Typography variant="caption">
                      💡 You can reuse previously uploaded audio files or upload a new one
                    </Typography>
                  </Alert>

                  {/* Radio Group for Selection Mode */}
                  <RadioGroup
                    value={audioSelectionMode}
                    onChange={(e) => {
                      setAudioSelectionMode(e.target.value as 'existing' | 'upload');
                      if (e.target.value === 'upload') {
                        setSelectedAudioRefId(null);
                        setAudioFile(null);
                      }
                    }}
                  >
                    {/* Option 1: Use Existing Audio */}
                    <FormControlLabel
                      value="existing"
                      control={<Radio />}
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Refresh sx={{ fontSize: 18, color: '#10b981' }} />
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            Reuse existing audio file
                          </Typography>
                        </Box>
                      }
                    />

                    {/* Show existing audio files when this mode is selected */}
                    {audioSelectionMode === 'existing' && (
                      <Box sx={{ ml: 4, mt: 1, mb: 2 }}>
                        {existingAudioFiles.map((audio) => (
                          <Paper
                            key={audio.refId}
                            variant="outlined"
                            sx={{
                              p: 1.5,
                              mb: 1,
                              cursor: 'pointer',
                              border: selectedAudioRefId === audio.refId ? '2px solid #f59e0b' : '1px solid',
                              bgcolor: selectedAudioRefId === audio.refId ? 'rgba(245, 158, 11, 0.05)' : 'transparent',
                              '&:hover': { bgcolor: 'action.hover' },
                            }}
                            onClick={() => handleExistingAudioSelect(audio.refId)}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <AudioFile sx={{ color: selectedAudioRefId === audio.refId ? '#f59e0b' : 'action.active' }} />
                              <Box sx={{ flex: 1 }}>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                  {audio.fileName}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {(audio.fileSize / 1024 / 1024).toFixed(2)} MB
                                </Typography>
                              </Box>
                              {selectedAudioRefId === audio.refId && (
                                <CheckCircle sx={{ color: '#f59e0b' }} />
                              )}
                            </Box>
                          </Paper>
                        ))}
                      </Box>
                    )}

                    {/* Option 2: Upload New Audio */}
                    <FormControlLabel
                      value="upload"
                      control={<Radio />}
                      label={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <CloudUpload sx={{ fontSize: 18, color: '#3b82f6' }} />
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            Upload a new audio file
                          </Typography>
                        </Box>
                      }
                    />
                  </RadioGroup>

                  {/* Show upload area when upload mode is selected */}
                  {audioSelectionMode === 'upload' && (
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 2,
                        ml: 4,
                        mt: 1,
                        textAlign: 'center',
                        cursor: 'pointer',
                        '&:hover': { bgcolor: 'action.hover' },
                      }}
                      component="label"
                    >
                      <input
                        type="file"
                        accept=".mp3,.wav,.m4a,.aac"
                        onChange={handleAudioFileChange}
                        style={{ display: 'none' }}
                      />

                      {audioFile ? (
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                          <CheckCircle color="success" />
                          <Typography variant="body2">
                            {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
                          </Typography>
                        </Box>
                      ) : (
                        <Box>
                          <CloudUpload sx={{ fontSize: 40, color: 'action.active', mb: 1 }} />
                          <Typography variant="body2" color="text.secondary">
                            Click to upload audio file
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Supported: MP3, WAV, M4A, AAC • Max 100MB
                          </Typography>
                        </Box>
                      )}
                    </Paper>
                  )}
                </Box>
              );
            } else {
              // No existing audio files - show simple upload
              return (
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    textAlign: 'center',
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                  component="label"
                >
                  <input
                    type="file"
                    accept=".mp3,.wav,.m4a,.aac"
                    onChange={handleAudioFileChange}
                    style={{ display: 'none' }}
                  />

                  {audioFile ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                      <CheckCircle color="success" />
                      <Typography variant="body2">
                        {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
                      </Typography>
                    </Box>
                  ) : (
                    <Box>
                      <CloudUpload sx={{ fontSize: 40, color: 'action.active', mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Click to upload audio file
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Supported: MP3, WAV, M4A, AAC • Max 100MB
                      </Typography>
                    </Box>
                  )}
                </Paper>
              );
            }
          })()}

          {/* Audio Crop Section (Optional) */}
          {audioFile && (
            <Box sx={{ mt: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={enableAudioCrop}
                    onChange={(e) => {
                      setEnableAudioCrop(e.target.checked);
                      if (!e.target.checked) {
                        setAudioStartTime(null);
                        setAudioEndTime(null);
                      }
                    }}
                    sx={{
                      color: '#f59e0b',
                      '&.Mui-checked': {
                        color: '#f59e0b',
                      },
                    }}
                  />
                }
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <ContentCut sx={{ fontSize: 18, color: '#f59e0b' }} />
                    <Typography variant="body2">
                      Crop Audio (Optional)
                    </Typography>
                  </Box>
                }
              />

              <Collapse in={enableAudioCrop}>
                <Box sx={{ mt: 1.5, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                    Specify which part of the audio file to use for lip-sync
                  </Typography>

                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                    <TextField
                      label="Audio Start (seconds)"
                      type="number"
                      value={audioStartTime ?? ''}
                      onChange={(e) => setAudioStartTime(e.target.value ? parseFloat(e.target.value) : null)}
                      inputProps={{ min: 0, step: 0.1 }}
                      size="small"
                      fullWidth
                      placeholder="e.g., 2.5"
                    />
                    <TextField
                      label="Audio End (seconds)"
                      type="number"
                      value={audioEndTime ?? ''}
                      onChange={(e) => setAudioEndTime(e.target.value ? parseFloat(e.target.value) : null)}
                      inputProps={{ min: 0, step: 0.1 }}
                      size="small"
                      fullWidth
                      placeholder="e.g., 12.5"
                    />
                  </Box>

                  {audioStartTime !== null && audioEndTime !== null && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Audio duration: {formatSegmentTime(audioEndTime - audioStartTime)}
                    </Typography>
                  )}
                </Box>
              </Collapse>
            </Box>
          )}
        </Box>

        {/* Optional Label */}
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
            📝 Label (Optional)
          </Typography>
          <TextField
            label="Segment Label"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g., Interview Section"
            size="small"
            fullWidth
          />
          <Typography variant="caption" color="text.secondary">
            Add a label to identify this segment
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          sx={{
            background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #d97706 0%, #b45309 100%)',
            },
          }}
        >
          {editingSegmentId ? 'Update Segment' : 'Add Segment'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default SegmentDialog;

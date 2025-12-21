import { useState, useEffect } from 'react';
import {
  useSegmentsStore,
  createNewSegment,
  validateAudioFile,
} from '../../../../../store/segmentsStore';
import { AudioInput } from '../../../../../types/segments';

interface UseSegmentFormProps {
  open: boolean;
  editingSegmentId: string | null;
  videoDuration: number;
  currentTime: number;
}

export const useSegmentForm = ({
  open,
  editingSegmentId,
  videoDuration,
  currentTime,
}: UseSegmentFormProps) => {
  const { addSegment, updateSegment, getSegmentById, validateSegmentTimes } = useSegmentsStore();

  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(0);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);

  const [enableAudioCrop, setEnableAudioCrop] = useState(false);
  const [audioStartTime, setAudioStartTime] = useState<number | null>(null);
  const [audioEndTime, setAudioEndTime] = useState<number | null>(null);

  // Initialize form when dialog opens
  useEffect(() => {
    if (open) {
      if (editingSegmentId) {
        const segment = getSegmentById(editingSegmentId);
        if (segment) {
          setStartTime(segment.startTime);
          setEndTime(segment.endTime);
          setLabel(segment.label || '');
          setAudioFile(segment.audioInput.file);

          // Check if audio crop times are explicitly set (not null/undefined)
          // Use && (AND) logic: either startTime OR endTime must be explicitly set
          const hasAudioCrop =
            (segment.audioInput.startTime !== null && segment.audioInput.startTime !== undefined) ||
            (segment.audioInput.endTime !== null && segment.audioInput.endTime !== undefined);
          setEnableAudioCrop(hasAudioCrop);
          setAudioStartTime(segment.audioInput.startTime ?? null);
          setAudioEndTime(segment.audioInput.endTime ?? null);
        }
      } else {
        const suggestedStart = Math.floor(currentTime);
        const suggestedEnd = Math.min(suggestedStart + 15, Math.floor(videoDuration));
        setStartTime(suggestedStart);
        setEndTime(suggestedEnd);
        setLabel('');
        setAudioFile(null);
        setEnableAudioCrop(false);
        setAudioStartTime(null);
        setAudioEndTime(null);
      }
      setError(null);
    }
  }, [open, editingSegmentId, currentTime, videoDuration, getSegmentById]);

  const handleAudioFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validation = validateAudioFile(file);
      if (!validation.valid) {
        setError(validation.error || 'Invalid audio file');
        return;
      }
      setAudioFile(file);
      setError(null);
    }
  };

  const handleAudioCropChange = (enabled: boolean) => {
    setEnableAudioCrop(enabled);
    if (!enabled) {
      setAudioStartTime(null);
      setAudioEndTime(null);
    }
  };

  const validateForm = (): boolean => {
    if (!audioFile && !editingSegmentId) {
      setError('Please select an audio file');
      return false;
    }

    const validation = validateSegmentTimes(startTime, endTime, editingSegmentId || undefined);
    if (!validation.valid) {
      setError(validation.error || 'Invalid time range');
      return false;
    }

    if (enableAudioCrop) {
      if (audioStartTime !== null && audioEndTime !== null && audioStartTime >= audioEndTime) {
        setError('Audio start time must be before end time');
        return false;
      }
      if (audioStartTime !== null && audioStartTime < 0) {
        setError('Audio start time cannot be negative');
        return false;
      }
    }

    return true;
  };

  const submitForm = () => {
    if (!validateForm()) return false;

    // When audio crop is explicitly enabled, use user-specified times
    // Otherwise, auto-set audio crop times to match video segment times
    // This ensures the audio portion matches the video segment portion
    // (user provides full audio file corresponding to full video file)
    const audioInput: AudioInput = {
      refId: `audio-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file: audioFile!,
      fileName: audioFile!.name,
      fileSize: audioFile!.size,
      startTime: enableAudioCrop ? (audioStartTime ?? startTime) : startTime,
      endTime: enableAudioCrop ? (audioEndTime ?? endTime) : endTime,
    };

    if (editingSegmentId) {
      const updates: any = { startTime, endTime, label };
      if (audioFile) {
        updates.audioInput = audioInput;
      }
      updateSegment(editingSegmentId, updates);
    } else {
      const newSegment = createNewSegment(startTime, endTime, audioInput, label);
      addSegment(newSegment);
    }

    return true;
  };

  return {
    startTime,
    endTime,
    audioFile,
    label,
    error,
    enableAudioCrop,
    audioStartTime,
    audioEndTime,
    setStartTime,
    setEndTime,
    setLabel,
    handleAudioFileChange,
    handleAudioCropChange,
    setAudioStartTime,
    setAudioEndTime,
    submitForm,
  };
};

/**
 * Video Submission Hook
 *
 * Handles the submission of Pro videos with segments and effects
 * to the backend API for processing.
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEffectsStore } from '../../../../store/effectsStore';
import { useSegmentsStore } from '../../../../store/segmentsStore';
import { API_ENDPOINTS } from '../constants/editorConstants';
import { processVideo, getJobStatus } from '../../../../services/embeddedApi';

export interface UseVideoSubmissionReturn {
  /** Whether submission is in progress */
  isSubmitting: boolean;
  /** Current submission progress message */
  submissionProgress: string;
  /** Handler to submit the video for processing */
  handleSubmit: () => Promise<void>;
}

export interface VideoSubmissionOptions {
  videoFile: File | null;
  videoUrl?: string;
  embeddedMode?: boolean;
  embeddedToken?: string;
  phrazeJobId?: string;
}

/**
 * Custom hook for handling Pro video submission
 *
 * @param options - Video submission options including file, URL, and embedded mode settings
 * @returns Submission state and handler
 */
export const useVideoSubmission = (
  options: VideoSubmissionOptions | File | null
): UseVideoSubmissionReturn => {
  // Handle both old signature (File | null) and new options object
  const normalizedOptions: VideoSubmissionOptions =
    options === null || options instanceof File
      ? { videoFile: options }
      : options;
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionProgress, setSubmissionProgress] = useState('');

  const { effects } = useEffectsStore();
  const { segments } = useSegmentsStore();

  const { videoFile, videoUrl, embeddedMode, embeddedToken, phrazeJobId } = normalizedOptions;

  /**
   * Handles Pro video submission
   */
  const handleSubmit = useCallback(async () => {
    console.log('=== PRO VIDEO SUBMIT HANDLER ===');
    console.log('Segments count:', segments.length);
    console.log('Segments data:', segments);
    console.log('Effects count:', effects.length);
    console.log('Video file:', videoFile);
    console.log('Video URL:', videoUrl);
    console.log('Embedded mode:', embeddedMode);

    // In embedded mode, we have videoUrl instead of videoFile
    if (!videoFile && !videoUrl) {
      console.error('No video file or URL available for submission');
      alert('No video available for processing');
      return;
    }

    if (segments.length === 0) {
      console.error('No segments configured - segments array is empty!');
      alert('Please add at least one segment for Pro video processing');
      return;
    }

    // Handle embedded mode submission via phraze.so API
    if (embeddedMode && embeddedToken) {
      await handleEmbeddedSubmit();
      return;
    }

    // For non-embedded mode, videoFile is required
    if (!videoFile) {
      console.error('No video file available for non-embedded submission');
      alert('No video file available for processing');
      return;
    }

    setIsSubmitting(true);
    setSubmissionProgress('Preparing Pro video for processing...');

    try {
      console.log('Submitting Pro video with', segments.length, 'segments');

      const formData = new FormData();
      formData.append('file', videoFile);
      formData.append('display_name', `Pro Video - ${videoFile.name}`);

      // Add only UNIQUE audio files (deduplicate by refId)
      // This is important when the same audio file is reused across multiple segments
      const uniqueAudioMap = new Map<string, File>();
      segments.forEach(seg => {
        if (seg.audioInput.file && !uniqueAudioMap.has(seg.audioInput.refId)) {
          uniqueAudioMap.set(seg.audioInput.refId, seg.audioInput.file);
        }
      });

      // Append unique audio files in the order their refIds appear
      uniqueAudioMap.forEach((file) => {
        formData.append('audio_files', file);
      });

      console.log('Including', uniqueAudioMap.size, 'unique audio files for', segments.length, 'segments');
      console.log('Unique audio refIds:', Array.from(uniqueAudioMap.keys()));
      console.log('RAW SEGMENTS FROM STORE:', JSON.stringify(segments, null, 2));

      // Build segments data for API
      const segmentsData = segments.map(seg => {
        // Per Sync.so docs: audioInput times are REQUIRED when multiple segments share the same audio
        // This tells Sync.so which portion of the audio file to use for each segment
        const audioInput: {
          refId: string;
          startTime?: number;
          endTime?: number;
        } = {
          refId: seg.audioInput.refId,
        };

        // ALWAYS include audio crop times if they are set in the segment
        // This is critical when multiple segments use the same audio file
        if (seg.audioInput.startTime !== null && seg.audioInput.startTime !== undefined) {
          audioInput.startTime = seg.audioInput.startTime;
        }
        if (seg.audioInput.endTime !== null && seg.audioInput.endTime !== undefined) {
          audioInput.endTime = seg.audioInput.endTime;
        }

        return {
          startTime: seg.startTime,
          endTime: seg.endTime,
          audioInput,
        };
      });

      formData.append('segments_data', JSON.stringify(segmentsData));
      console.log('Segments configuration:', JSON.stringify(segmentsData, null, 2));

      // Include effects data if any
      if (effects.length > 0) {
        const effectsData = effects.map(effect => ({
          type: effect.type,
          startTime: effect.startTime,
          endTime: effect.endTime,
          region: effect.region,
        }));
        formData.append('effects', JSON.stringify(effectsData));
        console.log('Including', effects.length, 'effects');
      }

      setSubmissionProgress('Uploading video and audio files for Pro processing...');

      // Get auth token
      const token = localStorage.getItem('access_token');
      if (!token) {
        console.error('No authentication token found');
        setIsSubmitting(false);
        setSubmissionProgress('');
        alert('Not authenticated. Please refresh the page and try again.');
        return;
      }

      const headers: Record<string, string> = {
        'Authorization': `Bearer ${token}`,
      };

      console.log('Sending request to Pro API endpoint');

      const response = await fetch(API_ENDPOINTS.PRO_SYNC_PROCESS, {
        method: 'POST',
        headers,
        body: formData,
      });

      console.log('Response status:', response.status);
      const result = await response.json();

      if (response.ok) {
        console.log('Pro video submitted successfully:', result);
        setSubmissionProgress('Pro job created successfully! Redirecting to jobs page...');

        // Navigate to jobs page
        setTimeout(() => {
          navigate('/jobs');
        }, 1500);
      } else {
        console.error('Submission failed:', result);
        setSubmissionProgress('');
        setIsSubmitting(false);

        if (response.status === 403) {
          alert('Insufficient permissions. Pro tier subscription required.');
        } else {
          alert(`Submission failed: ${result.detail || result.message || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Error submitting Pro video:', error);
      setSubmissionProgress('');
      setIsSubmitting(false);
      alert('Error submitting video. Please try again.');
    }
  }, [videoFile, videoUrl, embeddedMode, embeddedToken, segments, effects, navigate]);

  /**
   * Poll for job status until completion or failure
   */
  const pollJobStatus = useCallback(async (jobId: string, token: string): Promise<void> => {
    const MAX_POLLS = 120; // 10 minutes at 5 second intervals
    const POLL_INTERVAL = 5000; // 5 seconds

    for (let i = 0; i < MAX_POLLS; i++) {
      try {
        const status = await getJobStatus(jobId, token);
        console.log(`Job status poll ${i + 1}:`, status);

        if (status.status === 'completed') {
          setSubmissionProgress('Processing completed successfully!');
          setIsSubmitting(false);

          // Show success message with output URL
          if (status.output_url) {
            alert(`Processing completed!\n\nOutput video: ${status.output_url}`);
          } else {
            alert('Processing completed successfully!');
          }
          return;
        }

        if (status.status === 'failed') {
          setSubmissionProgress('');
          setIsSubmitting(false);
          alert(`Processing failed: ${status.error_message || 'Unknown error'}`);
          return;
        }

        // Update progress message
        const progressMsg = status.message || `Processing... ${status.progress || 0}%`;
        setSubmissionProgress(progressMsg);

        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));

      } catch (error) {
        console.error('Error polling job status:', error);
        // Continue polling despite errors
        await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
      }
    }

    // Timeout after max polls
    setSubmissionProgress('');
    setIsSubmitting(false);
    alert('Processing is taking longer than expected. Check the jobs page for status.');
  }, []);

  /**
   * Handles embedded mode submission via phraze.so API
   */
  const handleEmbeddedSubmit = useCallback(async () => {
    console.log('=== EMBEDDED MODE SUBMIT ===');
    console.log('Token:', embeddedToken ? 'present' : 'missing');
    console.log('Phraze Job ID:', phrazeJobId);

    if (!embeddedToken) {
      alert('Authentication token missing. Please try again.');
      return;
    }

    setIsSubmitting(true);
    setSubmissionProgress('Preparing embedded video for processing...');

    try {
      // Build segments data for API
      const segmentsData = segments.map(seg => ({
        startTime: seg.startTime,
        endTime: seg.endTime,
        audioInput: {
          refId: seg.audioInput.refId,
          startTime: seg.audioInput.startTime,
          endTime: seg.audioInput.endTime,
        },
      }));

      console.log('Submitting to embedded API with segments:', segmentsData);

      setSubmissionProgress('Submitting to phraze.so processing...');

      const response = await processVideo(embeddedToken, {
        processing_type: 'lip_sync',
        segments: segmentsData,
      });

      console.log('Embedded submission response:', response);
      setSubmissionProgress('Job submitted! Processing...');

      // Poll for job status until completion
      await pollJobStatus(response.job_id, embeddedToken);

    } catch (error: unknown) {
      console.error('Error submitting embedded video:', error);
      setSubmissionProgress('');
      setIsSubmitting(false);

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      alert(`Error submitting video: ${errorMessage}`);
    }
  }, [embeddedToken, phrazeJobId, segments, pollJobStatus]);

  return {
    isSubmitting,
    submissionProgress,
    handleSubmit,
  };
};

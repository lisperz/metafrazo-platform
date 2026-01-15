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
import { processVideo, getJobStatus, uploadAudioFile, redirectToPhraze } from '../../../../services/embeddedApi';

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
  callbackUrl?: string | null;
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

  const { effects, videoMetadata } = useEffectsStore();
  const { segments } = useSegmentsStore();

  const { videoFile, videoUrl, embeddedMode, embeddedToken, phrazeJobId, callbackUrl } = normalizedOptions;

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

    // In embedded mode, allow either segments OR effects (erasure areas)
    const hasErasureEffects = effects.filter(e => e.type === 'erasure').length > 0;
    if (embeddedMode && embeddedToken) {
      if (segments.length === 0 && !hasErasureEffects) {
        console.error('No segments or erasure areas configured');
        alert('Please add at least one segment or erasure area for processing');
        return;
      }
      await handleEmbeddedSubmit();
      return;
    }

    // For non-embedded mode, segments are required
    if (segments.length === 0) {
      console.error('No segments configured - segments array is empty!');
      alert('Please add at least one segment for Pro video processing');
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
      // CRITICAL: Audio crop times MUST match video segment times for proper sync
      // This prevents "remap" issues where output video duration doesn't match input
      const segmentsData = segments.map(seg => {
        // ALWAYS force audio crop times to match video segment times
        // This ensures the audio portion exactly corresponds to the video segment
        const audioStartTime = seg.startTime;
        const audioEndTime = seg.endTime;

        console.log(`Segment ${seg.id}: video=${seg.startTime}-${seg.endTime}, audio=${audioStartTime}-${audioEndTime} (forced match)`);

        const segmentData: {
          startTime: number;
          endTime: number;
          audioInput: { refId: string; startTime: number; endTime: number };
          speakerBox?: { x1: number; y1: number; x2: number; y2: number; method: string };
        } = {
          startTime: seg.startTime,
          endTime: seg.endTime,
          audioInput: {
            refId: seg.audioInput.refId,
            startTime: audioStartTime,
            endTime: audioEndTime,
          },
        };

        // Use per-segment speaker box if set
        if (seg.speakerBox) {
          console.log(`Segment ${seg.id}: using per-segment speakerBox=${JSON.stringify(seg.speakerBox)}`);
          segmentData.speakerBox = {
            x1: seg.speakerBox.x1,
            y1: seg.speakerBox.y1,
            x2: seg.speakerBox.x2,
            y2: seg.speakerBox.y2,
            method: seg.speakerBox.method,
          };
        }

        return segmentData;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoFile, videoUrl, embeddedMode, embeddedToken, segments, effects, navigate]);

  /**
   * Poll for job status until completion or failure
   * Note: For combined processing (lip-sync + text removal), this can take 20+ minutes
   */
  const pollJobStatus = useCallback(async (jobId: string, token: string, cbUrl?: string | null): Promise<void> => {
    const MAX_POLLS = 360; // 30 minutes at 5 second intervals (for combined processing)
    const POLL_INTERVAL = 5000; // 5 seconds

    for (let i = 0; i < MAX_POLLS; i++) {
      try {
        const status = await getJobStatus(jobId, token);
        console.log(`Job status poll ${i + 1}:`, status);

        if (status.status === 'completed') {
          setSubmissionProgress('Processing completed! Redirecting to jobs page...');
          setIsSubmitting(false);

          // Redirect back to jobs page after short delay
          setTimeout(() => {
            redirectToPhraze({
              jobSubmitted: true,
              callbackUrl: cbUrl,
            });
          }, 1500);
          return;
        }

        if (status.status === 'failed') {
          setSubmissionProgress('');
          setIsSubmitting(false);
          alert(`Processing failed: ${status.error_message || 'Unknown error'}`);
          // Redirect back to jobs page on failure too
          setTimeout(() => {
            redirectToPhraze('PROCESSING_FAILED', cbUrl);
          }, 1500);
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

    // Timeout after max polls - job continues in background, redirect to jobs page
    setSubmissionProgress('Processing continues in background. Redirecting...');
    setIsSubmitting(false);
    setTimeout(() => {
      redirectToPhraze({
        jobSubmitted: true,
        callbackUrl: cbUrl,
      });
    }, 1500);
  }, []);

  /**
   * Handles embedded mode submission via phraze.so API
   */
  const handleEmbeddedSubmit = useCallback(async () => {
    console.log('=== EMBEDDED MODE SUBMIT ===');
    console.log('Token:', embeddedToken ? 'present' : 'missing');
    console.log('Phraze Job ID:', phrazeJobId);
    console.log('Segments:', segments);

    if (!embeddedToken) {
      alert('Authentication token missing. Please try again.');
      return;
    }

    setIsSubmitting(true);
    setSubmissionProgress('Preparing embedded video for processing...');

    try {
      // Step 1: Upload unique audio files to S3 and get URLs
      setSubmissionProgress('Uploading audio files...');

      // Collect unique audio files by refId
      const uniqueAudioFiles = new Map<string, File>();
      segments.forEach(seg => {
        if (seg.audioInput.file && !uniqueAudioFiles.has(seg.audioInput.refId)) {
          uniqueAudioFiles.set(seg.audioInput.refId, seg.audioInput.file);
        }
      });

      console.log('Unique audio files to upload:', uniqueAudioFiles.size);

      // Upload each audio file and build refId -> URL mapping
      const audioUrlMap = new Map<string, string>();
      const audioEntries = Array.from(uniqueAudioFiles.entries());

      for (let i = 0; i < audioEntries.length; i++) {
        const [refId, file] = audioEntries[i];
        console.log(`Uploading audio: ${refId} (${file.name})`);
        setSubmissionProgress(`Uploading audio: ${file.name}...`);

        try {
          const uploadResult = await uploadAudioFile(embeddedToken, file, refId);
          audioUrlMap.set(refId, uploadResult.url);
          console.log(`Uploaded ${refId}: ${uploadResult.url}`);
        } catch (uploadError) {
          console.error(`Failed to upload audio ${refId}:`, uploadError);
          throw new Error(`Failed to upload audio file: ${file.name}`);
        }
      }

      // Step 2: Build segments data with audio URLs
      // CRITICAL: Audio crop times MUST match video segment times for proper sync
      // This prevents "remap" issues where output video duration doesn't match input
      const segmentsData = segments.map(seg => {
        const audioUrl = audioUrlMap.get(seg.audioInput.refId);
        if (!audioUrl) {
          throw new Error(`No audio URL for segment ${seg.id}`);
        }

        // ALWAYS force audio crop times to match video segment times
        // This ensures the audio portion exactly corresponds to the video segment
        const audioStartTime = seg.startTime;
        const audioEndTime = seg.endTime;

        console.log(`Segment ${seg.id}: video=${seg.startTime}-${seg.endTime}, audio=${audioStartTime}-${audioEndTime} (forced match)`);

        const segmentData: {
          startTime: number;
          endTime: number;
          audioInput: { refId: string; url: string; startTime: number; endTime: number };
          speakerBox?: { x1: number; y1: number; x2: number; y2: number; method: string };
        } = {
          startTime: seg.startTime,
          endTime: seg.endTime,
          audioInput: {
            refId: seg.audioInput.refId,
            url: audioUrl,
            startTime: audioStartTime,
            endTime: audioEndTime,
          },
        };

        // Use per-segment speaker box if set
        if (seg.speakerBox) {
          console.log(`Segment ${seg.id}: using per-segment speakerBox=${JSON.stringify(seg.speakerBox)}`);
          segmentData.speakerBox = {
            x1: seg.speakerBox.x1,
            y1: seg.speakerBox.y1,
            x2: seg.speakerBox.x2,
            y2: seg.speakerBox.y2,
            method: seg.speakerBox.method,
          };
        }

        return segmentData;
      });

      console.log('Submitting to embedded API with segments:', segmentsData);

      // Build effects data from effectsStore (erasure/protection areas)
      const effectsData = effects.map(effect => ({
        type: effect.type,
        startTime: effect.startTime,
        endTime: effect.endTime,
        region: effect.region,
      }));

      // Filter to only erasure effects for text removal
      const erasureEffects = effectsData.filter(e => e.type === 'erasure');
      const hasSegments = segmentsData.length > 0;
      const hasErasureEffects = erasureEffects.length > 0;

      // Determine processing type based on what's configured
      let processingType: 'lip_sync' | 'text_removal' | 'both' = 'lip_sync';
      if (hasSegments && hasErasureEffects) {
        processingType = 'both';
      } else if (hasErasureEffects && !hasSegments) {
        processingType = 'text_removal';
      }

      console.log('Processing type:', processingType);
      console.log('Erasure effects:', erasureEffects);
      console.log('Video metadata:', videoMetadata);

      setSubmissionProgress('Submitting to phraze.so processing...');

      const response = await processVideo(embeddedToken, {
        processing_type: processingType,
        segments: hasSegments ? segmentsData : undefined,
        effects: hasErasureEffects ? erasureEffects : undefined,
        video_metadata: videoMetadata ? {
          fps: videoMetadata.fps,
          total_frames: videoMetadata.totalFrames,
          width: videoMetadata.width,
          height: videoMetadata.height,
        } : undefined,
      });

      console.log('Embedded submission response:', response);
      setSubmissionProgress('Job submitted! Redirecting to jobs page...');

      // Redirect immediately after job is submitted - don't wait for completion
      // User can track job status on the jobs page
      // Include jobSubmitted flag so Phraze.so can update status to "processing"
      setTimeout(() => {
        redirectToPhraze({
          jobSubmitted: true,
          phrazeJobId: phrazeJobId,
          callbackUrl: callbackUrl,
        });
      }, 1500);

    } catch (error: unknown) {
      console.error('Error submitting embedded video:', error);
      setSubmissionProgress('');
      setIsSubmitting(false);

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      alert(`Processing failed: ${errorMessage}`);
    }
  }, [embeddedToken, phrazeJobId, segments, effects, callbackUrl, videoMetadata]);

  return {
    isSubmitting,
    submissionProgress,
    handleSubmit,
  };
};

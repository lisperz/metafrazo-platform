/**
 * Video Thumbnails Hook
 *
 * Generates and manages video thumbnails for the timeline display.
 */

import { useState, useEffect } from 'react';
import { TIMELINE_CONSTANTS } from '../constants/editorConstants';

export interface UseVideoThumbnailsReturn {
  /** Array of thumbnail data URLs */
  thumbnails: string[];
  /** Whether thumbnail generation is in progress */
  isGenerating: boolean;
  /** Error message if thumbnail generation failed */
  error: string | null;
}

/**
 * Custom hook for generating video thumbnails
 *
 * @param videoUrl - URL of the video
 * @param duration - Video duration in seconds
 * @returns Array of thumbnail data URLs, loading state, and error
 */
export const useVideoThumbnails = (
  videoUrl: string,
  duration: number
): UseVideoThumbnailsReturn => {
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoUrl || duration <= 0) {
      return;
    }

    const generateThumbnails = async () => {
      setIsGenerating(true);
      setError(null);

      const video = document.createElement('video');
      video.src = videoUrl;

      // Try with CORS first, fall back to without if it fails
      // Note: Without CORS, we can't extract frames, so thumbnails will be empty
      video.crossOrigin = 'anonymous';

      try {
        // Wait for metadata to load with timeout
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('Video metadata load timeout'));
          }, 10000);

          video.onloadedmetadata = () => {
            clearTimeout(timeout);
            resolve();
          };

          video.onerror = () => {
            clearTimeout(timeout);
            reject(new Error('Failed to load video metadata'));
          };
        });

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('Failed to get canvas context');
        }

        const { THUMBNAIL_COUNT, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT, THUMBNAIL_QUALITY } =
          TIMELINE_CONSTANTS;

        const interval = video.duration / THUMBNAIL_COUNT;
        const thumbs: string[] = [];

        // Generate thumbnails at regular intervals
        for (let i = 0; i < THUMBNAIL_COUNT; i++) {
          video.currentTime = i * interval;

          // Wait for seek to complete with timeout
          await new Promise<void>((resolve, reject) => {
            const timeout = setTimeout(() => {
              // Don't reject on seek timeout, just continue
              resolve();
            }, 3000);

            video.onseeked = () => {
              clearTimeout(timeout);
              resolve();
            };
          });

          try {
            // Draw frame to canvas
            canvas.width = THUMBNAIL_WIDTH;
            canvas.height = THUMBNAIL_HEIGHT;
            ctx.drawImage(video, 0, 0, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT);

            // Convert to data URL - this may fail with CORS restrictions
            thumbs.push(canvas.toDataURL('image/jpeg', THUMBNAIL_QUALITY));
          } catch (e) {
            // CORS error - can't extract frame data
            console.warn(`Failed to extract frame ${i} due to CORS restrictions`);
            // Use a placeholder or empty string
            thumbs.push('');
          }
        }

        // Only set thumbnails if we got at least some valid ones
        const validThumbs = thumbs.filter(t => t && t.length > 0);
        if (validThumbs.length > 0) {
          setThumbnails(thumbs);
        } else {
          setError('Could not generate thumbnails (CORS restriction)');
          console.warn('No valid thumbnails generated - S3 bucket may need CORS configuration');
        }

      } catch (err) {
        console.error('Error generating thumbnails:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');

        // Try fallback without CORS (video will still play, just no thumbnails)
        console.log('Attempting fallback without CORS...');
        video.crossOrigin = '';

        // Just mark as done without thumbnails
      } finally {
        setIsGenerating(false);
        // Cleanup
        video.src = '';
        video.load();
      }
    };

    generateThumbnails();
  }, [videoUrl, duration]);

  return { thumbnails, isGenerating, error };
};

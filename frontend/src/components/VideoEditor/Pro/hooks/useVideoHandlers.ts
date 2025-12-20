/**
 * Video Handlers Hook
 * Manages video player interactions, thumbnails, and playback controls
 */

import { useState, useEffect, useRef, RefObject } from 'react';
import ReactPlayer from 'react-player';
import { useEffectsStore } from '../../../../store/effectsStore';

export interface VideoHandlers {
  thumbnails: string[];
  videoBounds: { x: number; y: number; width: number; height: number } | null;
  isVideoReady: boolean;
  isMuted: boolean;
  handleReady: () => void;
  handleProgress: (state: any) => void;
  handleDuration: (dur: number) => void;
  handlePlayPause: () => void;
  handleSeek: (time: number) => void;
  handleVolumeToggle: () => void;
}

export const useVideoHandlers = (
  playerRef: RefObject<ReactPlayer>,
  videoContainerRef: RefObject<HTMLDivElement>,
  videoUrl: string,
  duration: number
): VideoHandlers => {
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const [videoBounds, setVideoBounds] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);
  const [isMuted, setIsMuted] = useState(false);

  const {
    setCurrentTime: setStoreTime,
    setDuration: setStoreDuration,
    setIsPlaying: setStoreIsPlaying,
    isPlaying,
  } = useEffectsStore();

  // Calculate actual video display bounds within the container
  const calculateVideoBounds = (): {
    x: number;
    y: number;
    width: number;
    height: number;
  } | null => {
    if (!playerRef.current || !videoContainerRef.current) return null;

    const internalPlayer = playerRef.current.getInternalPlayer();
    if (
      !internalPlayer ||
      !internalPlayer.videoWidth ||
      !internalPlayer.videoHeight
    )
      return null;

    const container = videoContainerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    const videoAspectRatio =
      internalPlayer.videoWidth / internalPlayer.videoHeight;
    const containerAspectRatio = containerWidth / containerHeight;

    let videoDisplayWidth: number;
    let videoDisplayHeight: number;
    let videoX: number;
    let videoY: number;

    if (videoAspectRatio > containerAspectRatio) {
      // Video is wider - fit to width, letterbox top/bottom
      videoDisplayWidth = containerWidth;
      videoDisplayHeight = containerWidth / videoAspectRatio;
      videoX = 0;
      videoY = (containerHeight - videoDisplayHeight) / 2;
    } else {
      // Video is taller - fit to height, letterbox left/right
      videoDisplayHeight = containerHeight;
      videoDisplayWidth = containerHeight * videoAspectRatio;
      videoX = (containerWidth - videoDisplayWidth) / 2;
      videoY = 0;
    }

    return {
      x: videoX,
      y: videoY,
      width: videoDisplayWidth,
      height: videoDisplayHeight,
    };
  };

  // Generate video thumbnails
  const generateThumbnails = async () => {
    console.log('Starting thumbnail generation for:', videoUrl);
    const video = document.createElement('video');
    video.src = videoUrl;
    video.crossOrigin = 'anonymous';

    try {
      // Wait for metadata with timeout
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Video metadata load timeout'));
        }, 15000);

        video.onloadedmetadata = () => {
          clearTimeout(timeout);
          resolve();
        };

        video.onerror = () => {
          clearTimeout(timeout);
          reject(new Error('Failed to load video'));
        };
      });

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        console.error('Failed to get canvas context');
        return;
      }

      const frameCount = 30; // Number of thumbnails to generate
      const interval = video.duration / frameCount;
      const thumbs: string[] = [];

      for (let i = 0; i < frameCount; i++) {
        video.currentTime = i * interval;

        // Wait for seek with timeout
        await new Promise<void>((resolve) => {
          const timeout = setTimeout(() => {
            resolve(); // Continue even if seek times out
          }, 3000);

          video.onseeked = () => {
            clearTimeout(timeout);
            resolve();
          };
        });

        try {
          canvas.width = 120;
          canvas.height = 68;
          ctx.drawImage(video, 0, 0, 120, 68);
          thumbs.push(canvas.toDataURL('image/jpeg', 0.7));
        } catch (e) {
          // CORS error - can't extract frame data
          console.warn(`Failed to extract frame ${i} due to CORS restrictions`);
          thumbs.push(''); // Use empty string as placeholder
        }
      }

      // Only set thumbnails if we got at least some valid ones
      const validThumbs = thumbs.filter(t => t && t.length > 0);
      if (validThumbs.length > 0) {
        setThumbnails(thumbs);
        console.log(`Generated ${validThumbs.length} valid thumbnails`);
      } else {
        console.warn('No valid thumbnails generated - S3 bucket may need CORS configuration');
      }
    } catch (error) {
      console.error('Error generating thumbnails:', error);
    } finally {
      // Cleanup
      video.src = '';
      video.load();
    }
  };

  // Generate thumbnails when video is ready
  useEffect(() => {
    if (videoUrl && playerRef.current && duration > 0) {
      generateThumbnails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoUrl, duration]);

  // Recalculate video bounds on container resize
  useEffect(() => {
    const handleResize = () => {
      if (isVideoReady) {
        setTimeout(() => {
          const bounds = calculateVideoBounds();
          if (bounds) {
            setVideoBounds(bounds);
          }
        }, 100);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isVideoReady]);

  // Handler: Video ready
  const handleReady = () => {
    console.log('Video ready');
    setIsVideoReady(true);

    // Calculate video bounds
    setTimeout(() => {
      const bounds = calculateVideoBounds();
      if (bounds) {
        setVideoBounds(bounds);
      }
    }, 100); // Small delay to ensure video dimensions are available

    // Get initial time from the video player
    if (playerRef.current) {
      const internalPlayer = playerRef.current.getInternalPlayer();
      if (internalPlayer && internalPlayer.currentTime !== undefined) {
        const initialTime = internalPlayer.currentTime || 0;
        setStoreTime(initialTime);
      }
    }
  };

  // Handler: Video progress update
  const handleProgress = (state: any) => {
    const preciseTime = state.playedSeconds || 0;
    setStoreTime(preciseTime);
  };

  // Handler: Video duration loaded
  const handleDuration = (dur: number) => {
    setStoreDuration(dur);
  };

  // Handler: Play/Pause toggle
  const handlePlayPause = () => {
    setStoreIsPlaying(!isPlaying);
  };

  // Handler: Seek to specific time
  const handleSeek = (time: number) => {
    if (playerRef.current && duration > 0) {
      const clampedTime = Math.max(0, Math.min(time, duration));
      setStoreTime(clampedTime);

      const seekPercentage = clampedTime / duration;
      playerRef.current.seekTo(seekPercentage, 'fraction');
    }
  };

  // Handler: Volume mute toggle
  const handleVolumeToggle = () => {
    setIsMuted(!isMuted);
  };

  return {
    thumbnails,
    videoBounds,
    isVideoReady,
    isMuted,
    handleReady,
    handleProgress,
    handleDuration,
    handlePlayPause,
    handleSeek,
    handleVolumeToggle,
  };
};

/**
 * Video Player Hook
 *
 * Manages video player state, playback controls, and timeline synchronization.
 */

import { useState, useRef, useCallback } from 'react';
import ReactPlayer from 'react-player';
import { useEffectsStore, VideoMetadata } from '../../../../store/effectsStore';
import { clampTime } from '../../../../utils/timelineUtils';

export interface UseVideoPlayerReturn {
  // Refs
  playerRef: React.RefObject<ReactPlayer | null>;
  videoContainerRef: React.RefObject<HTMLDivElement | null>;

  // State
  isVideoReady: boolean;
  isMuted: boolean;
  currentTime: number;
  duration: number;
  isPlaying: boolean;

  // Handlers
  handleReady: () => void;
  handleProgress: (state: { playedSeconds: number }) => void;
  handleDuration: (duration: number) => void;
  handlePlayPause: () => void;
  handleVolumeToggle: () => void;
  handleSeek: (time: number) => void;
}

/**
 * Custom hook for managing video player functionality
 *
 * @returns Video player state and control functions
 */
export const useVideoPlayer = (): UseVideoPlayerReturn => {
  // Refs
  const playerRef = useRef<ReactPlayer | null>(null);
  const videoContainerRef = useRef<HTMLDivElement | null>(null);

  // Local state
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  // Store state and actions
  const {
    currentTime,
    duration,
    isPlaying,
    setCurrentTime: setStoreTime,
    setDuration: setStoreDuration,
    setIsPlaying: setStoreIsPlaying,
    setVideoMetadata,
  } = useEffectsStore();

  /**
   * Handles video ready event
   * Initializes video state and retrieves initial time
   */
  const handleReady = useCallback(() => {
    console.log('Video ready');
    setIsVideoReady(true);

    // Get initial time from the video player
    if (playerRef.current) {
      const internalPlayer = playerRef.current.getInternalPlayer() as HTMLVideoElement;
      if (internalPlayer && internalPlayer.currentTime !== undefined) {
        const initialTime = internalPlayer.currentTime || 0;
        setStoreTime(initialTime);
      }

      // Capture video metadata for speaker selection feature
      if (internalPlayer && internalPlayer.videoWidth && internalPlayer.videoHeight) {
        const videoDuration = internalPlayer.duration || 0;
        // Estimate fps (most videos are 30fps, but we can't get exact fps from HTML5 video)
        const estimatedFps = 30;
        const totalFrames = Math.ceil(videoDuration * estimatedFps);

        const metadata: VideoMetadata = {
          width: internalPlayer.videoWidth,
          height: internalPlayer.videoHeight,
          fps: estimatedFps,
          totalFrames: totalFrames,
        };

        console.log('Video metadata captured:', metadata);
        setVideoMetadata(metadata);
      }
    }
  }, [setStoreTime, setVideoMetadata]);

  /**
   * Handles video progress updates
   * Updates current time in store with high precision
   */
  const handleProgress = useCallback((state: { playedSeconds: number }) => {
    const preciseTime = state.playedSeconds || 0;
    setStoreTime(preciseTime);
  }, [setStoreTime]);

  /**
   * Handles duration update
   */
  const handleDuration = useCallback((dur: number) => {
    setStoreDuration(dur);
  }, [setStoreDuration]);

  /**
   * Toggles play/pause state
   */
  const handlePlayPause = useCallback(() => {
    setStoreIsPlaying(!isPlaying);
  }, [isPlaying, setStoreIsPlaying]);

  /**
   * Toggles mute state
   */
  const handleVolumeToggle = useCallback(() => {
    setIsMuted(prev => !prev);
  }, []);

  /**
   * Seeks to a specific time in the video
   *
   * @param time - Target time in seconds
   */
  const handleSeek = useCallback((time: number) => {
    if (playerRef.current && duration > 0) {
      // Clamp time to valid range
      const clampedTime = clampTime(time, duration);
      setStoreTime(clampedTime);

      // Seek with high precision using fraction
      const seekPercentage = clampedTime / duration;
      playerRef.current.seekTo(seekPercentage, 'fraction');
    }
  }, [duration, setStoreTime]);

  return {
    // Refs
    playerRef,
    videoContainerRef,

    // State
    isVideoReady,
    isMuted,
    currentTime,
    duration,
    isPlaying,

    // Handlers
    handleReady,
    handleProgress,
    handleDuration,
    handlePlayPause,
    handleVolumeToggle,
    handleSeek,
  };
};

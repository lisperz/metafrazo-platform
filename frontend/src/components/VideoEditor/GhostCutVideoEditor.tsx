import React, { useState, useRef, useEffect } from 'react';
import { Rnd } from 'react-rnd';
import ReactPlayer from 'react-player';
import {
  Box,
  Typography,
  Button,
  IconButton,
  Slider,
  CircularProgress,
} from '@mui/material';
import {
  ArrowBack,
  PlayArrow,
  Pause,
  Delete,
  Close,
  Undo,
  Redo,
  VolumeUp,
  VolumeOff,
} from '@mui/icons-material';
import { useEffectsStore, VideoEffect } from '../../store/effectsStore';
import { useNavigate } from 'react-router-dom';
import { calculateProgressPercentage, formatTime as formatTimeUtil, clampTime, handleTimelineInteraction } from '../../utils/timelineUtils';
import { API_ENDPOINTS } from './GhostCut/constants/editorConstants';

interface GhostCutVideoEditorProps {
  videoUrl: string;
  videoFile: File | null;
  onBack?: () => void;
}

interface TimelineEffect {
  id: string;
  type: 'erasure' | 'protection' | 'text';
  startFrame: number;
  endFrame: number;
  color: string;
  label: string;
}

const GhostCutVideoEditor: React.FC<GhostCutVideoEditorProps> = ({ 
  videoUrl, 
  videoFile, 
  onBack 
}) => {
  const navigate = useNavigate();
  const playerRef = useRef<ReactPlayer>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const frameStripRef = useRef<HTMLDivElement>(null);
  
  // Local component state
  const [isVideoReady, setIsVideoReady] = useState(false);
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState<string | null>(null);
  const [timelineEffects, setTimelineEffects] = useState<TimelineEffect[]>([]);
  const [videoBounds, setVideoBounds] = useState<{x: number, y: number, width: number, height: number} | null>(null);
  
  // Drawing state
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [currentRect, setCurrentRect] = useState<any>(null);
  const [selectedType, setSelectedType] = useState<'erasure' | 'protection' | 'text'>('erasure');
  
  // Edit mode state for existing effects
  const [editingEffectId, setEditingEffectId] = useState<string | null>(null);
  
  // Timeline interaction state
  const [isDraggingTimeline, setIsDraggingTimeline] = useState(false);
  
  // Audio state
  const [isMuted, setIsMuted] = useState(false);
  
  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionProgress, setSubmissionProgress] = useState('');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  
  // Get all state and actions from centralized store
  const {
    effects,
    addEffect,
    updateEffect,
    deleteEffect,
    currentTime,
    duration,
    isPlaying,
    zoomLevel: timelineZoom,
    setCurrentTime: setStoreTime,
    setDuration: setStoreDuration,
    setIsPlaying: setStoreIsPlaying,
    setZoomLevel: setTimelineZoom,
    undo,
    redo,
    canUndo,
    canRedo,
  } = useEffectsStore();

  // Debug log for audio file state
  useEffect(() => {
    console.log('AudioFile state updated:', audioFile);
  }, [audioFile]);

  // Synchronize timeline effects with main effects store
  useEffect(() => {
    const syncedTimelineEffects: TimelineEffect[] = effects.map(effect => {
      const colors = {
        erasure: '#5B8FF9',
        protection: '#5AD8A6',
        text: '#5D7092',
      };
      
      const labels = {
        erasure: 'Erasure Area',
        protection: 'Protection Area',
        text: 'Erase Text',
      };

      return {
        id: effect.id,
        type: effect.type,
        // Use precise percentage calculation without rounding
        startFrame: (effect.startTime / duration) * 100,
        endFrame: (effect.endTime / duration) * 100,
        color: colors[effect.type],
        label: labels[effect.type],
      };
    });


    setTimelineEffects(syncedTimelineEffects);
  }, [effects, duration]); // Sync whenever effects or duration changes

  // Keyboard shortcuts for undo/redo
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey)) {
        if (event.key === 'z' && !event.shiftKey) {
          event.preventDefault();
          if (canUndo()) {
            undo();
          }
        } else if ((event.key === 'y') || (event.key === 'z' && event.shiftKey)) {
          event.preventDefault();
          if (canRedo()) {
            redo();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, canUndo, canRedo]);

  // Auto-login function to ensure user is authenticated
  useEffect(() => {
    const autoLogin = async () => {
      // Check if we already have a valid token
      const existingToken = localStorage.getItem('access_token');
      if (existingToken) {
        // Try to verify the token by making a test request
        try {
          const response = await fetch(API_ENDPOINTS.AUTH_ME, {
            headers: {
              'Authorization': `Bearer ${existingToken}`
            }
          });
          if (response.ok) {
            console.log('Already authenticated');
            return; // Token is valid, no need to login
          }
        } catch (error) {
          console.log('Existing token invalid, logging in...');
        }
      }

      // Auto-login with demo account
      try {
        const response = await fetch(API_ENDPOINTS.AUTH_LOGIN, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: 'demo@example.com',
            password: 'demo123'
          })
        });

        if (response.ok) {
          const data = await response.json();
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          console.log('Auto-login successful for demo@example.com');
        } else {
          console.error('Auto-login failed');
        }
      } catch (error) {
        console.error('Auto-login error:', error);
      }
    };

    autoLogin();
  }, []); // Run once on component mount

  // Generate video thumbnails
  useEffect(() => {
    if (videoUrl && playerRef.current && duration > 0) {
      generateThumbnails();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoUrl, duration]);

  const generateThumbnails = async () => {
    const video = document.createElement('video');
    video.src = videoUrl;
    video.crossOrigin = 'anonymous';
    
    await new Promise((resolve) => {
      video.onloadedmetadata = resolve;
    });

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const frameCount = 30; // Number of thumbnails to generate
    const interval = video.duration / frameCount;
    const thumbs: string[] = [];

    for (let i = 0; i < frameCount; i++) {
      video.currentTime = i * interval;
      await new Promise((resolve) => {
        video.onseeked = resolve;
      });

      canvas.width = 120;
      canvas.height = 68;
      ctx.drawImage(video, 0, 0, 120, 68);
      thumbs.push(canvas.toDataURL('image/jpeg', 0.7));
    }

    setThumbnails(thumbs);
  };

  // Calculate actual video display bounds within the container
  const calculateVideoBounds = () => {
    if (!playerRef.current || !videoContainerRef.current) return null;
    
    const internalPlayer = playerRef.current.getInternalPlayer();
    if (!internalPlayer || !internalPlayer.videoWidth || !internalPlayer.videoHeight) return null;
    
    const container = videoContainerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    const videoAspectRatio = internalPlayer.videoWidth / internalPlayer.videoHeight;
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
      height: videoDisplayHeight
    };
  };

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
        // Only update the central store
        setStoreTime(initialTime);
      }
    }
  };

  const handleProgress = (state: any) => {
    // Use the most precise time available from ReactPlayer
    const preciseTime = state.playedSeconds || 0;
    // Update only the central store to maintain single source of truth
    setStoreTime(preciseTime);
  };

  const handleDuration = (dur: number) => {
    // Update only the central store
    setStoreDuration(dur);
  };

  const handlePlayPause = () => {
    setStoreIsPlaying(!isPlaying);
  };

  const handleVolumeToggle = () => {
    setIsMuted(!isMuted);
  };

  const handleSeek = (time: number) => {
    if (playerRef.current && duration > 0) {
      // Use utility function for clamping
      const clampedTime = clampTime(time, duration);
      // Update only the central store
      setStoreTime(clampedTime);
      
      // Seek the player with high precision
      const seekPercentage = clampedTime / duration;
      playerRef.current.seekTo(seekPercentage, 'fraction');
    }
  };


  const handleAddEffect = (type: 'erasure' | 'protection' | 'text') => {
    setSelectedType(type);
    setIsDrawingMode(true);
    
    // Create a default rectangle
    setCurrentRect({
      x: 0.3,
      y: 0.3,
      width: 0.4,
      height: 0.4,
    });
  };

  const handleSaveRect = () => {
    if (!currentRect) return;

    const startTime = currentTime;
    const endTime = Math.min(currentTime + 5, duration);
    
    const newEffect: VideoEffect = {
      id: `effect_${Date.now()}`,
      type: selectedType,
      startTime,
      endTime,
      region: currentRect,
    };

    addEffect(newEffect);
    // Timeline effects will be automatically synchronized via useEffect
    
    setCurrentRect(null);
    setIsDrawingMode(false);
  };

  const handleCancelDrawing = () => {
    setCurrentRect(null);
    setIsDrawingMode(false);
  };

  const handleTimelineEffectDrag = (
    e: React.MouseEvent,
    effectId: string,
    type: 'start' | 'end' | 'move'
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(effectId);
    
    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!frameStripRef.current) return;
      
      // Use centralized timeline interaction for precise calculation
      const newTime = handleTimelineInteraction(
        moveEvent,
        frameStripRef.current,
        duration,
        timelineZoom
      );
      
      // Update the actual effect in store - timeline will auto-sync
      const effect = effects.find(e => e.id === effectId);
      if (effect) {
        if (type === 'start') {
          const maxStartTime = effect.endTime - 0.1; // Minimum 0.1s duration
          const newStartTime = Math.min(newTime, maxStartTime);
          updateEffect(effectId, { startTime: newStartTime });
        } else if (type === 'end') {
          const minEndTime = effect.startTime + 0.1; // Minimum 0.1s duration
          const newEndTime = Math.max(minEndTime, newTime);
          updateEffect(effectId, { endTime: clampTime(newEndTime, duration) });
        } else if (type === 'move') {
          const effectDuration = effect.endTime - effect.startTime;
          // Center the drag on the mouse position
          const newStartTime = clampTime(newTime - effectDuration / 2, duration - effectDuration);
          const newEndTime = newStartTime + effectDuration;
          updateEffect(effectId, {
            startTime: newStartTime,
            endTime: newEndTime
          });
        }
      }
    };
    
    const handleMouseUp = () => {
      setIsDragging(null);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleDeleteTimelineEffect = (id: string) => {
    deleteEffect(id);
    // Timeline effects will be automatically synchronized via useEffect
  };


  const handleEffectClick = (effectId: string, e: React.MouseEvent) => {
    // Only handle clicks that are not on drag handles or delete button
    if ((e.target as HTMLElement).closest('[data-drag-handle]') || 
        (e.target as HTMLElement).closest('button')) {
      return;
    }
    
    setEditingEffectId(effectId);
    setIsDrawingMode(false); // Exit any current drawing mode
  };

  const handleStopEditing = () => {
    setEditingEffectId(null);
  };

  // Use utility function for time formatting
  const formatTime = (seconds: number, includeMs: boolean = false): string => {
    if (includeMs) {
      return formatTimeUtil(seconds);
    }
    // For simple MM:SS format
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Use centralized calculation for progress percentage
  const progressPercentage = calculateProgressPercentage(currentTime, duration);
  
  // Debug logging and initial state sync
  useEffect(() => {
    console.log('Timeline Debug:', {
      currentTime,
      duration,
      progressPercentage,
      formatted: formatTime(currentTime),
      isVideoReady
    });
  }, [currentTime, duration, progressPercentage, isVideoReady]);
  
  // Force timeline update when video becomes ready
  useEffect(() => {
    if (isVideoReady && playerRef.current && duration > 0) {
      // Force a progress update to sync the timeline
      const currentState = playerRef.current.getCurrentTime();
      if (currentState !== undefined && currentState !== currentTime) {
        // Only update the central store
        setStoreTime(currentState);
      }
    }
  }, [isVideoReady, duration, currentTime, setStoreTime]);

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

  return (
    <Box sx={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      bgcolor: '#f5f5f5',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <Box sx={{ 
        bgcolor: 'white',
        borderBottom: '1px solid #e0e0e0',
        px: 2,
        py: 0.5,
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        minHeight: '48px'
      }}>
        <IconButton onClick={onBack || (() => navigate(-1))} size="small">
          <ArrowBack />
        </IconButton>
        <Typography sx={{ fontSize: '14px', color: '#666' }}>
          Video Erasure
        </Typography>

        {/* Audio Upload Box */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          mx: 2,
          p: 1,
          bgcolor: '#f8f9fa',
          borderRadius: 1,
          border: '1px solid #e0e0e0'
        }}>
          <Typography sx={{ fontSize: '12px', color: '#666', mr: 1 }}>
            Lip Sync:
          </Typography>
          <input
            type="file"
            accept="audio/*"
            id="audio-upload"
            style={{ display: 'none' }}
            onChange={(e) => {
              console.log('Audio input changed, files:', e.target.files);
              const file = e.target.files?.[0];
              if (file) {
                console.log('Audio file selected:', file.name, 'Type:', file.type, 'Size:', file.size);
                setAudioFile(file);
              } else {
                console.log('No audio file selected');
              }
            }}
          />
          <label htmlFor="audio-upload">
            <Button
              component="span"
              variant="outlined"
              size="small"
              sx={{
                fontSize: '11px',
                textTransform: 'none',
                minWidth: '80px',
                height: '28px',
                borderColor: audioFile ? '#52c41a' : '#d9d9d9',
                color: audioFile ? '#52c41a' : '#666',
                bgcolor: audioFile ? '#f6ffed' : 'white'
              }}
            >
              {audioFile ? 'Audio Ready' : 'Upload Audio'}
            </Button>
          </label>
          {audioFile && (
            <Typography sx={{ fontSize: '10px', color: '#52c41a', ml: 1 }}>
              {audioFile.name.slice(0, 15)}...
            </Typography>
          )}
        </Box>

        <Box sx={{ flex: 1 }} />
        <Typography sx={{ fontSize: '13px', color: '#999' }}>
          Basic Version
        </Typography>
        <Button
          variant="contained"
          size="small"
          disabled={isSubmitting}
          onClick={async () => {
            if (!videoFile) {
              console.error('No video file available for submission');
              return;
            }

            setIsSubmitting(true);
            setSubmissionProgress('Preparing video for processing...');

            try {
              console.log('Submitting video for AI processing...');
              
              const formData = new FormData();
              formData.append('file', videoFile);
              formData.append('display_name', `Video Processing - ${videoFile.name}`);

              // Include audio file for lip sync if uploaded
              if (audioFile) {
                formData.append('audio', audioFile);
                console.log('Including audio file for lip sync:', audioFile.name);
              }

              // Send region/effect data for targeted text removal
              if (effects.length > 0) {
                const effectsData = effects.map(effect => ({
                  type: effect.type, // 'erasure', 'protection', 'text'
                  startTime: effect.startTime, // ✅ Send actual time in seconds (not percentage)
                  endTime: effect.endTime,     // ✅ Send actual time in seconds (not percentage)
                  region: effect.region        // {x, y, width, height} normalized coordinates
                }));
                console.log('Sending effects data to backend:', effectsData);
                formData.append('effects', JSON.stringify(effectsData));
              }

              // Choose API endpoint based on whether audio is provided
              const apiEndpoint = audioFile
                ? API_ENDPOINTS.SYNC_PROCESS  // Use sync workflow for lip-sync + text removal
                : API_ENDPOINTS.DIRECT_PROCESS;  // Use direct workflow for text removal only

              const progressMessage = audioFile
                ? 'Uploading video and audio files for lip-sync processing...'
                : 'Uploading video and annotation data...';

              setSubmissionProgress(progressMessage);

              // Get auth token for API request
              const token = localStorage.getItem('access_token');
              console.log('Token from localStorage:', token ? `Bearer ${token.substring(0, 20)}...` : 'NO TOKEN');

              const headers: Record<string, string> = {};
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
                console.log('Authorization header set:', headers['Authorization'].substring(0, 30) + '...');
              } else {
                console.error('No authentication token found! User needs to be logged in.');
                setIsSubmitting(false);
                setSubmissionProgress('');
                alert('Not authenticated. Please refresh the page and try again.');
                return;
              }

              console.log('Sending request to:', apiEndpoint);
              console.log('Request headers:', headers);

              const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers,
                body: formData
              });

              console.log('Response status:', response.status);
              const result = await response.json();

              if (response.ok) {
                console.log('Video submitted successfully:', result);

                const successMessage = audioFile
                  ? 'Lip-sync and text removal job created successfully! Redirecting to jobs page...'
                  : 'Video processing job created successfully! Redirecting to jobs page...';

                setSubmissionProgress(successMessage);

                // Wait a bit to ensure the job appears in the database before navigating
                setTimeout(() => {
                  navigate('/jobs');
                }, 2000);
              } else {
                console.error('Submission failed:', result);
                console.error('Response status:', response.status);
                console.error('Response details:', result);
                setSubmissionProgress('');
                setIsSubmitting(false);

                // If 403, likely an auth issue
                if (response.status === 403) {
                  alert('Authentication failed. Please refresh the page to re-authenticate.');
                  // Try to re-authenticate
                  window.location.reload();
                } else {
                  alert(`Submission failed: ${result.detail || result.message || 'Unknown error'}`);
                }
              }
            } catch (error) {
              console.error('Error submitting video:', error);
              setSubmissionProgress('');
              setIsSubmitting(false);
              alert('Error submitting video. Please try again.');
            }
          }}
          sx={{
            bgcolor: '#1890ff',
            fontSize: '13px',
            px: 3,
            textTransform: 'none',
            '&:hover': {
              bgcolor: '#40a9ff'
            }
          }}
        >
          {isSubmitting ? 'Processing...' : 'Submit'}
        </Button>
      </Box>
      
      {/* Progress indicator for submission */}
      {isSubmitting && submissionProgress && (
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          py: 2,
          gap: 2
        }}>
          <Box sx={{
            width: 16,
            height: 16,
            border: '2px solid #f3f3f3',
            borderTop: '2px solid #1890ff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            '@keyframes spin': {
              '0%': { transform: 'rotate(0deg)' },
              '100%': { transform: 'rotate(360deg)' }
            }
          }} />
          <Typography sx={{ 
            fontSize: '14px', 
            color: '#666',
            fontStyle: 'italic'
          }}>
            {submissionProgress}
          </Typography>
        </Box>
      )}

      {/* Main Content Area */}
      <Box sx={{ 
        flex: 1, 
        display: 'flex', 
        overflow: 'hidden'
      }}>
        {/* Video and Timeline Section */}
        <Box sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
        
        {/* Video Player Container - Increased size */}
        <Box sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '55%', // Increased to give more space to video player
          bgcolor: '#000',
          p: 2 // Increased padding for better visual balance
        }}>
          <Box 
            ref={videoContainerRef}
            onClick={(e) => {
              // If clicking on the video container (not on an effect), stop editing
              if (e.target === e.currentTarget) {
                handleStopEditing();
              }
            }}
            sx={{ 
              width: '100%',
              maxWidth: '900px', // Larger max width for bigger video display
              height: '100%',
              bgcolor: 'black',
              position: 'relative',
              borderRadius: '4px',
              overflow: 'hidden',
            }}
          >
          <ReactPlayer
            ref={playerRef}
            url={videoUrl}
            playing={isPlaying}
            muted={isMuted}
            width="100%"
            height="100%"
            onReady={handleReady}
            onProgress={handleProgress}
            onDuration={handleDuration}
            onSeek={(seconds: number) => {
              // Sync only to central store
              setStoreTime(seconds);
            }}
            onError={(error: any) => {
              console.error('Video playback error:', error);
            }}
            progressInterval={50}
            controls={false}
          />

          {/* Video bounds container for proper constraint */}
          {videoBounds && (
            <Box
              className="video-bounds-container"
              sx={{
                position: 'absolute',
                left: videoBounds.x,
                top: videoBounds.y,
                width: videoBounds.width,
                height: videoBounds.height,
                pointerEvents: 'none',
                zIndex: 1,
              }}
            />
          )}

          {/* Drawing Rectangle Overlay */}
          {isDrawingMode && currentRect && videoBounds && (
            <Rnd
              default={{
                x: videoBounds.x + (currentRect.x * videoBounds.width),
                y: videoBounds.y + (currentRect.y * videoBounds.height),
                width: currentRect.width * videoBounds.width,
                height: currentRect.height * videoBounds.height,
              }}
              bounds=".video-bounds-container"
              onDragStop={(e, d) => {
                if (videoBounds) {
                  setCurrentRect({
                    x: (d.x - videoBounds.x) / videoBounds.width,
                    y: (d.y - videoBounds.y) / videoBounds.height,
                    width: currentRect.width,
                    height: currentRect.height,
                  });
                }
              }}
              onResizeStop={(e, direction, ref, delta, position) => {
                if (videoBounds) {
                  setCurrentRect({
                    x: (position.x - videoBounds.x) / videoBounds.width,
                    y: (position.y - videoBounds.y) / videoBounds.height,
                    width: parseInt(ref.style.width) / videoBounds.width,
                    height: parseInt(ref.style.height) / videoBounds.height,
                  });
                }
              }}
              style={{
                border: `3px solid ${selectedType === 'erasure' ? '#5B8FF9' : selectedType === 'protection' ? '#5AD8A6' : '#5D7092'}`,
                backgroundColor: `${selectedType === 'erasure' ? 'rgba(91, 143, 249, 0.15)' : selectedType === 'protection' ? 'rgba(90, 216, 166, 0.15)' : 'rgba(93, 112, 146, 0.15)'}`,
                position: 'absolute',
                zIndex: 10,
                boxShadow: '0 0 10px rgba(0, 0, 0, 0.3)',
              }}
            >
              {/* Corner dots for all effect types during drawing */}
              {(() => {
                const dotColor = selectedType === 'erasure' ? '#5B8FF9' :
                               selectedType === 'protection' ? '#5AD8A6' : '#5D7092';
                const hoverColor = selectedType === 'erasure' ? '#40a9ff' :
                                 selectedType === 'protection' ? '#52c41a' : '#434c5e';
                
                return (
                  <>
                    {/* Top-left corner dot */}
                    <Box
                      sx={{
                        position: 'absolute',
                        left: -4,
                        top: -4,
                        width: 8,
                        height: 8,
                        backgroundColor: dotColor,
                        border: '2px solid white',
                        borderRadius: '50%',
                        cursor: 'nw-resize',
                        pointerEvents: 'auto',
                        '&:hover': {
                          backgroundColor: hoverColor,
                          transform: 'scale(1.2)',
                        }
                      }}
                    />
                    
                    {/* Top-right corner dot */}
                    <Box
                      sx={{
                        position: 'absolute',
                        right: -4,
                        top: -4,
                        width: 8,
                        height: 8,
                        backgroundColor: dotColor,
                        border: '2px solid white',
                        borderRadius: '50%',
                        cursor: 'ne-resize',
                        pointerEvents: 'auto',
                        '&:hover': {
                          backgroundColor: hoverColor,
                          transform: 'scale(1.2)',
                        }
                      }}
                    />
                    
                    {/* Bottom-left corner dot */}
                    <Box
                      sx={{
                        position: 'absolute',
                        left: -4,
                        bottom: -4,
                        width: 8,
                        height: 8,
                        backgroundColor: dotColor,
                        border: '2px solid white',
                        borderRadius: '50%',
                        cursor: 'sw-resize',
                        pointerEvents: 'auto',
                        '&:hover': {
                          backgroundColor: hoverColor,
                          transform: 'scale(1.2)',
                        }
                      }}
                    />
                    
                    {/* Bottom-right corner dot */}
                    <Box
                      sx={{
                        position: 'absolute',
                        right: -4,
                        bottom: -4,
                        width: 8,
                        height: 8,
                        backgroundColor: dotColor,
                        border: '2px solid white',
                        borderRadius: '50%',
                        cursor: 'se-resize',
                        pointerEvents: 'auto',
                        '&:hover': {
                          backgroundColor: hoverColor,
                          transform: 'scale(1.2)',
                        }
                      }}
                    />
                  </>
                );
              })()}
              
              <Box sx={{
                position: 'absolute',
                top: -50,
                left: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5,
              }}>
                {/* Time range display */}
                <Typography sx={{
                  fontSize: '10px',
                  color: '#fff',
                  bgcolor: 'rgba(0, 0, 0, 0.7)',
                  px: 1,
                  py: 0.5,
                  borderRadius: '3px',
                  fontFamily: 'monospace',
                  whiteSpace: 'nowrap'
                }}>
                  {formatTime(currentTime, true)} - {formatTime(Math.min(currentTime + 5, duration), true)}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={handleSaveRect}
                    sx={{ 
                      fontSize: '11px',
                      minWidth: 'auto',
                      px: 1,
                      py: 0.5,
                      bgcolor: '#52c41a',
                      '&:hover': { bgcolor: '#73d13d' }
                    }}
                  >
                    Confirm
                  </Button>
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={handleCancelDrawing}
                    sx={{ 
                      fontSize: '11px',
                      minWidth: 'auto',
                      px: 1,
                      py: 0.5,
                      borderColor: '#ff4d4f',
                      color: '#ff4d4f',
                      '&:hover': { 
                        borderColor: '#ff7875',
                        color: '#ff7875'
                      }
                    }}
                  >
                    Cancel
                  </Button>
                </Box>
              </Box>
            </Rnd>
          )}

          {/* Display existing rectangles - Sort by area to show smaller ones on top */}
          {effects.filter(e => 
            currentTime >= e.startTime && currentTime <= e.endTime
          ).sort((a, b) => {
            // Sort by area (larger areas first, so smaller ones appear on top)
            const areaA = a.region.width * a.region.height;
            const areaB = b.region.width * b.region.height;
            return areaB - areaA;
          }).map((effect, index) => {
            const isEditing = editingEffectId === effect.id;
            
            // If editing, use Rnd component for full functionality
            if (isEditing && videoBounds) {
              return (
                <Rnd
                  key={effect.id}
                  default={{
                    x: videoBounds.x + (effect.region.x * videoBounds.width),
                    y: videoBounds.y + (effect.region.y * videoBounds.height),
                    width: effect.region.width * videoBounds.width,
                    height: effect.region.height * videoBounds.height,
                  }}
                  bounds=".video-bounds-container"
                  onDragStop={(e, d) => {
                    if (videoBounds) {
                      const newRegion = {
                        x: (d.x - videoBounds.x) / videoBounds.width,
                        y: (d.y - videoBounds.y) / videoBounds.height,
                        width: effect.region.width,
                        height: effect.region.height,
                      };
                      updateEffect(effect.id, { region: newRegion });
                    }
                  }}
                  onResizeStop={(e, direction, ref, delta, position) => {
                    if (videoBounds) {
                      const newRegion = {
                        x: (position.x - videoBounds.x) / videoBounds.width,
                        y: (position.y - videoBounds.y) / videoBounds.height,
                        width: parseInt(ref.style.width) / videoBounds.width,
                        height: parseInt(ref.style.height) / videoBounds.height,
                      };
                      updateEffect(effect.id, { region: newRegion });
                    }
                  }}
                  style={{
                    border: `2px solid ${
                      effect.type === 'erasure' ? '#5B8FF9' :
                      effect.type === 'protection' ? '#5AD8A6' : '#5D7092'
                    }`,
                    backgroundColor: `${
                      effect.type === 'erasure' ? 'rgba(91, 143, 249, 0.1)' :
                      effect.type === 'protection' ? 'rgba(90, 216, 166, 0.1)' : 
                      'rgba(93, 112, 146, 0.1)'
                    }`,
                    position: 'absolute',
                    zIndex: 20 - index, // Higher z-index for smaller/later effects
                    outline: '2px dashed #fff',
                    outlineOffset: '4px',
                  }}
                >
                  {/* Corner dots for editing all effect types */}
                  <>
                    {(() => {
                      const dotColor = effect.type === 'erasure' ? '#5B8FF9' :
                                     effect.type === 'protection' ? '#5AD8A6' : '#5D7092';
                      const hoverColor = effect.type === 'erasure' ? '#40a9ff' :
                                       effect.type === 'protection' ? '#52c41a' : '#434c5e';
                      
                      return (
                        <>
                          {/* Top-left corner dot */}
                          <Box
                            sx={{
                              position: 'absolute',
                              left: -4,
                              top: -4,
                              width: 8,
                              height: 8,
                              backgroundColor: dotColor,
                              border: '2px solid white',
                              borderRadius: '50%',
                              cursor: 'nw-resize',
                              pointerEvents: 'auto',
                              '&:hover': {
                                backgroundColor: hoverColor,
                                transform: 'scale(1.2)',
                              }
                            }}
                          />
                          
                          {/* Top-right corner dot */}
                          <Box
                            sx={{
                              position: 'absolute',
                              right: -4,
                              top: -4,
                              width: 8,
                              height: 8,
                              backgroundColor: dotColor,
                              border: '2px solid white',
                              borderRadius: '50%',
                              cursor: 'ne-resize',
                              pointerEvents: 'auto',
                              '&:hover': {
                                backgroundColor: hoverColor,
                                transform: 'scale(1.2)',
                              }
                            }}
                          />
                          
                          {/* Bottom-left corner dot */}
                          <Box
                            sx={{
                              position: 'absolute',
                              left: -4,
                              bottom: -4,
                              width: 8,
                              height: 8,
                              backgroundColor: dotColor,
                              border: '2px solid white',
                              borderRadius: '50%',
                              cursor: 'sw-resize',
                              pointerEvents: 'auto',
                              '&:hover': {
                                backgroundColor: hoverColor,
                                transform: 'scale(1.2)',
                              }
                            }}
                          />
                          
                          {/* Bottom-right corner dot */}
                          <Box
                            sx={{
                              position: 'absolute',
                              right: -4,
                              bottom: -4,
                              width: 8,
                              height: 8,
                              backgroundColor: dotColor,
                              border: '2px solid white',
                              borderRadius: '50%',
                              cursor: 'se-resize',
                              pointerEvents: 'auto',
                              '&:hover': {
                                backgroundColor: hoverColor,
                                transform: 'scale(1.2)',
                              }
                            }}
                          />
                        </>
                      );
                    })()}
                  </>
                  
                  {/* Delete button positioned on the right side away from corner dots */}
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteEffect(effect.id);
                      setEditingEffectId(null);
                    }}
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      right: -30,
                      transform: 'translateY(-50%)',
                      width: 24,
                      height: 24,
                      bgcolor: '#ff4d4f',
                      color: 'white',
                      '&:hover': {
                        bgcolor: '#ff7875',
                        transform: 'translateY(-50%) scale(1.1)',
                      },
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                      zIndex: 20,
                    }}
                  >
                    <Close sx={{ fontSize: 14 }} />
                  </IconButton>
                  
                  {/* Edit mode controls */}
                  <Box sx={{
                    position: 'absolute',
                    top: -30,
                    left: 0,
                    display: 'flex',
                    gap: 1,
                  }}>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={handleStopEditing}
                      sx={{ 
                        fontSize: '11px',
                        minWidth: 'auto',
                        px: 1,
                        py: 0.5,
                        bgcolor: '#52c41a',
                        '&:hover': { bgcolor: '#73d13d' }
                      }}
                    >
                      Done
                    </Button>
                  </Box>
                </Rnd>
              );
            }
            
            // For non-editing effects, use static Box that can be clicked to enter edit mode
            if (!videoBounds) return null;
            
            return (
              <Box
                key={effect.id}
                sx={{
                  position: 'absolute',
                  left: `${videoBounds.x + (effect.region.x * videoBounds.width)}px`,
                  top: `${videoBounds.y + (effect.region.y * videoBounds.height)}px`,
                  width: `${effect.region.width * videoBounds.width}px`,
                  height: `${effect.region.height * videoBounds.height}px`,
                  border: `2px solid ${
                    effect.type === 'erasure' ? '#5B8FF9' :
                    effect.type === 'protection' ? '#5AD8A6' : '#5D7092'
                  }`,
                  backgroundColor: `${
                    effect.type === 'erasure' ? 'rgba(91, 143, 249, 0.1)' :
                    effect.type === 'protection' ? 'rgba(90, 216, 166, 0.1)' : 
                    'rgba(93, 112, 146, 0.1)'
                  }`,
                  pointerEvents: 'auto',
                  cursor: 'pointer',
                  zIndex: 15 - index, // Higher z-index for smaller/later effects
                  '&:hover': {
                    opacity: 0.8,
                    '& .delete-button': {
                      opacity: 1,
                    }
                  }
                }}
                onClick={() => setEditingEffectId(effect.id)}
              >
                {/* Delete button positioned on right side - hidden by default, shown on hover */}
                <IconButton
                  className="delete-button"
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteEffect(effect.id);
                  }}
                  sx={{
                    position: 'absolute',
                    top: '50%',
                    right: -30,
                    transform: 'translateY(-50%)',
                    width: 24,
                    height: 24,
                    bgcolor: '#ff4d4f',
                    color: 'white',
                    opacity: 0,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      bgcolor: '#ff7875',
                      transform: 'translateY(-50%) scale(1.1)',
                      opacity: '1 !important',
                    },
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    zIndex: 20,
                  }}
                >
                  <Close sx={{ fontSize: 14 }} />
                </IconButton>
              </Box>
            );
          })}
          </Box>
        </Box>

        {/* Timeline Controls - Compact */}
        <Box sx={{ 
          flex: 1,
          bgcolor: 'white',
          display: 'flex',
          flexDirection: 'column',
          borderTop: '2px solid #e0e0e0',
          overflow: 'auto',
          minHeight: '45%', // Reduced space for timeline to give more to video
          maxHeight: '45%' // Limit timeline height
        }}>
          {/* Control Buttons */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, // Further reduced gap
            p: 1, // Further reduced padding
            borderBottom: '1px solid #f0f0f0',
            bgcolor: 'white',
            flexWrap: 'wrap',
            minHeight: '50px' // Set minimum height for compactness
          }}>
            {/* Undo/Redo Controls */}
            <IconButton 
              onClick={undo}
              disabled={!canUndo()}
              size="small"
              sx={{
                color: canUndo() ? '#333' : '#ccc',
                '&:hover': {
                  bgcolor: canUndo() ? 'rgba(0,0,0,0.08)' : 'transparent'
                }
              }}
              title="Undo (Ctrl+Z)"
            >
              <Undo />
            </IconButton>
            
            <IconButton 
              onClick={redo}
              disabled={!canRedo()}
              size="small"
              sx={{
                color: canRedo() ? '#333' : '#ccc',
                '&:hover': {
                  bgcolor: canRedo() ? 'rgba(0,0,0,0.08)' : 'transparent'
                }
              }}
              title="Redo (Ctrl+Y)"
            >
              <Redo />
            </IconButton>
            
            {/* Separator */}
            <Box sx={{ 
              width: '1px', 
              height: '20px', 
              bgcolor: '#e0e0e0',
              mx: 1
            }} />
            

            <IconButton 
              onClick={handlePlayPause}
              sx={{ 
                bgcolor: '#1890ff',
                color: 'white',
                '&:hover': { bgcolor: '#40a9ff' }
              }}
            >
              {isPlaying ? <Pause /> : <PlayArrow />}
            </IconButton>

            <Button
              variant="contained"
              size="small"
              onClick={() => handleAddEffect('erasure')}
              startIcon={
                <Box sx={{ 
                  width: 16, 
                  height: 16, 
                  borderRadius: '50%', 
                  bgcolor: '#5B8FF9' 
                }}>
                  {/* Color indicator */}
                </Box>
              }
              sx={{
                bgcolor: 'white',
                color: '#333',
                border: '1px solid #d9d9d9',
                fontSize: '13px',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: '#fafafa',
                  borderColor: '#40a9ff'
                }
              }}
            >
              Add Erasure Area
            </Button>

            <Button
              variant="contained"
              size="small"
              onClick={() => handleAddEffect('protection')}
              startIcon={
                <Box sx={{ 
                  width: 16, 
                  height: 16, 
                  borderRadius: '50%', 
                  bgcolor: '#5AD8A6' 
                }}>
                  {/* Color indicator */}
                </Box>
              }
              sx={{
                bgcolor: 'white',
                color: '#333',
                border: '1px solid #d9d9d9',
                fontSize: '13px',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: '#fafafa',
                  borderColor: '#52c41a'
                }
              }}
            >
              Add Protection Area
            </Button>

            <Button
              variant="contained"
              size="small"
              onClick={() => handleAddEffect('text')}
              startIcon={
                <Box sx={{ 
                  width: 16, 
                  height: 16, 
                  borderRadius: '50%', 
                  bgcolor: '#5D7092' 
                }}>
                  {/* Color indicator */}
                </Box>
              }
              sx={{
                bgcolor: 'white',
                color: '#333',
                border: '1px solid #d9d9d9',
                fontSize: '13px',
                textTransform: 'none',
                '&:hover': {
                  bgcolor: '#fafafa',
                  borderColor: '#666'
                }
              }}
            >
              Erase Text
            </Button>


            <Box sx={{ flex: 1 }} />

            <Typography sx={{ fontSize: '13px', color: '#666', fontFamily: 'monospace' }}>
              {formatTime(currentTime, true)} / {formatTime(duration, true)}
            </Typography>

            <IconButton 
              size="small"
              onClick={handleVolumeToggle}
              sx={{
                color: isMuted ? '#ff4d4f' : '#666',
                '&:hover': {
                  bgcolor: 'rgba(0,0,0,0.08)'
                }
              }}
            >
              {isMuted ? <VolumeOff fontSize="small" /> : <VolumeUp fontSize="small" />}
            </IconButton>
            
            {/* Timeline Zoom Controls */}
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1,
              ml: 2,
              minWidth: 150
            }}>
              <Typography sx={{ fontSize: '11px', color: '#666', whiteSpace: 'nowrap' }}>
                Zoom
              </Typography>
              <Slider
                value={timelineZoom}
                onChange={(e, value) => setTimelineZoom(value as number)}
                min={0.5}
                max={5}
                step={0.1}
                size="small"
                marks={[{ value: 1, label: '1:1' }]}
                sx={{
                  width: 80,
                  '& .MuiSlider-thumb': {
                    width: 16,
                    height: 16,
                  },
                  '& .MuiSlider-track': {
                    color: '#1890ff',
                  },
                  '& .MuiSlider-rail': {
                    color: '#d9d9d9',
                  },
                  '& .MuiSlider-mark': {
                    backgroundColor: '#1890ff',
                    height: 8,
                    width: 2,
                  },
                  '& .MuiSlider-markActive': {
                    backgroundColor: '#1890ff',
                  },
                  '& .MuiSlider-markLabel': {
                    fontSize: '9px',
                    color: '#666',
                    top: 20,
                  }
                }}
              />
              <Button
                size="small"
                variant={timelineZoom === 1 ? "contained" : "outlined"}
                onClick={() => setTimelineZoom(1)}
                sx={{
                  minWidth: 'auto',
                  px: 1,
                  py: 0.25,
                  fontSize: '10px',
                  height: 20,
                  bgcolor: timelineZoom === 1 ? '#1890ff' : 'transparent',
                  color: timelineZoom === 1 ? 'white' : '#666',
                  borderColor: '#d9d9d9',
                  '&:hover': {
                    bgcolor: timelineZoom === 1 ? '#40a9ff' : 'rgba(24, 144, 255, 0.1)',
                    borderColor: '#1890ff'
                  }
                }}
              >
                1:1
              </Button>
            </Box>
          </Box>

          {/* Video Frames Timeline - GhostCut Style */}
          <Box sx={{ 
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'white',
            overflow: 'hidden',
            minHeight: '300px'
          }}>
            
            {/* New Simplified Time Ruler */}
            <Box 
              data-timeline-ruler
              onClick={(e) => {
                // Use centralized timeline interaction handler
                const newTime = handleTimelineInteraction(
                  e.nativeEvent,
                  e.currentTarget,
                  duration,
                  timelineZoom
                );
                handleSeek(newTime);
              }}
              sx={{
                height: 40,
                bgcolor: '#ffffff',
                borderTop: '1px solid #e0e0e0',
                borderBottom: '1px solid #e0e0e0',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                cursor: 'pointer',
                overflow: 'hidden',
                minWidth: `${100 * timelineZoom}%`,
                width: `${100 * timelineZoom}%`,
              }}>
              
              {/* Background gradient for visual appeal */}
              <Box sx={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: 0,
                bottom: 0,
                background: 'linear-gradient(to bottom, #f8f9fa, #ffffff)',
                pointerEvents: 'none'
              }} />
              
              {/* Time marks based on actual time positions */}
              {Array.from({ length: Math.min(11, Math.ceil(duration) + 1) }, (_, i) => {
                const markTime = (i / 10) * duration;
                // Use the same percentage calculation as effects and timeline indicator
                const markPercentage = calculateProgressPercentage(markTime, duration);
                const isMainMark = i % 2 === 0;
                return (
                  <Box key={i} sx={{
                    position: 'absolute',
                    left: `${markPercentage}%`,
                    top: 0,
                    bottom: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    pointerEvents: 'none'
                  }}>
                    {/* Time label with milliseconds */}
                    {isMainMark && (
                      <Typography sx={{
                        position: 'absolute',
                        top: '2px',
                        fontSize: '10px',
                        color: '#666',
                        fontFamily: 'monospace',
                        fontWeight: 500,
                        userSelect: 'none'
                      }}>
                        {formatTime(markTime, true)}
                      </Typography>
                    )}
                    {/* Tick mark */}
                    <Box sx={{
                      width: '1px',
                      height: isMainMark ? '12px' : '8px',
                      bgcolor: isMainMark ? '#999' : '#ccc',
                      position: 'absolute',
                      bottom: 0
                    }} />
                  </Box>
                );
              })}
              
              {/* Current time indicator - clean red line with draggable handle */}
              {isVideoReady && duration > 0 && (
                <>
                  <Box
                    sx={{
                      position: 'absolute',
                      left: `${progressPercentage}%`,
                      top: 0,
                      bottom: 0,
                      width: '2px',
                      bgcolor: '#ff4d4f',
                      zIndex: 20,
                      pointerEvents: 'none',
                      boxShadow: '0 0 6px rgba(255, 77, 79, 0.6)'
                    }}
                  />
                  
                  {/* Draggable time handle */}
                  <Box
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingTimeline(true);
                      const startX = e.clientX;
                      const startTime = currentTime;
                      
                      // Get timeline container reference
                      const timelineContainer = e.currentTarget.closest('[data-timeline-ruler]') as HTMLElement;
                      if (!timelineContainer) {
                        setIsDraggingTimeline(false);
                        return;
                      }
                      
                      const handleMouseMove = (moveEvent: MouseEvent) => {
                        // Use centralized timeline interaction
                        const newTime = handleTimelineInteraction(
                          moveEvent,
                          timelineContainer,
                          duration,
                          timelineZoom
                        );
                        handleSeek(newTime);
                      };
                      
                      const handleMouseUp = () => {
                        setIsDraggingTimeline(false);
                        document.removeEventListener('mousemove', handleMouseMove);
                        document.removeEventListener('mouseup', handleMouseUp);
                      };
                      
                      document.addEventListener('mousemove', handleMouseMove);
                      document.addEventListener('mouseup', handleMouseUp);
                    }}
                    sx={{
                      position: 'absolute',
                      left: `${progressPercentage}%`,
                      top: -3,
                      width: '8px',
                      height: '46px',
                      bgcolor: isDraggingTimeline ? 'rgba(255, 77, 79, 0.2)' : 'transparent',
                      cursor: 'ew-resize',
                      zIndex: 21,
                      transform: 'translateX(-4px)',
                      borderRadius: '2px',
                      '&:hover': {
                        bgcolor: 'rgba(255, 77, 79, 0.15)',
                        '&::after': {
                          content: '""',
                          position: 'absolute',
                          left: '50%',
                          top: '50%',
                          transform: 'translate(-50%, -50%)',
                          width: '3px',
                          height: '20px',
                          bgcolor: '#ff4d4f',
                          borderRadius: '1px',
                          boxShadow: '0 0 4px rgba(255, 77, 79, 0.8)'
                        }
                      }
                    }}
                  />
                  
                  {/* Current time display */}
                  <Box
                    sx={{
                      position: 'absolute',
                      left: `${progressPercentage}%`,
                      top: '50%',
                      transform: 'translate(-50%, -50%)',
                      bgcolor: '#ff4d4f',
                      color: 'white',
                      px: 1,
                      py: 0.25,
                      borderRadius: '3px',
                      fontSize: '10px',
                      fontWeight: 600,
                      whiteSpace: 'nowrap',
                      zIndex: 21,
                      pointerEvents: 'none',
                      opacity: progressPercentage > 5 && progressPercentage < 95 ? 1 : 0,
                      transition: 'opacity 0.2s'
                    }}
                  >
                    {formatTime(currentTime, true)}
                  </Box>
                </>
              )}
            </Box>
            
            {/* Timeline Content Area */}
            <Box sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'auto'
            }}>
            
            {/* Frame Strip - GhostCut Style */}
            <Box 
              ref={frameStripRef}
              data-frame-strip
              onClick={(e) => {
                // Use centralized timeline interaction handler
                const newTime = handleTimelineInteraction(
                  e.nativeEvent,
                  e.currentTarget,
                  duration,
                  timelineZoom
                );
                handleSeek(newTime);
              }}
              sx={{
                height: 80,
                bgcolor: 'white',
                borderRadius: '6px',
                overflow: 'hidden',
                cursor: 'pointer',
                display: 'flex',
                position: 'relative',
                border: '1px solid #d9d9d9',
                mb: 1,
                minWidth: `${100 * timelineZoom}%`,
                width: `${100 * timelineZoom}%`,
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
              }}
            >
              {/* Thumbnail Images with borders */}
              {thumbnails.map((thumb, index) => (
                <Box
                  key={index}
                  sx={{
                    height: '100%',
                    width: `${100 / thumbnails.length}%`,
                    position: 'relative',
                    borderRight: index < thumbnails.length - 1 ? '1px solid #e9ecef' : 'none'
                  }}
                >
                  <Box
                    component="img"
                    src={thumb}
                    sx={{
                      height: '100%',
                      width: '100%',
                      objectFit: 'cover',
                      userSelect: 'none',
                      pointerEvents: 'none',
                    }}
                  />
                </Box>
              ))}
              
              {/* Current Time Indicator on Frame Strip - Clean vertical line with draggable handle */}
              {isVideoReady && duration > 0 && (
                <>
                  <Box
                    sx={{
                      position: 'absolute',
                      left: `${progressPercentage}%`,
                      top: 0,
                      bottom: 0,
                      width: '2px',
                      bgcolor: '#ff4d4f',
                      zIndex: 30,
                      pointerEvents: 'none',
                      boxShadow: '0 0 6px rgba(255, 77, 79, 0.6)'
                    }}
                  />
                  
                  {/* Draggable handle for frame strip */}
                  <Box
                    onMouseDown={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingTimeline(true);
                      const startX = e.clientX;
                      const startTime = currentTime;
                      
                      // Get frame strip container reference
                      const frameStripContainer = e.currentTarget.closest('[data-frame-strip]') as HTMLElement;
                      if (!frameStripContainer) {
                        setIsDraggingTimeline(false);
                        return;
                      }
                      
                      const handleMouseMove = (moveEvent: MouseEvent) => {
                        // Use centralized timeline interaction
                        const newTime = handleTimelineInteraction(
                          moveEvent,
                          frameStripContainer,
                          duration,
                          timelineZoom
                        );
                        handleSeek(newTime);
                      };
                      
                      const handleMouseUp = () => {
                        setIsDraggingTimeline(false);
                        document.removeEventListener('mousemove', handleMouseMove);
                        document.removeEventListener('mouseup', handleMouseUp);
                      };
                      
                      document.addEventListener('mousemove', handleMouseMove);
                      document.addEventListener('mouseup', handleMouseUp);
                    }}
                    sx={{
                      position: 'absolute',
                      left: `${progressPercentage}%`,
                      top: -5,
                      width: '8px',
                      height: '90px',
                      bgcolor: isDraggingTimeline ? 'rgba(255, 77, 79, 0.2)' : 'transparent',
                      cursor: 'ew-resize',
                      zIndex: 31,
                      transform: 'translateX(-4px)',
                      borderRadius: '2px',
                      '&:hover': {
                        bgcolor: 'rgba(255, 77, 79, 0.15)',
                        '&::after': {
                          content: '""',
                          position: 'absolute',
                          left: '50%',
                          top: '50%',
                          transform: 'translate(-50%, -50%)',
                          width: '3px',
                          height: '40px',
                          bgcolor: '#ff4d4f',
                          borderRadius: '1px',
                          boxShadow: '0 0 4px rgba(255, 77, 79, 0.8)'
                        }
                      }
                    }}
                  />
                </>
              )}

            </Box>

            {/* Timeline Effects Tracks - GhostCut Style */}
            <Box sx={{ 
              position: 'relative',
              flex: 1,
              minHeight: 200,
              maxHeight: 300,
              bgcolor: 'white',
              borderRadius: '6px',
              border: '1px solid #d9d9d9',
              display: 'flex',
              flexDirection: 'column',
              minWidth: `${100 * timelineZoom}%`,
              width: `${100 * timelineZoom}%`,
              boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
              overflow: 'hidden' // Add overflow hidden to contain the timeline
            }}>
              {/* Timeline Indicator spanning entire timeline effects area */}
              {isVideoReady && duration > 0 && (
                <Box
                  sx={{
                    position: 'absolute',
                    left: `${progressPercentage}%`,
                    top: 0,
                    bottom: 0,
                    width: '2px',
                    bgcolor: '#ff4d4f',
                    zIndex: 100,
                    pointerEvents: 'none',
                    boxShadow: '0 0 6px rgba(255, 77, 79, 0.6)',
                    transform: 'translateX(-1px)',
                  }}
                />
              )}
              
              {/* Simple header without duplicate buttons */}
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center',
                justifyContent: 'space-between',
                mb: 1.5,
                pb: 1,
                borderBottom: '1px solid #e9ecef'
              }}>
                <Typography sx={{ fontSize: '12px', color: '#666', fontWeight: 500 }}>
                  Effect Track
                </Typography>
                <Typography sx={{ fontSize: '11px', color: '#999' }}>
                  Current Effects ({timelineEffects.length})
                </Typography>
              </Box>
              
              {/* Effect Bars - GhostCut Style with Separate Tracks */}
              <Box sx={{ 
                position: 'relative', 
                flex: 1, 
                minHeight: '150px',
                maxHeight: '220px',
                overflowY: 'auto',
                overflowX: 'hidden',
                '&::-webkit-scrollbar': {
                  width: '6px',
                },
                '&::-webkit-scrollbar-track': {
                  backgroundColor: '#f5f5f5',
                  borderRadius: '3px',
                },
                '&::-webkit-scrollbar-thumb': {
                  backgroundColor: '#d9d9d9',
                  borderRadius: '3px',
                  '&:hover': {
                    backgroundColor: '#bfbfbf',
                  },
                },
              }}>
              
              {/* Dynamic effect rows - each effect gets its own row */}
              <Box sx={{
                position: 'relative',
                height: `${Math.max(50, timelineEffects.length * 40)}px`,
                width: '100%'
              }}>
                
  
              {timelineEffects.map((effect, index) => {
                  // Each effect gets its own row
                  const trackTop = index * 40 + 5; // 40px spacing between rows, 5px top margin
                
                  // Use the same calculation as timeline indicator for perfect sync
                  const trackWidth = 100; // Full width percentage
                  // Direct percentage values without additional division
                  const effectLeft = effect.startFrame;
                  const effectWidth = effect.endFrame - effect.startFrame;
                
                return (
                  <Box
                    key={effect.id}
                    sx={{
                      position: 'absolute',
                      left: `${effectLeft}%`,
                      width: `${effectWidth}%`,
                      top: `${trackTop}px`,
                      height: '30px',
                      bgcolor: effect.color,
                      borderRadius: '4px',
                      cursor: 'move',
                      display: 'flex',
                      alignItems: 'center',
                      px: 1,
                      opacity: editingEffectId === effect.id ? 1 : 0.85,
                      zIndex: 15,
                      border: editingEffectId === effect.id ? '2px solid #1890ff' : '1px solid rgba(255,255,255,0.3)',
                      boxShadow: editingEffectId === effect.id ? '0 2px 8px rgba(24,144,255,0.4)' : '0 1px 3px rgba(0,0,0,0.1)',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        opacity: 1,
                        transform: 'translateY(-1px)',
                        boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                        '& [data-drag-handle="true"]': {
                          opacity: 1
                        }
                      }
                    }}
                    onMouseDown={(e) => handleTimelineEffectDrag(e, effect.id, 'move')}
                    onClick={(e) => handleEffectClick(effect.id, e)}
                  >
                    {/* Start Handle - More subtle */}
                    <Box
                      data-drag-handle="true"
                      sx={{
                        position: 'absolute',
                        left: -2,
                        top: 0,
                        bottom: 0,
                        width: '6px',
                        bgcolor: 'rgba(255,255,255,0.8)',
                        cursor: 'ew-resize',
                        borderRadius: '2px 0 0 2px',
                        opacity: 0,
                        transition: 'opacity 0.2s ease',
                        '&:hover': {
                          bgcolor: 'rgba(255,255,255,1)',
                          opacity: 1,
                        }
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        handleTimelineEffectDrag(e, effect.id, 'start');
                      }}
                    />

                    {/* Label with time range */}
                    <Box sx={{ 
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <Typography sx={{ 
                        color: 'white',
                        fontSize: '9px',
                        fontWeight: 600,
                        userSelect: 'none',
                        textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                      }}>
                        {effect.label}
                      </Typography>
                      <Typography sx={{ 
                        color: 'rgba(255, 255, 255, 0.9)',
                        fontSize: '8px',
                        fontFamily: 'monospace',
                        userSelect: 'none',
                        textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                      }}>
                        {(() => {
                          const startTime = (effect.startFrame / 100) * duration;
                          const endTime = (effect.endFrame / 100) * duration;
                          return `${formatTime(startTime, true)} - ${formatTime(endTime, true)}`;
                        })()}
                      </Typography>
                    </Box>

                    {/* Delete Button - More subtle */}
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTimelineEffect(effect.id);
                      }}
                      sx={{
                        p: 0.25,
                        color: 'rgba(255,255,255,0.9)',
                        opacity: 0.8,
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          bgcolor: 'rgba(255,255,255,0.2)',
                          opacity: 1,
                          transform: 'scale(1.1)'
                        }
                      }}
                    >
                      <Delete sx={{ fontSize: 12 }} />
                    </IconButton>

                    {/* End Handle - More subtle */}
                    <Box
                      data-drag-handle="true"
                      sx={{
                        position: 'absolute',
                        right: -2,
                        top: 0,
                        bottom: 0,
                        width: '6px',
                        bgcolor: 'rgba(255,255,255,0.8)',
                        cursor: 'ew-resize',
                        borderRadius: '0 2px 2px 0',
                        opacity: 0,
                        transition: 'opacity 0.2s ease',
                        '&:hover': {
                          bgcolor: 'rgba(255,255,255,1)',
                          opacity: 1,
                        }
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        handleTimelineEffectDrag(e, effect.id, 'end');
                      }}
                    />
                  </Box>
                );
              })}
              </Box>
            </Box> {/* Close Timeline Content Area */}
          </Box> {/* Close Video Frames Timeline */}
        </Box> {/* Close Main Content Area */}

      </Box>
    </Box>
    </Box>
    </Box>
    </Box>
  );
};

export default GhostCutVideoEditor;
/**
 * Embedded Editor Page for phraze.so integration
 * This page loads videos from S3 URL provided via JWT token
 * Routes to Normal or Pro editor based on subscription tier
 * No upload UI - video is pre-loaded from phraze.so
 * Updated: 2025-12-25 - Force rebuild for Railway deployment
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Box, CircularProgress, Typography, Alert, Button, Chip } from '@mui/material';
import { Error as ErrorIcon, Refresh as RefreshIcon, Star as StarIcon } from '@mui/icons-material';

import GhostCutVideoEditor from '../../components/VideoEditor/GhostCutVideoEditor';
import ProVideoEditor from '../../components/VideoEditor/Pro/ProVideoEditor';
import {
  validateAccess,
  getTokenFromUrl,
  redirectToPhraze,
  ValidationResponse,
} from '../../services/embeddedApi';

type LoadingState = 'validating' | 'loading_video' | 'ready' | 'error';

interface ErrorInfo {
  code: string;
  message: string;
  redirectUrl?: string;
}

const EmbeddedEditorPage: React.FC = () => {
  const [loadingState, setLoadingState] = useState<LoadingState>('validating');
  const [error, setError] = useState<ErrorInfo | null>(null);
  const [tokenData, setTokenData] = useState<ValidationResponse | null>(null);
  const [videoReady, setVideoReady] = useState(false);

  // Get token from URL on mount
  const token = getTokenFromUrl();

  const validateAndLoad = useCallback(async () => {
    console.log('[EmbeddedEditor] Starting validation, token:', token ? 'present' : 'missing');

    if (!token) {
      setError({
        code: 'TOKEN_MISSING',
        message: 'No authentication token provided in URL. Please access this page with a valid token parameter.',
      });
      setLoadingState('error');
      // Don't auto-redirect - let user see the error
      return;
    }

    try {
      setLoadingState('validating');
      console.log('[EmbeddedEditor] Calling validateAccess...');

      // Validate token with backend
      const validation = await validateAccess(token);
      console.log('[EmbeddedEditor] Validation response:', validation);

      if (!validation.valid) {
        setError({
          code: 'VALIDATION_FAILED',
          message: 'Access validation failed. The token may be invalid or expired.',
        });
        setLoadingState('error');
        // Don't auto-redirect - let user see the error
        return;
      }

      setTokenData(validation);
      setLoadingState('loading_video');

      // Pre-check video URL accessibility (skip CORS issues)
      if (validation.video_url) {
        console.log('[EmbeddedEditor] Video URL:', validation.video_url);
      }

      setVideoReady(true);
      setLoadingState('ready');
      console.log('[EmbeddedEditor] Ready to show editor');

    } catch (err: any) {
      console.error('[EmbeddedEditor] Validation error:', err);

      // Extract error info from response
      const errorDetail = err.response?.data?.detail;
      let errorMessage = 'Failed to connect to the server.';
      let errorCode = 'CONNECTION_ERROR';

      if (errorDetail && typeof errorDetail === 'object') {
        errorCode = errorDetail.error_code || 'UNKNOWN_ERROR';
        errorMessage = errorDetail.message || 'An error occurred';
      } else if (err.message) {
        errorMessage = err.message;
        if (err.message.includes('Network Error')) {
          errorMessage = 'Network error - cannot reach backend server. Check CORS settings or backend URL.';
        }
      }

      setError({
        code: errorCode,
        message: errorMessage,
        redirectUrl: errorDetail?.redirect_url,
      });

      setLoadingState('error');
      // Don't auto-redirect - let user see and debug the error
    }
  }, [token]);

  useEffect(() => {
    validateAndLoad();
  }, [validateAndLoad]);

  // Render loading screen
  if (loadingState === 'validating' || loadingState === 'loading_video') {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
        }}
      >
        <CircularProgress size={60} sx={{ color: '#0A47F2', mb: 3 }} />
        <Typography variant="h6" sx={{ color: '#4a5568', mb: 1 }}>
          {loadingState === 'validating' ? 'Validating access...' : 'Loading video...'}
        </Typography>
        <Typography variant="body2" sx={{ color: '#718096' }}>
          Please wait while we prepare your editor
        </Typography>
      </Box>
    );
  }

  // Render error screen
  if (loadingState === 'error' && error) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
          p: 4,
        }}
      >
        <Box
          sx={{
            backgroundColor: 'white',
            borderRadius: '16px',
            p: 4,
            maxWidth: 500,
            width: '100%',
            textAlign: 'center',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
          }}
        >
          <ErrorIcon sx={{ fontSize: 64, color: '#ef4444', mb: 2 }} />

          <Typography variant="h5" sx={{ color: '#1f2937', fontWeight: 600, mb: 1 }}>
            {error.code === 'TOKEN_EXPIRED' ? 'Session Expired' : 'Access Error'}
          </Typography>

          <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
            <Typography variant="body2">
              <strong>Error Code:</strong> {error.code}
            </Typography>
            <Typography variant="body2">{error.message}</Typography>
          </Alert>

          <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={validateAndLoad}
            >
              Try Again
            </Button>
            <Button
              variant="contained"
              sx={{
                backgroundColor: '#0A47F2',
                '&:hover': { backgroundColor: '#1D4ED8' },
              }}
              onClick={() => redirectToPhraze(undefined, tokenData?.callback_url)}
            >
              Return to Jobs
            </Button>
          </Box>

          <Typography variant="caption" sx={{ display: 'block', mt: 3, color: '#9ca3af' }}>
            If this problem persists, please contact support.
          </Typography>
        </Box>
      </Box>
    );
  }

  // Render editor when ready - choose between Normal or Pro based on subscription tier
  if (loadingState === 'ready' && tokenData && videoReady) {
    const isProUser = tokenData.is_pro_user;

    return (
      <Box sx={{ minHeight: '100vh', width: '100%' }}>
        {/* Render Pro Video Editor for pro/enterprise users */}
        {isProUser ? (
          <ProVideoEditor
            videoUrl={tokenData.video_url!}
            videoFile={null}
            embeddedMode={true}
            embeddedToken={token!}
            phrazeJobId={tokenData.job_id!}
            callbackUrl={tokenData.callback_url}
            onBack={() => redirectToPhraze(undefined, tokenData.callback_url)}
          />
        ) : (
          /* Render Normal Video Editor for free/normal users */
          <GhostCutVideoEditor
            videoUrl={tokenData.video_url!}
            videoFile={null}
            embeddedMode={true}
            embeddedToken={token!}
            phrazeJobId={tokenData.job_id!}
            callbackUrl={tokenData.callback_url}
            onBack={() => redirectToPhraze(undefined, tokenData.callback_url)}
          />
        )}
      </Box>
    );
  }

  // Fallback
  return null;
};

export default EmbeddedEditorPage;

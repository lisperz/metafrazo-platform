/**
 * Normal Video Editor Page - Entry point for basic text removal editing
 * Styled similarly to Pro Video Editor for consistency
 */

import React, { useState, useCallback } from 'react';
import { Box, Container, Card, Typography, Stepper, Step, StepLabel, Alert } from '@mui/material';
import VideoUpload from '../../components/VideoEditor/VideoUpload';
import GhostCutVideoEditor from '../../components/VideoEditor/GhostCutVideoEditor';
import ProConnector from './ProVideoEditorPage/components/ProConnector';
import ProStepIcon from './ProVideoEditorPage/components/ProStepIcon';

const steps = ['Upload Video', 'Add Effects', 'Process with AI'];

const VideoEditorPage: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVideoUpload = useCallback((file: File, url: string) => {
    setVideoFile(file);
    setVideoUrl(url);
    setActiveStep(1);
    setError(null);
  }, []);

  return (
    <Box sx={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
      width: '100%'
    }}>
      {activeStep === 0 && (
        <>
          {/* Hero Section */}
          <Box sx={{
            background: 'linear-gradient(135deg, rgba(24,144,255,0.9) 0%, rgba(16,108,199,0.9) 100%)',
            pt: 8, pb: 6, color: 'white'
          }}>
            <Container maxWidth="lg">
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h2" sx={{
                  fontWeight: 700,
                  fontSize: { xs: '2.5rem', md: '3.5rem' },
                  textShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  mb: 2,
                }}>
                  Video Text Inpainting
                </Typography>
                <Typography variant="h6" sx={{
                  mb: 4,
                  opacity: 0.9,
                  fontSize: { xs: '1rem', md: '1.25rem' },
                  fontWeight: 300
                }}>
                  Upload your video and remove text automatically using AI
                </Typography>
              </Box>
            </Container>
          </Box>

          {/* Main Content */}
          <Container maxWidth="lg" sx={{ py: 6 }}>
            {/* Progress Stepper */}
            <Card sx={{
              borderRadius: '16px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              mb: 4,
              overflow: 'hidden'
            }}>
              <Box sx={{
                background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.9) 100%)',
                p: 4
              }}>
                <Typography variant="h5" sx={{
                  fontWeight: 600,
                  mb: 3,
                  color: '#2d3748',
                  textAlign: 'center'
                }}>
                  Processing Steps
                </Typography>
                <Stepper
                  alternativeLabel
                  activeStep={activeStep}
                  connector={<ProConnector />}
                  sx={{ mb: 2 }}
                >
                  {steps.map((label, index) => (
                    <Step key={label}>
                      <StepLabel
                        StepIconComponent={ProStepIcon}
                        sx={{
                          '& .MuiStepLabel-label': {
                            fontWeight: 600,
                            color: index === activeStep ? '#1890ff' : '#718096',
                            fontSize: '0.95rem',
                            mt: 1
                          }
                        }}
                      >
                        {label}
                      </StepLabel>
                    </Step>
                  ))}
                </Stepper>
              </Box>
            </Card>

            {/* Error Display */}
            {error && (
              <Alert
                severity="error"
                sx={{
                  mb: 4,
                  borderRadius: '12px',
                  boxShadow: '0 4px 20px rgba(239,68,68,0.15)'
                }}
                onClose={() => setError(null)}
              >
                {error}
              </Alert>
            )}

            {/* Upload Area */}
            <Card sx={{
              borderRadius: '16px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              overflow: 'hidden'
            }}>
              <VideoUpload onUpload={handleVideoUpload} />
            </Card>

            {/* How it works section */}
            <Card sx={{
              borderRadius: '16px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              mt: 4,
              p: 4
            }}>
              <Typography variant="h5" sx={{ fontWeight: 600, mb: 3, color: '#2d3748' }}>
                How it works
              </Typography>
              <Box component="ol" sx={{ pl: 2, '& li': { mb: 1.5, color: '#4a5568' } }}>
                <li>Upload your video file (MP4, AVI, MOV, etc.)</li>
                <li>Our AI automatically detects and removes text from the video</li>
                <li>Optionally upload an audio file to perform AI lip-sync on your video</li>
                <li>Download your processed video with text removed and lip-sync applied</li>
              </Box>
              <Typography variant="body2" sx={{ mt: 3, color: '#718096' }}>
                Processing may take several minutes depending on video length and complexity.
              </Typography>
            </Card>
          </Container>
        </>
      )}

      {activeStep === 1 && videoUrl && videoFile && (
        <GhostCutVideoEditor
          videoUrl={videoUrl}
          videoFile={videoFile}
          onBack={() => setActiveStep(0)}
        />
      )}
    </Box>
  );
};

export default VideoEditorPage;

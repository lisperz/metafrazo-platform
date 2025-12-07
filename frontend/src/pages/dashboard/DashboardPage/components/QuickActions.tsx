/**
 * Quick Actions - Dashboard quick action buttons
 */

import React from 'react';
import { Card, CardContent, Typography, Box, Button, Chip } from '@mui/material';
import { VideoSettings, Star, History } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom fontWeight={600}>
          Quick Actions
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Button
            variant="contained"
            fullWidth
            startIcon={<VideoSettings />}
            onClick={() => navigate('/editor')}
            size="large"
          >
            Video Editor
          </Button>
          <Button
            variant="outlined"
            fullWidth
            startIcon={<Star />}
            onClick={() => navigate('/editor/pro')}
            sx={{
              borderColor: '#f59e0b',
              color: '#d97706',
              '&:hover': {
                borderColor: '#d97706',
                backgroundColor: 'rgba(245, 158, 11, 0.04)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              Pro Video Editor
              <Chip
                label="PRO"
                size="small"
                sx={{
                  height: 18,
                  fontSize: 10,
                  fontWeight: 700,
                  background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                  color: 'white',
                  '& .MuiChip-label': { px: 0.75 },
                }}
              />
            </Box>
          </Button>
          <Button
            variant="outlined"
            fullWidth
            startIcon={<History />}
            onClick={() => navigate('/history')}
          >
            Translation History
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

export default QuickActions;

/**
 * Recent Jobs - Display recent job history
 */

import React from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  IconButton,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle,
  Schedule,
  Error as ErrorIcon,
  PlayArrow,
  Refresh,
  VideoLibrary,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { JobData } from '../hooks/useDashboardData';

interface RecentJobsProps {
  jobs: JobData[];
  onRefresh: () => void;
}

const RecentJobs: React.FC<RecentJobsProps> = ({ jobs, onRefresh }) => {
  const navigate = useNavigate();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      case 'pending': return 'info';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle />;
      case 'processing': return <Schedule />;
      case 'failed': return <ErrorIcon />;
      case 'pending': return <Schedule />;
      default: return <Schedule />;
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" fontWeight={600}>
            Recent Jobs
          </Typography>
          <Box>
            <IconButton onClick={onRefresh} size="small">
              <Refresh />
            </IconButton>
            <Button
              variant="outlined"
              size="small"
              onClick={() => navigate('/history')}
              sx={{ ml: 1 }}
            >
              View All
            </Button>
          </Box>
        </Box>

        {jobs.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center', backgroundColor: 'grey.50' }}>
            <VideoLibrary sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No videos processed yet
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Start editing your first video with our AI-powered tools.
            </Typography>
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={() => navigate('/editor')}
            >
              Open Video Editor
            </Button>
          </Paper>
        ) : (
          <List>
            {jobs.map((job) => (
              <ListItem
                key={job.id}
                sx={{
                  border: 1,
                  borderColor: 'grey.200',
                  borderRadius: 1,
                  mb: 1,
                }}
                secondaryAction={
                  job.status === 'completed' ? (
                    <IconButton
                      edge="end"
                      onClick={() => window.open(job.output_url, '_blank')}
                    >
                      <PlayArrow />
                    </IconButton>
                  ) : null
                }
              >
                <ListItemIcon>
                  {getStatusIcon(job.status)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" noWrap>
                        {job.display_name || job.original_filename}
                      </Typography>
                      <Chip
                        label={job.status}
                        size="small"
                        color={getStatusColor(job.status) as any}
                        variant="outlined"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        Created: {new Date(job.created_at).toLocaleDateString()}
                      </Typography>
                      {job.progress !== undefined && job.status === 'processing' && (
                        <Box sx={{ mt: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={job.progress}
                            sx={{ height: 4, borderRadius: 2 }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {job.progress}% complete
                          </Typography>
                        </Box>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentJobs;

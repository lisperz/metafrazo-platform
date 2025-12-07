import React from 'react';
import { TableRow, TableCell, Box, Typography, Chip, LinearProgress, IconButton, Tooltip } from '@mui/material';
import { VideoLibrary, PlayArrow, Download, MoreVert } from '@mui/icons-material';
import { Job } from '../types';
import { formatFileSize, formatDateInChicagoTime, getStatusColor } from '../utils/formatters';

interface JobTableRowProps {
  job: Job;
  onMenuOpen: (event: React.MouseEvent<HTMLElement>, job: Job) => void;
}

const JobTableRow: React.FC<JobTableRowProps> = ({ job, onMenuOpen }) => {
  const { date, time } = formatDateInChicagoTime(job.created_at);

  return (
    <TableRow hover>
      <TableCell sx={{ minWidth: 280, maxWidth: 400 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <VideoLibrary sx={{ mr: 2, color: 'grey.400', flexShrink: 0 }} />
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Tooltip title={job.display_name || job.original_filename} placement="top">
                <Typography
                  variant="subtitle2"
                  sx={{
                    wordBreak: 'break-word',
                    overflowWrap: 'break-word',
                  }}
                >
                  {job.display_name || job.original_filename}
                </Typography>
              </Tooltip>
              {job.is_pro_job && (
                <Chip
                  label="PRO"
                  size="small"
                  sx={{
                    height: 18,
                    fontSize: '10px',
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                    color: 'white',
                    flexShrink: 0,
                    '& .MuiChip-label': {
                      px: 1,
                    },
                  }}
                />
              )}
            </Box>
            <Typography variant="body2" color="text.secondary">
              {formatFileSize(job.file_size || 0)}
              {job.is_pro_job && job.segments_data?.total_segments && (
                <>
                  {' '}
                  • {job.segments_data.total_segments} segment{job.segments_data.total_segments > 1 ? 's' : ''}
                </>
              )}
            </Typography>
          </Box>
        </Box>
      </TableCell>
      <TableCell>
        <Chip label={job.status} size="small" color={getStatusColor(job.status)} variant="outlined" />
      </TableCell>
      <TableCell sx={{ minWidth: 120 }}>
        {job.status === 'processing' && job.progress !== undefined ? (
          <Box>
            <LinearProgress variant="determinate" value={job.progress} sx={{ mb: 0.5, height: 6, borderRadius: 3 }} />
            <Typography variant="caption" color="text.secondary">
              {job.progress}%
            </Typography>
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {job.status === 'completed' ? '100%' : '-'}
          </Typography>
        )}
      </TableCell>
      <TableCell>
        <Typography variant="body2">{job.credits_used || job.estimated_credits || '-'}</Typography>
      </TableCell>
      <TableCell>
        <Typography variant="body2">{date}</Typography>
        <Typography variant="caption" color="text.secondary">
          {time}
        </Typography>
      </TableCell>
      <TableCell align="right">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {job.status === 'completed' && job.output_url && (
            <>
              <Tooltip title="View Result">
                <IconButton size="small" onClick={() => window.open(job.output_url, '_blank')}>
                  <PlayArrow />
                </IconButton>
              </Tooltip>
              <Tooltip title="Download">
                <IconButton size="small" onClick={() => window.open(`${job.output_url}?download=1`, '_blank')}>
                  <Download />
                </IconButton>
              </Tooltip>
            </>
          )}
          <IconButton size="small" onClick={(e) => onMenuOpen(e, job)}>
            <MoreVert />
          </IconButton>
        </Box>
      </TableCell>
    </TableRow>
  );
};

export default JobTableRow;

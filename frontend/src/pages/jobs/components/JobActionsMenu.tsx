import React from 'react';
import { Menu, MenuList, MenuItem, ListItemIcon, ListItemText, alpha, useTheme } from '@mui/material';
import { Download, Stop, Delete } from '@mui/icons-material';
import { Job } from '../types';

interface JobActionsMenuProps {
  anchorEl: HTMLElement | null;
  selectedJob: Job | null;
  onClose: () => void;
  onCancelJob: (jobId: string) => void;
  onDeleteJob: (jobId: string) => void;
  isCancelling: boolean;
  isDeleting: boolean;
}

// Terminal states where jobs can be deleted (handles both American and British spellings)
const DELETABLE_STATUSES = ['completed', 'failed', 'cancelled', 'canceled'];

const JobActionsMenu: React.FC<JobActionsMenuProps> = ({
  anchorEl,
  selectedJob,
  onClose,
  onCancelJob,
  onDeleteJob,
  isCancelling,
  isDeleting,
}) => {
  const theme = useTheme();

  const handleDownload = () => {
    if (selectedJob?.output_url) {
      window.open(selectedJob.output_url, '_blank');
      onClose();
    }
  };

  const handleCancel = () => {
    if (selectedJob?.id) {
      onCancelJob(selectedJob.id);
    }
  };

  const handleDelete = () => {
    if (selectedJob?.id) {
      onDeleteJob(selectedJob.id);
    }
  };

  // Check if the job can be deleted (terminal states)
  const canDelete = selectedJob?.status && DELETABLE_STATUSES.includes(selectedJob.status);

  // Check if there are any actions available
  const hasDownload = selectedJob?.status === 'completed' && selectedJob?.output_url;
  const hasCancel = selectedJob?.status === 'processing';
  const hasActions = hasDownload || hasCancel || canDelete;

  return (
    <Menu
      anchorEl={anchorEl}
      open={Boolean(anchorEl)}
      onClose={onClose}
      PaperProps={{
        sx: {
          minWidth: 160,
          borderRadius: 2,
        },
      }}
    >
      <MenuList sx={{ py: 0.5 }}>
        {hasDownload && (
          <MenuItem onClick={handleDownload} sx={{ borderRadius: 1, mx: 0.5 }}>
            <ListItemIcon>
              <Download fontSize="small" />
            </ListItemIcon>
            <ListItemText>Download Video</ListItemText>
          </MenuItem>
        )}
        {hasCancel && (
          <MenuItem
            onClick={handleCancel}
            disabled={isCancelling}
            sx={{ borderRadius: 1, mx: 0.5 }}
          >
            <ListItemIcon>
              <Stop fontSize="small" />
            </ListItemIcon>
            <ListItemText>{isCancelling ? 'Cancelling...' : 'Cancel Job'}</ListItemText>
          </MenuItem>
        )}
        {canDelete && (
          <MenuItem
            onClick={handleDelete}
            disabled={isDeleting}
            sx={{
              borderRadius: 1,
              mx: 0.5,
              color: 'error.main',
              '&:hover': {
                backgroundColor: alpha(theme.palette.error.main, 0.08),
              },
            }}
          >
            <ListItemIcon>
              <Delete fontSize="small" sx={{ color: 'error.main' }} />
            </ListItemIcon>
            <ListItemText>{isDeleting ? 'Deleting...' : 'Delete Job'}</ListItemText>
          </MenuItem>
        )}
        {!hasActions && (
          <MenuItem disabled sx={{ borderRadius: 1, mx: 0.5 }}>
            <ListItemText sx={{ color: 'text.secondary' }}>No actions available</ListItemText>
          </MenuItem>
        )}
      </MenuList>
    </Menu>
  );
};

export default JobActionsMenu;

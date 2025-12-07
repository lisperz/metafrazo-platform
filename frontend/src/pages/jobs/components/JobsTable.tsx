import React from 'react';
import {
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
} from '@mui/material';
import { Job } from '../types';
import JobTableRow from './JobTableRow';

interface JobsTableProps {
  jobs: Job[];
  totalJobs: number;
  page: number;
  rowsPerPage: number;
  onPageChange: (event: unknown, newPage: number) => void;
  onRowsPerPageChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onMenuOpen: (event: React.MouseEvent<HTMLElement>, job: Job) => void;
}

const JobsTable: React.FC<JobsTableProps> = ({
  jobs,
  totalJobs,
  page,
  rowsPerPage,
  onPageChange,
  onRowsPerPageChange,
  onMenuOpen,
}) => {
  return (
    <Card>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Video</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Credits</TableCell>
              <TableCell>Created</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <JobTableRow key={job.id} job={job} onMenuOpen={onMenuOpen} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={totalJobs}
        page={page}
        onPageChange={onPageChange}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={onRowsPerPageChange}
        rowsPerPageOptions={[5, 10, 25, 50]}
      />
    </Card>
  );
};

export default JobsTable;

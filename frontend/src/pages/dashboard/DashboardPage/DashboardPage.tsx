/**
 * Dashboard Page - Main user dashboard
 */

import React from 'react';
import { Container, Typography, Box, Alert, Button, Grid } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../contexts/AuthContext';
import { useDashboardData } from './hooks/useDashboardData';
import StatsCards from './components/StatsCards';
import QuickActions from './components/QuickActions';
import CreditUsage from './components/CreditUsage';
import RecentJobs from './components/RecentJobs';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    stats,
    recentJobs,
    refetchJobs,
  } = useDashboardData();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom fontWeight={600}>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome back, {user?.first_name || 'User'}! Here's your account overview.
        </Typography>
      </Box>

      {/* User Subscription Alert */}
      <Alert severity="info" sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography>
            You're on the <strong>{user?.subscription_tier || 'Free'}</strong> plan with{' '}
            <strong>{user?.credits_balance || 0}</strong> credits remaining.
          </Typography>
          <Button variant="outlined" size="small" onClick={() => navigate('/settings')}>
            Upgrade Plan
          </Button>
        </Box>
      </Alert>

      {/* Stats Cards */}
      <StatsCards stats={stats} creditsBalance={user?.credits_balance || 0} />

      {/* Main Content Grid */}
      <Grid container spacing={4}>
        {/* Quick Actions & Credit Usage */}
        <Grid item xs={12} md={4}>
          <QuickActions />
          <CreditUsage stats={stats} />
        </Grid>

        {/* Recent Jobs */}
        <Grid item xs={12} md={8}>
          <RecentJobs jobs={recentJobs} onRefresh={() => refetchJobs()} />
        </Grid>
      </Grid>
    </Container>
  );
};

export default DashboardPage;

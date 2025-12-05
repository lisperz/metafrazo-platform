import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Box, IconButton } from '@mui/material';
import { Menu as MenuIcon } from '@mui/icons-material';

import { useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Navbar from './components/Layout/Navbar';
import Sidebar from './components/Layout/Sidebar';
import LoadingScreen from './components/Common/LoadingScreen';
import ErrorBoundary from './components/Common/ErrorBoundary';

// Pages - Refactored organized imports
import HomePage from './pages/dashboard/HomePage';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import UploadPage from './pages/upload/UploadPage';
import JobsPage from './pages/jobs/JobsPage';
import SettingsPage from './pages/admin/SettingsPage';
import AdminPage from './pages/admin/AdminPage';
import VideoInpaintingPage from './pages/video/VideoInpaintingPage';
import SimpleVideoInpaintingPage from './pages/video/SimpleVideoInpaintingPage';
import ProVideoEditorPage from './pages/video/ProVideoEditorPage';
import VideoEditorPage from './pages/video/VideoEditorPage';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  
  // Check localStorage as backup
  const token = localStorage.getItem('access_token');
  
  if (loading) {
    return <LoadingScreen />;
  }
  
  if (!user && !token) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Public Route Component (redirect if already authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <LoadingScreen />;
  }
  
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Layout Component
const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  
  // For simple video inpainting page and video editor, render without layout for full-screen experience
  const fullScreenRoutes = ['/simple', '/editor', '/editor/pro'];
  console.log('[Layout] Current pathname:', location.pathname);
  console.log('[Layout] Should use full-screen:', fullScreenRoutes.includes(location.pathname));
  
  if (fullScreenRoutes.includes(location.pathname)) {
    return <>{children}</>;
  }
  
  // Show sidebar layout for authenticated users
  const shouldShowSidebar = user;
  
  if (!shouldShowSidebar) {
    return <>{children}</>;
  }
  
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar 
        open={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
      />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minHeight: '100vh',
          backgroundColor: 'background.default',
          position: 'relative',
        }}
      >
        {/* Mobile menu button */}
        <Box
          sx={{
            display: { xs: 'block', sm: 'none' },
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 1,
          }}
        >
          <IconButton
            onClick={() => setSidebarOpen(true)}
            sx={{
              backgroundColor: 'background.paper',
              boxShadow: 1,
              '&:hover': {
                backgroundColor: 'background.paper',
              },
            }}
          >
            <MenuIcon />
          </IconButton>
        </Box>
        {children}
      </Box>
    </Box>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <Layout>
        <Routes>
        {/* Public Routes */}
        <Route
          path="/"
          element={<Navigate to="/login" replace />}
        />
        <Route 
          path="/simple" 
          element={<SimpleVideoInpaintingPage />}
        />
        <Route 
          path="/login" 
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          } 
        />
        <Route 
          path="/register" 
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          } 
        />
        
        {/* Dashboard - Wrapped with ErrorBoundary for debugging */}
        <Route
          path="/dashboard"
          element={
            <ErrorBoundary>
              <DashboardPage />
            </ErrorBoundary>
          }
        />
        <Route 
          path="/upload" 
          element={
            <ProtectedRoute>
              <UploadPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/jobs" 
          element={
            <ProtectedRoute>
              <JobsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute>
              <AdminPage />
            </ProtectedRoute>
          } 
        />
        
        {/* Video Inpainting - Public Route for testing */}
        <Route 
          path="/inpaint" 
          element={<VideoInpaintingPage />} 
        />
        
        {/* Video Editor Route - Protected */}
        <Route
          path="/editor"
          element={
            <ProtectedRoute>
              <VideoEditorPage />
            </ProtectedRoute>
          }
        />

        {/* Pro Video Editor Route - Protected */}
        <Route
          path="/editor/pro"
          element={
            <ProtectedRoute>
              <ProVideoEditorPage />
            </ProtectedRoute>
          }
        />
        
        {/* History Route */}
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <JobsPage />
            </ProtectedRoute>
          }
        />
        <Route 
          path="/credits" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/docs" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/faq" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/support" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        
        {/* Fallback Route */}
        <Route 
          path="*" 
          element={<Navigate to="/dashboard" replace />} 
        />
        </Routes>
      </Layout>
    </ThemeProvider>
  );
};

export default App;
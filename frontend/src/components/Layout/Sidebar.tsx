import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Avatar,
  IconButton,
  useTheme,
  alpha,
  Chip,
} from '@mui/material';
import {
  Translate,
  History,
  CreditCard,
  Description,
  LiveHelp,
  ContactSupport,
  ExpandMore,
  AccountCircle,
  VideoSettings,
  Star,
} from '@mui/icons-material';
import ThemeToggle from '../Common/ThemeToggle';
import { useNavigate, useLocation } from 'react-router-dom';

import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  section: string;
  badge?: string;
  requiresPro?: boolean;
}

const DRAWER_WIDTH = 280;

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const theme = useTheme();

  const menuItems: MenuItem[] = [
    {
      id: 'editor',
      label: 'Video Editor',
      icon: <VideoSettings />,
      path: '/editor',
      section: 'Translate',
    },
    {
      id: 'pro-editor',
      label: 'Pro Video Editor',
      icon: <Star />,
      path: '/editor/pro',
      section: 'Translate',
      badge: 'PRO',
      requiresPro: true,
    },
    {
      id: 'history',
      label: 'Translation History',
      icon: <History />,
      path: '/history',
      section: 'Translate',
    },
    {
      id: 'credits',
      label: 'Credits',
      icon: <CreditCard />,
      path: '/credits',
      section: 'Credits',
    },
    {
      id: 'documentation',
      label: 'Documentation',
      icon: <Description />,
      path: '/docs',
      section: 'Help & Support',
    },
    {
      id: 'faq',
      label: 'FAQ',
      icon: <LiveHelp />,
      path: '/faq',
      section: 'Help & Support',
    },
    {
      id: 'support',
      label: 'Support',
      icon: <ContactSupport />,
      path: '/support',
      section: 'Help & Support',
    },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    onClose();
  };

  const sections = ['Translate', 'Credits', 'Help & Support'];

  const drawer = (
    <Box 
      sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Header with Logo and User Info */}
      <Box sx={{ p: 3 }} role="banner">
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              backgroundColor: 'primary.main',
              borderRadius: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mr: 2,
            }}
          >
            <Typography 
              sx={{ 
                color: 'white', 
                fontWeight: 'bold', 
                fontSize: 16 
              }}
            >
              M
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
              MetaFrazo
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {user?.credits_balance || 5} credits
            </Typography>
          </Box>
          <ThemeToggle size="small" />
        </Box>

        {/* Navigation Sections */}
        <Box sx={{ mb: 4 }}>
          {sections.map((section) => (
            <Box key={section} sx={{ mb: 3 }}>
              <Typography
                variant="overline"
                id={`nav-section-${section.replace(/\s+/g, '-').toLowerCase()}`}
                sx={{
                  color: 'text.secondary',
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: 1,
                  ml: 1,
                  mb: 1,
                  display: 'block',
                }}
                role="group"
                aria-label={`${section} navigation section`}
              >
                {section}
              </Typography>
              <List 
                sx={{ py: 0 }}
                role="menu"
                aria-labelledby={`nav-section-${section.replace(/\s+/g, '-').toLowerCase()}`}
              >
                {menuItems
                  .filter((item) => item.section === section)
                  .map((item) => {
                    const isActive = location.pathname === item.path;
                    
                    return (
                      <ListItem key={item.id} disablePadding>
                        <ListItemButton
                          selected={isActive}
                          onClick={() => handleNavigation(item.path)}
                          role="menuitem"
                          aria-label={`Navigate to ${item.label}`}
                          tabIndex={0}
                          sx={{
                            borderRadius: 2,
                            mx: 1,
                            mb: 0.5,
                            minHeight: 40,
                            '&:hover': {
                              backgroundColor: alpha(theme.palette.primary.main, 0.04),
                            },
                            '&.Mui-selected': {
                              backgroundColor: alpha(theme.palette.primary.main, 0.12),
                              color: 'primary.main',
                              '&:hover': {
                                backgroundColor: alpha(theme.palette.primary.main, 0.16),
                              },
                            },
                            '&:focus': {
                              outline: `2px solid ${theme.palette.primary.main}`,
                              outlineOffset: 2,
                            },
                          }}
                        >
                          <ListItemIcon
                            sx={{
                              minWidth: 36,
                              color: isActive ? 'primary.main' : 'text.secondary',
                            }}
                          >
                            {item.icon}
                          </ListItemIcon>
                          <ListItemText
                            primary={
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <span>{item.label}</span>
                                {item.badge && (
                                  <Chip
                                    label={item.badge}
                                    size="small"
                                    sx={{
                                      height: 18,
                                      fontSize: 10,
                                      fontWeight: 700,
                                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                                      color: 'white',
                                      '& .MuiChip-label': {
                                        px: 0.75,
                                      },
                                    }}
                                  />
                                )}
                              </Box>
                            }
                            primaryTypographyProps={{
                              fontSize: 14,
                              fontWeight: isActive ? 600 : 400,
                            }}
                          />
                        </ListItemButton>
                      </ListItem>
                    );
                  })}
              </List>
            </Box>
          ))}
        </Box>
      </Box>

      {/* Account Section at Bottom */}
      <Box 
        sx={{ 
          mt: 'auto', 
          p: 2, 
          borderTop: `1px solid ${theme.palette.divider}` 
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Avatar
            sx={{
              width: 32,
              height: 32,
              backgroundColor: alpha(theme.palette.text.secondary, 0.1),
              color: 'text.secondary',
              fontSize: 14,
              mr: 2,
            }}
          >
            {user?.first_name?.charAt(0) || 'A'}
          </Avatar>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography 
              variant="body2" 
              sx={{ fontWeight: 500, lineHeight: 1.2 }}
            >
              Account
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                display: 'block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: 140,
              }}
            >
              {user?.email || 'user@example.com'}
            </Typography>
          </Box>
          <IconButton size="small" sx={{ ml: 1 }}>
            <ExpandMore fontSize="small" />
          </IconButton>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
    >
      {/* Mobile drawer */}
      <Drawer
        variant="temporary"
        open={open}
        onClose={onClose}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            backgroundColor: 'background.paper',
            borderRight: `1px solid ${theme.palette.divider}`,
          },
        }}
      >
        {drawer}
      </Drawer>
      
      {/* Desktop drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
            backgroundColor: 'background.paper',
            borderRight: `1px solid ${theme.palette.divider}`,
            position: 'fixed',
            height: '100%',
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};

export default Sidebar;
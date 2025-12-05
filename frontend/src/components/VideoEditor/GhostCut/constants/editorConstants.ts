/**
 * Constants for GhostCut Video Editor
 */

import { EffectType } from '../types';
import { getApiBaseUrl } from '../../../../services/api';

// Effect Colors
export const EFFECT_COLORS: Record<EffectType, string> = {
  erasure: '#5B8FF9',
  protection: '#5AD8A6',
  text: '#5D7092',
};

// Effect Hover Colors
export const EFFECT_HOVER_COLORS: Record<EffectType, string> = {
  erasure: '#40a9ff',
  protection: '#52c41a',
  text: '#434c5e',
};

// Effect Labels
export const EFFECT_LABELS: Record<EffectType, string> = {
  erasure: 'Erasure Area',
  protection: 'Protection Area',
  text: 'Erase Text',
};

// Effect Background Colors (with transparency)
export const EFFECT_BG_COLORS: Record<EffectType, string> = {
  erasure: 'rgba(91, 143, 249, 0.15)',
  protection: 'rgba(90, 216, 166, 0.15)',
  text: 'rgba(93, 112, 146, 0.15)',
};

// Effect Border Colors
export const EFFECT_BORDER_COLORS: Record<EffectType, string> = {
  erasure: 'rgba(91, 143, 249, 0.1)',
  protection: 'rgba(90, 216, 166, 0.1)',
  text: 'rgba(93, 112, 146, 0.1)',
};

// Timeline Configuration
export const TIMELINE_CONFIG = {
  THUMBNAIL_COUNT: 30,
  THUMBNAIL_WIDTH: 120,
  THUMBNAIL_HEIGHT: 68,
  THUMBNAIL_QUALITY: 0.7,
  DEFAULT_EFFECT_DURATION: 5, // seconds
  MIN_EFFECT_DURATION: 0.1, // seconds
  TIME_MARK_COUNT: 11,
  ZOOM_MIN: 0.5,
  ZOOM_MAX: 5,
  ZOOM_STEP: 0.1,
  ZOOM_DEFAULT: 1,
  TRACK_HEIGHT: 40, // pixels
  TRACK_MARGIN: 5, // pixels
  EFFECT_HEIGHT: 30, // pixels
} as const;

// UI Configuration
export const UI_CONFIG = {
  CORNER_DOT_SIZE: 8,
  CORNER_DOT_BORDER: 2,
  DELETE_BUTTON_SIZE: 24,
  DELETE_BUTTON_OFFSET: 30,
  HANDLE_WIDTH: 6,
  HANDLE_OPACITY_DEFAULT: 0,
  HANDLE_OPACITY_HOVER: 1,
  TIMELINE_INDICATOR_WIDTH: 2,
  DRAGGABLE_HANDLE_WIDTH: 8,
} as const;

/**
 * API endpoint constants
 * Uses dynamic base URL to support both local development and production
 *
 * Backend route mappings:
 * - SYNC_PROCESS: /api/v1/video-editors/sync-process (simple lip-sync with single audio)
 * - DIRECT_PROCESS: /api/v1/jobs/direct-process (text removal only, GhostCut)
 */
export const getApiEndpoints = () => {
  const baseUrl = getApiBaseUrl();
  return {
    SYNC_PROCESS: `${baseUrl}/video-editors/sync-process`,
    DIRECT_PROCESS: `${baseUrl}/jobs/direct-process`,
    AUTH_ME: `${baseUrl}/auth/me`,
    AUTH_LOGIN: `${baseUrl}/auth/login`,
  };
};

// For backward compatibility - will be evaluated at runtime
export const API_ENDPOINTS = {
  get SYNC_PROCESS() { return getApiEndpoints().SYNC_PROCESS; },
  get DIRECT_PROCESS() { return getApiEndpoints().DIRECT_PROCESS; },
  get AUTH_ME() { return getApiEndpoints().AUTH_ME; },
  get AUTH_LOGIN() { return getApiEndpoints().AUTH_LOGIN; },
};

// Auth Configuration
export const AUTH_CONFIG = {
  DEMO_EMAIL: 'demo@example.com',
  DEMO_PASSWORD: 'demo123',
  TOKEN_KEY: 'access_token',
  REFRESH_TOKEN_KEY: 'refresh_token',
} as const;

// Video Player Configuration
export const VIDEO_CONFIG = {
  PROGRESS_INTERVAL: 50, // milliseconds
  READY_DELAY: 100, // milliseconds
  RESIZE_DELAY: 100, // milliseconds
  MAX_VIDEO_WIDTH: 900, // pixels
} as const;

// Navigation Delays
export const NAVIGATION_DELAYS = {
  AFTER_SUBMIT: 2000, // milliseconds
} as const;

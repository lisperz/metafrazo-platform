/**
 * Constants for Pro Video Editor
 *
 * This module contains all constant values, color mappings, and configuration
 * used throughout the Pro Video Editor.
 */

import { EffectType } from '../types';
import { getApiBaseUrl } from '../../../../services/api';

/**
 * Color mapping for different effect types
 */
export const EFFECT_COLORS: Record<EffectType, string> = {
  erasure: '#5B8FF9',
  protection: '#5AD8A6',
  text: '#5D7092',
} as const;

/**
 * Human-readable labels for effect types
 */
export const EFFECT_LABELS: Record<EffectType, string> = {
  erasure: 'Erasure Area',
  protection: 'Protection Area',
  text: 'Erase Text',
} as const;

/**
 * Hover state colors for effects (lighter variants)
 */
export const EFFECT_HOVER_COLORS: Record<EffectType, string> = {
  erasure: '#40a9ff',
  protection: '#52c41a',
  text: '#434c5e',
} as const;

/**
 * Timeline-specific constants
 */
export const TIMELINE_CONSTANTS = {
  /** Number of video thumbnails to generate */
  THUMBNAIL_COUNT: 30,
  /** Thumbnail width in pixels */
  THUMBNAIL_WIDTH: 120,
  /** Thumbnail height in pixels */
  THUMBNAIL_HEIGHT: 68,
  /** JPEG quality for thumbnails (0-1) */
  THUMBNAIL_QUALITY: 0.7,
  /** Minimum effect duration in seconds */
  MIN_EFFECT_DURATION: 0.1,
  /** Default effect duration in seconds */
  DEFAULT_EFFECT_DURATION: 5,
  /** Timeline zoom range */
  ZOOM_MIN: 0.5,
  ZOOM_MAX: 5,
  ZOOM_DEFAULT: 1,
  ZOOM_STEP: 0.1,
  /** Timeline track height in pixels */
  TRACK_HEIGHT: 40,
  /** Track vertical spacing in pixels */
  TRACK_SPACING: 5,
  /** Effect bar height in pixels */
  EFFECT_BAR_HEIGHT: 30,
  /** Progress update interval in milliseconds */
  PROGRESS_INTERVAL: 50,
  /** Video bounds calculation delay in milliseconds */
  BOUNDS_CALCULATION_DELAY: 100,
  /** Maximum number of segments allowed */
  MAX_SEGMENTS: 10,
} as const;

/**
 * API endpoint constants
 * Uses dynamic base URL to support both local development and production
 */
export const getApiEndpoints = () => {
  const baseUrl = getApiBaseUrl();
  return {
    PRO_SYNC_PROCESS: `${baseUrl}/video-editors/pro-sync-process`,
    AUTH_ME: `${baseUrl}/auth/me`,
    AUTH_LOGIN: `${baseUrl}/auth/login`,
  };
};

// For backward compatibility - will be evaluated at runtime
export const API_ENDPOINTS = {
  get PRO_SYNC_PROCESS() { return getApiEndpoints().PRO_SYNC_PROCESS; },
  get AUTH_ME() { return getApiEndpoints().AUTH_ME; },
  get AUTH_LOGIN() { return getApiEndpoints().AUTH_LOGIN; },
};

/**
 * Demo account credentials for auto-login
 */
export const DEMO_CREDENTIALS = {
  email: 'demo@example.com',
  password: 'demo123',
} as const;

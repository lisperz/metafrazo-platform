/**
 * Embedded Editor API service for phraze.so integration
 * Handles communication with the embedded editor backend endpoints
 */

import axios, { AxiosInstance } from 'axios';
import { getApiBaseUrl } from './api';

// Types for embedded API
export interface ValidationResponse {
  valid: boolean;
  user_id: string | null;
  job_id: string | null;
  video_url: string | null;
  callback_url: string | null;
  subscription_tier: string | null;
  is_pro_user: boolean;
  message: string;
}

export interface ProcessRequest {
  processing_type: 'text_removal' | 'lip_sync' | 'both';
  target_language?: string;
  audio_url?: string;
  segments?: any[];
}

export interface ProcessResponse {
  job_id: string;
  phraze_job_id: string;
  status: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  phraze_job_id: string;
  status: string;
  progress: number;
  message: string | null;
  output_url: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  redirect_url?: string;
  job_id?: string;
  timestamp: string;
}

/**
 * Get backend URL from query parameter or use default
 * Allows testing Railway frontend with local backend
 */
export const getBackendUrlFromParams = (): string | null => {
  const params = new URLSearchParams(window.location.search);
  return params.get('backend_url');
};

/**
 * Get the embedded API base URL
 * Uses backend_url query param if provided, otherwise uses default
 */
const getEmbeddedApiBaseUrl = (): string => {
  const overrideUrl = getBackendUrlFromParams();
  if (overrideUrl) {
    // Remove trailing slash and ensure /api/v1/embedded path
    const cleanUrl = overrideUrl.replace(/\/$/, '');
    return `${cleanUrl}/api/v1/embedded`;
  }
  return `${getApiBaseUrl()}/embedded`;
};

// Create axios instance factory for embedded API (no auth interceptors)
const createEmbeddedApi = (): AxiosInstance => {
  const baseURL = getEmbeddedApiBaseUrl();
  console.log('[EmbeddedAPI] Using backend URL:', baseURL);

  return axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

// Lazy-initialized instance (created on first use to get correct URL params)
let embeddedApiInstance: AxiosInstance | null = null;

const getEmbeddedApi = (): AxiosInstance => {
  if (!embeddedApiInstance) {
    embeddedApiInstance = createEmbeddedApi();
  }
  return embeddedApiInstance;
};

/**
 * Validate access token from phraze.so
 */
export const validateAccess = async (token: string): Promise<ValidationResponse> => {
  const response = await getEmbeddedApi().get<ValidationResponse>('/validate', {
    params: { token }
  });
  return response.data;
};

/**
 * Start video processing
 */
export const processVideo = async (
  token: string,
  config: ProcessRequest
): Promise<ProcessResponse> => {
  const response = await getEmbeddedApi().post<ProcessResponse>(
    '/process',
    config,
    { params: { token } }
  );
  return response.data;
};

/**
 * Get job status
 */
export const getJobStatus = async (
  jobId: string,
  token: string
): Promise<JobStatusResponse> => {
  const response = await getEmbeddedApi().get<JobStatusResponse>(
    `/status/${jobId}`,
    { params: { token } }
  );
  return response.data;
};

/**
 * Cancel job
 */
export const cancelJob = async (
  jobId: string,
  token: string
): Promise<{ job_id: string; status: string; message: string }> => {
  const response = await getEmbeddedApi().post(
    `/cancel/${jobId}`,
    {},
    { params: { token } }
  );
  return response.data;
};

/**
 * Parse token from URL query parameters
 */
export const getTokenFromUrl = (): string | null => {
  const params = new URLSearchParams(window.location.search);
  return params.get('token');
};

/**
 * Redirect to phraze.so with optional error code
 */
export const redirectToPhraze = (errorCode?: string): void => {
  const baseUrl = 'https://phraze.so';
  if (errorCode) {
    window.location.href = `${baseUrl}/dashboard?error=${errorCode}`;
  } else {
    window.location.href = baseUrl;
  }
};

export default getEmbeddedApi;

import axios, { AxiosResponse } from 'axios';

// Base API configuration
// Determine if we're running on Railway production
const isRailwayProduction = typeof window !== 'undefined' &&
  window.location.hostname.includes('railway.app');

// Use environment variable if set and not empty, otherwise detect environment
const API_BASE_URL = (process.env.REACT_APP_API_URL && process.env.REACT_APP_API_URL.length > 0)
  ? process.env.REACT_APP_API_URL
  : isRailwayProduction
    ? 'https://backend-production-268a.up.railway.app/api/v1'
    : '/api/v1';

// Export for use in other parts of the app (e.g., Pro Video Editor)
export const getApiBaseUrl = (): string => API_BASE_URL;

// Debug logging for production troubleshooting
console.log('[API] Configuration:', {
  hostname: typeof window !== 'undefined' ? window.location.hostname : 'SSR',
  isRailwayProduction,
  envVar: process.env.REACT_APP_API_URL,
  finalUrl: API_BASE_URL
});

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  email_verified: boolean;
  subscription_tier: string;
  credits_balance: number;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  company?: string;
}

export interface VideoJob {
  id: string;
  user_id: string;
  original_filename: string;
  display_name?: string;
  status: string;
  progress_percentage: number;
  progress_message?: string;
  processing_config: any;
  estimated_credits?: number;
  actual_credits_used?: number;
  video_duration_seconds?: number;
  video_resolution?: string;
  queued_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  created_at: string;
  is_pro_job?: boolean;
  segments_data?: {
    segments?: any[];
    total_segments?: number;
  };
  output_url?: string;
  file_size?: number;
  duration?: number;
  credits_used?: number;
  progress?: number;
}

export interface JobListResponse {
  jobs: VideoJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreditTransaction {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  description?: string;
  created_at: string;
}

export interface SubscriptionTier {
  id: number;
  name: string;
  display_name: string;
  description?: string;
  price_monthly: number;
  credits_per_month: number;
  max_video_length_seconds: number;
  max_file_size_mb: number;
  max_concurrent_jobs: number;
  features: string[];
}

// Auth API
const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await api.post('/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await api.post('/auth/register', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/auth/logout');
  },

  getCurrentUser: async (): Promise<User> => {
    const response: AxiosResponse<User> = await api.get('/auth/me');
    return response.data;
  },

  refreshToken: async (refreshToken: string): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },
};

// Jobs API
const jobsApi = {
  getJobs: async (page = 1, pageSize = 20, statusFilter?: string): Promise<JobListResponse> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (statusFilter) {
      params.append('status_filter', statusFilter);
    }

    const response: AxiosResponse<JobListResponse> = await api.get(`/jobs?${params}`);
    return response.data;
  },

  getUserJobs: async (params: { limit?: number; offset?: number; search?: string; status?: string } = {}): Promise<any> => {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.append('page_size', params.limit.toString());
    if (params.offset) {
      const page = Math.floor(params.offset / (params.limit || 10)) + 1;
      queryParams.append('page', page.toString());
    }
    if (params.status) queryParams.append('status_filter', params.status);

    const response = await api.get(`/jobs/?${queryParams}`);
    return response.data;
  },

  getJob: async (jobId: string): Promise<VideoJob> => {
    const response: AxiosResponse<VideoJob> = await api.get(`/jobs/${jobId}`);
    return response.data;
  },

  submitJob: async (file: File, displayName?: string, processingConfig?: any): Promise<VideoJob> => {
    const formData = new FormData();
    formData.append('video_file', file);
    
    if (displayName) {
      formData.append('display_name', displayName);
    }
    
    if (processingConfig) {
      formData.append('processing_config', JSON.stringify(processingConfig));
    }

    const response: AxiosResponse<VideoJob> = await api.post('/jobs/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  cancelJob: async (jobId: string): Promise<void> => {
    await api.post(`/jobs/${jobId}/cancel`);
  },

  retryJob: async (jobId: string): Promise<void> => {
    await api.post(`/jobs/${jobId}/retry`);
  },

  deleteJob: async (jobId: string): Promise<void> => {
    await api.delete(`/jobs/${jobId}`);
  },

  getProcessingTemplates: async (): Promise<any[]> => {
    const response = await api.get('/jobs/templates/');
    return response.data;
  },

  // Direct upload and process endpoint (NO CELERY QUEUE - IMMEDIATE PROCESSING!)
  uploadAndProcess: async (file: File, displayName?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    if (displayName) {
      formData.append('display_name', displayName);
    }

    // Use the new direct processing endpoint that bypasses Celery
    const response = await api.post('/direct/direct-process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Batch process multiple videos at once
  batchProcess: async (files: File[]): Promise<any> => {
    const formData = new FormData();
    
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await api.post('/direct/batch-process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Get real-time job status
  getJobStatusDirect: async (jobId: string): Promise<any> => {
    const response = await api.get(`/direct/job-status/${jobId}`);
    return response.data;
  },
};

// Users API
const usersApi = {
  getProfile: async (): Promise<User> => {
    const response: AxiosResponse<User> = await api.get('/users/me');
    return response.data;
  },

  updateProfile: async (data: Partial<User>): Promise<User> => {
    const response: AxiosResponse<User> = await api.put('/users/me', data);
    return response.data;
  },

  getCreditHistory: async (params: { limit?: number; offset?: number } = {}): Promise<any> => {
    const { limit = 50, offset = 0 } = params;
    const response = await api.get(`/users/me/credits?limit=${limit}&offset=${offset}`);
    return response.data;
  },

  getUserStats: async (): Promise<any> => {
    const response = await api.get('/users/me/stats');
    return response.data;
  },

  getUsageStats: async (): Promise<any> => {
    const response = await api.get('/users/me/usage-stats');
    return response.data;
  },

  getSubscriptionTiers: async (): Promise<SubscriptionTier[]> => {
    const response: AxiosResponse<SubscriptionTier[]> = await api.get('/users/subscription-tiers');
    return response.data;
  },

  changePassword: async (data: { current_password: string; new_password: string }): Promise<void> => {
    await api.post('/users/me/change-password', data);
  },

  getApiKeys: async (): Promise<any[]> => {
    const response = await api.get('/users/me/api-keys');
    return response.data;
  },

  createApiKey: async (name: string): Promise<any> => {
    const response = await api.post('/users/me/api-keys', { name });
    return response.data;
  },

  deleteApiKey: async (keyId: string): Promise<void> => {
    await api.delete(`/users/me/api-keys/${keyId}`);
  },
};

// Files API
const filesApi = {
  downloadFile: async (fileId: string): Promise<Blob> => {
    const response = await api.get(`/files/${fileId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  getFileInfo: async (fileId: string): Promise<any> => {
    const response = await api.get(`/files/${fileId}`);
    return response.data;
  },

  deleteFile: async (fileId: string): Promise<void> => {
    await api.delete(`/files/${fileId}`);
  },

  shareFile: async (fileId: string, expiresHours = 24): Promise<any> => {
    const response = await api.post(`/files/${fileId}/share`, {
      expires_hours: expiresHours,
    });
    return response.data;
  },
};

// Admin API
const adminApi = {
  getSystemStats: async (): Promise<any> => {
    const response = await api.get('/admin/stats');
    return response.data;
  },

  getUsers: async (params: { limit?: number; offset?: number } = {}): Promise<any> => {
    const { limit = 100, offset = 0 } = params;
    const response = await api.get(`/admin/users?limit=${limit}&offset=${offset}`);
    return response.data;
  },

  getAllJobs: async (params: { limit?: number; offset?: number } = {}): Promise<any> => {
    const { limit = 50, offset = 0 } = params;
    const response = await api.get(`/admin/jobs?limit=${limit}&offset=${offset}`);
    return response.data;
  },

  getSystemHealth: async (): Promise<any> => {
    const response = await api.get('/admin/health');
    return response.data;
  },

  suspendUser: async (userId: string): Promise<void> => {
    await api.post(`/admin/users/${userId}/suspend`);
  },

  adjustUserCredits: async (userId: string, amount: number, reason: string): Promise<void> => {
    await api.post(`/admin/users/${userId}/credits`, {
      amount,
      reason,
    });
  },
};

// Chunked Upload API
const chunkedUploadApi = {
  initializeUpload: (data: {
    filename: string;
    total_size: number;
    chunk_size?: number;
    content_hash?: string;
  }) => {
    const formData = new FormData();
    formData.append('filename', data.filename);
    formData.append('total_size', data.total_size.toString());
    if (data.chunk_size) formData.append('chunk_size', data.chunk_size.toString());
    if (data.content_hash) formData.append('content_hash', data.content_hash);
    
    return api.post('/chunked-upload/initialize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  uploadChunk: (uploadId: string, formData: FormData, options?: { signal?: AbortSignal }) =>
    api.post(`/chunked-upload/chunk/${uploadId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      ...options,
    }).then(res => res.data),

  finalizeUpload: (uploadId: string, data: { final_hash?: string }) => {
    const formData = new FormData();
    if (data.final_hash) formData.append('final_hash', data.final_hash);
    
    return api.post(`/chunked-upload/finalize/${uploadId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(res => res.data);
  },

  getUploadStatus: (uploadId: string) =>
    api.get(`/chunked-upload/status/${uploadId}`).then(res => res.data),

  cancelUpload: (uploadId: string) =>
    api.delete(`/chunked-upload/cancel/${uploadId}`).then(res => res.data),
};

// Export all APIs
export { authApi, jobsApi, usersApi, filesApi, adminApi, chunkedUploadApi };

export default api;
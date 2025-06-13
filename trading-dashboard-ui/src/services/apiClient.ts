// src/services/apiClient.ts
import axios, { type AxiosInstance, type InternalAxiosRequestConfig, type AxiosRequestConfig, type AxiosResponse, AxiosError } from 'axios';

// Types for API responses
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface ApiError {
  success: false;
  message: string;
  detail?: string;
  status?: number;
}

// API Client Configuration
const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000'),
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
};

// Create Axios instance
const apiClient: AxiosInstance = axios.create(API_CONFIG);

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add timestamp to prevent caching
    if (config.params) {
      config.params._t = new Date().getTime();
    } else {
      config.params = { _t: new Date().getTime() };
    }

    // Add authentication token if available
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log request in development
    if (import.meta.env.DEV) {
      console.log('🚀 API Request:', {
        method: config.method?.toUpperCase(),
        url: config.url,
        data: config.data,
        params: config.params,
      });
    }

    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log('✅ API Response:', {
        status: response.status,
        url: response.config.url,
        data: response.data,
      });
    }

    return response;
  },
  (error: AxiosError) => {
    // Handle different types of errors
    let apiError: ApiError = {
      success: false,
      message: 'An unexpected error occurred',
      status: error.response?.status,
    };

    if (error.response) {
      // Server responded with error status
      const errorData = error.response.data as any;
      apiError = {
        success: false,
        message: errorData?.message || errorData?.detail || 'Server error occurred',
        detail: errorData?.detail,
        status: error.response.status,
      };
    } else if (error.request) {
      // Request was made but no response received
      apiError = {
        success: false,
        message: 'Network error - unable to connect to server',
        detail: 'Please check your internet connection and try again',
      };
    } else {
      // Something else happened
      apiError = {
        success: false,
        message: error.message || 'Request configuration error',
      };
    }

    // Log error in development
    if (import.meta.env.DEV) {
      console.error('❌ API Error:', {
        status: error.response?.status,
        message: apiError.message,
        url: error.config?.url,
        data: error.response?.data,
      });
    }

    // Handle specific status codes
    switch (error.response?.status) {
      case 401:
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem('auth_token');
        // You might want to redirect to login page here
        break;
      case 403:
        // Forbidden - show access denied message
        apiError.message = 'Access denied - insufficient permissions';
        break;
      case 404:
        // Not found
        apiError.message = 'Requested resource not found';
        break;
      case 422:
        // Validation error
        apiError.message = 'Validation error - please check your input';
        break;
      case 500:
        // Internal server error
        apiError.message = 'Internal server error - please try again later';
        break;
    }

    return Promise.reject(apiError);
  }
);

// API Methods
export const api = {
  // Generic methods
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> =>
    apiClient.get(url, config).then(response => response.data),

  post: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> =>
    apiClient.post(url, data, config).then(response => response.data),

  put: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> =>
    apiClient.put(url, data, config).then(response => response.data),

  patch: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> =>
    apiClient.patch(url, data, config).then(response => response.data),

  delete: <T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> =>
    apiClient.delete(url, config).then(response => response.data),

  // Trading specific endpoints
  clients: {
    // Get all clients
    getAll: (params?: { skip?: number; limit?: number; search?: string }) =>
      api.get<any[]>('/api/v1/admin/clients', { params }),

    // Get specific client
    getById: (clientId: number) =>
      api.get<any>(`/api/v1/admin/clients/${clientId}`),

    // Create new client
    create: (clientData: any) =>
      api.post<any>('/api/v1/admin/clients', clientData),

    // Update client
    update: (clientId: number, clientData: any) =>
      api.put<any>(`/api/v1/admin/clients/${clientId}`, clientData),

    // Update client credentials
    updateCredentials: (clientId: number, credentials: any) =>
      api.put<any>(`/api/v1/admin/clients/${clientId}/credentials`, credentials),

    // Get credential status
    getCredentialStatus: (clientId: number) =>
      api.get<any>(`/api/v1/admin/clients/${clientId}/credentials/status`),
  },

  tokens: {
    // Search tokens/instruments
    search: (params: { q: string; exchange?: string; limit?: number }) =>
      api.get<any[]>('/api/v1/tokens/search', { params }),

    // Get supported exchanges
    getExchanges: () =>
      api.get<any>('/api/v1/tokens/exchanges'),

    // Get local tokens
    getLocal: (params?: { skip?: number; limit?: number; exchange?: string; search?: string }) =>
      api.get<any[]>('/api/v1/tokens/local', { params }),

    // Refresh instrument cache
    refreshCache: (exchange: string) =>
      api.post<any>('/api/v1/tokens/cache/refresh', null, { params: { exchange } }),

    // Get cache status
    getCacheStatus: () =>
      api.get<any>('/api/v1/tokens/cache/status'),
  },

  portfolio: {
    // Get client portfolio
    getClientPortfolio: (clientId: number, params?: { segment?: string; include_trades?: boolean }) =>
      api.get<any>(`/api/v1/portfolio/clients/${clientId}`, { params }),

    // Get client positions
    getClientPositions: (clientId: number, params?: { segment?: string }) =>
      api.get<any>(`/api/v1/portfolio/clients/${clientId}/positions`, { params }),

    // Get client holdings
    getClientHoldings: (clientId: number, params?: { segment?: string }) =>
      api.get<any>(`/api/v1/portfolio/clients/${clientId}/holdings`, { params }),

    // Get dashboard stats
    getDashboardStats: () =>
      api.get<any>('/api/v1/portfolio/dashboard/stats'),

    // Get client summaries
    getClientSummaries: (params?: { limit?: number }) =>
      api.get<any>('/api/v1/portfolio/dashboard/clients', { params }),

    // Get realtime portfolio data
    getRealtimePortfolio: (clientId: number, params?: { segment?: string }) =>
      api.get<any>(`/api/v1/portfolio/clients/${clientId}/realtime`, { params }),
  },

  orders: {
    // Execute batch orders
    executeBatch: (orderData: any) =>
      api.post<any>('/api/v1/orders/execute-all', orderData),

    // Exit all positions for token
    exitAllPositions: (tokenId: string, exitData: any) =>
      api.post<any>(`/api/v1/orders/tokens/${tokenId}/exit-all`, exitData),

    // Get order status
    getOrderStatus: (orderId: string, params: { client_id: number; segment?: string }) =>
      api.get<any>(`/api/v1/orders/status/${orderId}`, { params }),

    // Cancel order
    cancelOrder: (orderId: string, params: { client_id: number; segment?: string }) =>
      api.post<any>(`/api/v1/orders/cancel/${orderId}`, null, { params }),
  },

  // Health checks
  health: {
    // Main API health check
    check: () =>
      api.get<any>('/health'),

    // Service-specific health checks
    checkPortfolio: () =>
      api.get<any>('/api/v1/portfolio/health'),

    checkOrders: () =>
      api.get<any>('/api/v1/orders/health'),
  },
};

// Utility functions
export const setAuthToken = (token: string) => {
  localStorage.setItem('auth_token', token);
};

export const clearAuthToken = () => {
  localStorage.removeItem('auth_token');
};

export const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token');
};

// Export the configured axios instance for direct use if needed
export default apiClient;
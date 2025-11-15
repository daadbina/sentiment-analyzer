import axios from 'axios';

const API_BASE_URL = '/api/v1/dashboard';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.config.url} - Status: ${response.status}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const dashboardAPI = {
  // Get latest conflict predictions
  getLatestPredictions: async (params = {}) => {
    const { limit = 100, minConfidence = 0.0, hours = 24 } = params;
    const response = await api.get('/conflict-predictions/latest', {
      params: {
        limit,
        min_confidence: minConfidence,
        hours,
      },
    });
    return response.data;
  },

  // Get country risk scores
  getCountryRiskScores: async () => {
    const response = await api.get('/conflict-predictions/by-country');
    return response.data;
  },

  // Get trend data
  getTrendData: async (params = {}) => {
    const { period = 'day', days = 7 } = params;
    const response = await api.get('/conflict-predictions/trends', {
      params: { period, days },
    });
    return response.data;
  },

  // Get top country pairs
  getTopCountryPairs: async (params = {}) => {
    const { limit = 10 } = params;
    const response = await api.get('/conflict-predictions/top-pairs', {
      params: { limit },
    });
    return response.data;
  },

  // Get dashboard stats
  getDashboardStats: async () => {
    const response = await api.get('/conflict-predictions/stats');
    return response.data;
  },

  // Get network graph data
  getNetworkGraph: async (params = {}) => {
    const { minConfidence = 0.5, hours = 168 } = params;
    const response = await api.get('/network-graph', {
      params: {
        min_confidence: minConfidence,
        hours,
      },
    });
    return response.data;
  },

  // Get BTC predictions
  getBTCPredictions: async (params = {}) => {
    const { limit = 10, minConfidence = 0.0, hours = 24 } = params;
    const response = await api.get('/btc-predictions', {
      params: {
        limit,
        min_confidence: minConfidence,
        hours,
      },
    });
    return response.data;
  },
};

export default dashboardAPI;


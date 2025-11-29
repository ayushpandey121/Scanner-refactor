// Create: rice_webapp_frontend/src/utils/axiosConfig.js

import axios from 'axios';

// Detect if running in Electron
export const isElectron = () => {
  return typeof window !== 'undefined' && 
         window.electron && 
         window.electron.isElectron;
};

// Get API base URL
export const getApiBaseUrl = () => {
  // In Electron (production), use localhost
  if (isElectron()) {
    return 'http://localhost:5000';
  }
  
  // In development (browser with Vite), use empty string (proxy handles it)
  if (import.meta.env.DEV) {
    return '';
  }
  
  // In production browser build
  return 'http://localhost:5000';
};

// Configure axios defaults GLOBALLY
axios.defaults.baseURL = getApiBaseUrl();
axios.defaults.timeout = 30000;

// Add request interceptor to log requests
axios.interceptors.request.use(
  (config) => {
    // For Flask backend endpoints, ensure full URL in Electron
    if (isElectron() && config.url && !config.url.startsWith('http')) {
      config.url = `${getApiBaseUrl()}${config.url}`;
    }
    
    console.log('🚀 API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor
axios.interceptors.response.use(
  (response) => {
    console.log('✅ API Response:', response.config.url, response.status);
    return response;
  },
  (error) => {
    console.error('❌ API Error:', error.message);
    if (error.response) {
      console.error('Response:', error.response.status, error.response.data);
    }
    return Promise.reject(error);
  }
);

// Export configured axios
export default axios;
import axios from 'axios';
import { API_URL, TOKEN_STORAGE_KEY } from '../utils/constants';

// Create an axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to add the auth token to requests
api.interceptors.request.use(
  (config) => {
    const tokenData = JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY));
    if (tokenData && tokenData.access) {
      config.headers['Authorization'] = `Bearer ${tokenData.access}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor to refresh the token if it's expired
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is due to an expired token and we haven't tried to refresh it yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const tokenData = JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY));
        
        if (tokenData && tokenData.refresh) {
          // Try to refresh the token
          const refreshRes = await axios.post(`${API_URL}/ponds/token/refresh/`, {
            refresh: tokenData.refresh,
          });
          
          // If successful, update the token in storage
          if (refreshRes.data.access) {
            localStorage.setItem(
              TOKEN_STORAGE_KEY,
              JSON.stringify({
                ...tokenData,
                access: refreshRes.data.access,
              })
            );
            
            // Retry the original request with the new token
            originalRequest.headers['Authorization'] = `Bearer ${refreshRes.data.access}`;
            return api(originalRequest);
          }
        }
      } catch (refreshError) {
        // If token refresh fails, log the user out
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
import api from './api';
import { TOKEN_STORAGE_KEY, REMEMBER_ME_KEY } from '../utils/constants';

export const login = async (credentials) => {
  try {
    const response = await api.post('/auth/login/', credentials);
    
    // Save tokens to storage
    if (response.data.access && response.data.refresh) {
      localStorage.setItem(
        TOKEN_STORAGE_KEY,
        JSON.stringify({
          access: response.data.access,
          refresh: response.data.refresh,
        })
      );
      
      // Handle remember me
      if (credentials.rememberMe) {
        localStorage.setItem(REMEMBER_ME_KEY, 'true');
      } else {
        localStorage.removeItem(REMEMBER_ME_KEY);
      }
    }
    
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Login failed. Please try again.' };
  }
};

export const logout = async () => {
  try {
    const tokenData = JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY));
    if (tokenData && tokenData.refresh) {
      await api.post('/auth/logout/', { refresh: tokenData.refresh });
    }
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    // We don't remove REMEMBER_ME_KEY on logout
  }
};

export const changePassword = async (passwordData) => {
  try {
    const response = await api.post('/auth/change-password/', passwordData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Password change failed. Please try again.' };
  }
};

export const isAuthenticated = () => {
  const tokenData = JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY));
  return tokenData && tokenData.access ? true : false;
};

export const getAuthTokens = () => {
  return JSON.parse(localStorage.getItem(TOKEN_STORAGE_KEY));
};

export const registerPond = async (pondData) => {
  try {
    const response = await api.post('/auth/register-pond/', pondData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Pond registration failed. Please try again.' };
  }
};
import api from './api';

// Get user profile
export const getUserProfile = async () => {
  try {
    const response = await api.get('/profile/');
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch user profile. Please try again.' };
  }
};

// Update user profile
export const updateUserProfile = async (profileData) => {
  try {
    const response = await api.put('/update-profile/', profileData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to update user profile. Please try again.' };
  }
};

// Change password
export const changeUserPassword = async (passwordData) => {
  try {
    const response = await api.post('/auth/change-password/', passwordData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to change password. Please try again.' };
  }
};
import api from './api';

// Get all ponds
export const getPonds = async () => {
  try {
    const response = await api.get('/ponds/');
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch ponds. Please try again.' };
  }
};

// Get a specific pond
export const getPond = async (pondId) => {
  try {
    const response = await api.get(`/ponds/${pondId}/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch pond details. Please try again.' };
  }
};

// Update a pond
export const updatePond = async (pondId, pondData) => {
  try {
    const response = await api.put(`/ponds/${pondId}/`, pondData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to update pond. Please try again.' };
  }
};

// Delete a pond
export const deletePond = async (pondId) => {
  try {
    await api.delete(`/ponds/${pondId}/`);
    return { success: true };
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to delete pond. Please try again.' };
  }
};

// Register a new pond
export const registerPond = async (pondData) => {
  try {
    const response = await api.post('/ponds/register-pond/', pondData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to register pond. Please try again.' };
  }
};
import api from './api';

// Get all ponds for the logged-in user
export const getUserPonds = async () => {
  try {
    const response = await api.get('/dashboard/user-ponds/');
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch ponds. Please try again.' };
  }
};

// Get current sensor data for a specific pond
export const getCurrentData = async (pondId) => {
  try {
    const response = await api.get(`/dashboard/current-data/?pond_id=${pondId}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch current data. Please try again.' };
  }
};

// Get historical data for a specific pond
export const getHistoricalData = async (pondId, range = '24h') => {
  try {
    const response = await api.get(`/dashboard/historical-data/?pond_id=${pondId}&range=${range}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch historical data. Please try again.' };
  }
};

// Feed fish
export const feedFish = async (pondId, amount) => {
  try {
    const response = await api.post(`/control/${pondId}/feed/`, { feed_amount: amount });
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to feed fish. Please try again.' };
  }
};

// Control water valve
export const controlWaterValve = async (pondId, valveState) => {
  try {
    const response = await api.post(`/control/${pondId}/water-valve/`, { valve_state: valveState });
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to control water valve. Please try again.' };
  }
};

// Get device logs
export const getDeviceLogs = async (pondId, logType = 'ACTION', limit = 10) => {
  try {
    const response = await api.get(`/control/${pondId}/logs/?log_type=${logType}&limit=${limit}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch device logs. Please try again.' };
  }
};
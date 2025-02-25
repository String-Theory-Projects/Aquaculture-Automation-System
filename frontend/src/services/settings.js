import api from './api';

// Get Wi-Fi configuration for a pond
export const getWifiConfig = async (pondId) => {
  try {
    const response = await api.get(`/settings/${pondId}/wifi/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch Wi-Fi configuration. Please try again.' };
  }
};

// Create Wi-Fi configuration for a pond
export const createWifiConfig = async (pondId, wifiData) => {
  try {
    const response = await api.post(`/settings/${pondId}/wifi/`, wifiData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to create Wi-Fi configuration. Please try again.' };
  }
};

// Update Wi-Fi configuration for a pond
export const updateWifiConfig = async (pondId, wifiData) => {
  try {
    const response = await api.put(`/settings/${pondId}/wifi/`, wifiData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to update Wi-Fi configuration. Please try again.' };
  }
};

// Delete Wi-Fi configuration for a pond
export const deleteWifiConfig = async (pondId) => {
  try {
    const response = await api.delete(`/settings/${pondId}/wifi/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to delete Wi-Fi configuration. Please try again.' };
  }
};

// Get automation schedules for a pond
export const getSchedules = async (pondId) => {
  try {
    const response = await api.get(`/settings/${pondId}/schedules/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch automation schedules. Please try again.' };
  }
};

// Create a new automation schedule
export const createSchedule = async (pondId, scheduleData) => {
  try {
    const response = await api.post(`/settings/${pondId}/schedules/`, scheduleData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to create automation schedule. Please try again.' };
  }
};

// Update an existing automation schedule
export const updateSchedule = async (scheduleId, scheduleData) => {
  try {
    const response = await api.put(`/settings/schedules/${scheduleId}/`, scheduleData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to update automation schedule. Please try again.' };
  }
};

// Delete an automation schedule
export const deleteSchedule = async (scheduleId) => {
  try {
    const response = await api.delete(`/settings/schedules/${scheduleId}/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to delete automation schedule. Please try again.' };
  }
};

// Get a specific automation schedule
export const getSchedule = async (scheduleId) => {
  try {
    const response = await api.get(`/settings/schedules/${scheduleId}/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to fetch automation schedule. Please try again.' };
  }
};

// Execute an automation schedule manually
export const executeSchedule = async (scheduleId) => {
  try {
    const response = await api.post(`/control/automation/${scheduleId}/execute/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { detail: 'Failed to execute automation schedule. Please try again.' };
  }
};
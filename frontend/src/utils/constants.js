// API URL
export const API_URL = 'http://127.0.0.1:8000/api';

// Polling interval in milliseconds (10 seconds)
export const POLLING_INTERVAL = 10000;

// Authentication
export const TOKEN_STORAGE_KEY = 'futurefish_tokens';
export const REMEMBER_ME_KEY = 'futurefish_remember_me';
export const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds

// Parameter Ranges
export const PARAMETER_RANGES = {
  DO: {
    min: 4,
    max: 8,
    optimalMin: 5,
    optimalMax: 6,
    unit: 'mg/L'
  },
  pH: {
    min: 6.5,
    max: 8.5,
    optimalMin: 7,
    optimalMax: 7.5,
    unit: ''
  },
  temperature: {
    min: 25,
    max: 30,
    optimalMin: 26,
    optimalMax: 28,
    unit: '°C'
  },
  turbidity: {
    min: 25,
    max: 100,
    optimalMin: 30,
    optimalMax: 80,
    unit: 'NTU'
  },
  waterLevel: {
    min: 0,
    max: 100,
    optimalMin: 70,
    optimalMax: 90,
    unit: '%'
  }
};

// Data timeframes
export const TIMEFRAMES = [
  { label: 'Last 24 Hours', value: '24h', description: 'Hourly data for the past 24 hours' },
  { label: 'Last Week', value: '1w', description: 'Data every 6 hours for the past week' },
  { label: 'Last Month', value: '1m', description: 'Daily data for the past month' }
];

// Days of the week for automation scheduling
export const DAYS_OF_WEEK = [
  { value: '0', label: 'Sunday' },
  { value: '1', label: 'Monday' },
  { value: '2', label: 'Tuesday' },
  { value: '3', label: 'Wednesday' },
  { value: '4', label: 'Thursday' },
  { value: '5', label: 'Friday' },
  { value: '6', label: 'Saturday' }
];

// Automation types
export const AUTOMATION_TYPES = [
  { value: 'FEED', label: 'Feed Fish' },
  { value: 'WATER', label: 'Water Change' }
];

// Feed amount range
export const FEED_AMOUNT_RANGE = {
  min: 0,
  max: 1000,
  step: 10,
  unit: 'g'
};

// Water level range
export const WATER_LEVEL_RANGE = {
  min: 0,
  max: 100,
  step: 5,
  unit: '%'
};
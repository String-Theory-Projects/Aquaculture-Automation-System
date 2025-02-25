import { createContext, useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { login as authLogin, logout as authLogout, changePassword, isAuthenticated } from '../services/auth';
import { INACTIVITY_TIMEOUT } from '../utils/constants';
import api from '../services/api';

// Create the context
const AuthContext = createContext();

// Hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Provider component
export const AuthProvider = ({ children, lastActivity }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Auto-logout after inactivity
  useEffect(() => {
    if (!isAuthenticated()) return;

    const checkInactivity = setInterval(() => {
      const now = Date.now();
      if (now - lastActivity > INACTIVITY_TIMEOUT) {
        handleLogout();
        alert('You have been logged out due to inactivity.');
      }
    }, 60000); // Check every minute

    return () => clearInterval(checkInactivity);
  }, [lastActivity]);

  // Fetch user profile on mount if authenticated
  useEffect(() => {
    const fetchUserProfile = async () => {
      if (!isAuthenticated()) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.get('/profile/');
        setUser(response.data);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching user profile:', err);
        setLoading(false);
      }
    };

    fetchUserProfile();
  }, []);

  // Login function
  const handleLogin = async (credentials) => {
    try {
      setError(null);
      setLoading(true);
      const data = await authLogin(credentials);
      
      // Fetch user profile after successful login
      const profileResponse = await api.get('/profile/');
      setUser(profileResponse.data);
      
      setLoading(false);
      navigate('/');
      return true;
    } catch (err) {
      setError(err.detail || 'Login failed. Please check your credentials.');
      setLoading(false);
      return false;
    }
  };

  // Logout function
  const handleLogout = async () => {
    setLoading(true);
    await authLogout();
    setUser(null);
    setLoading(false);
    navigate('/login');
  };

  // Update profile function
  const updateProfile = async (profileData) => {
    try {
      setError(null);
      setLoading(true);
      const response = await api.put('/update-profile/', profileData);
      setUser(response.data);
      setLoading(false);
      return true;
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile.');
      setLoading(false);
      return false;
    }
  };

  // Change password function
  const handleChangePassword = async (passwordData) => {
    try {
      setError(null);
      setLoading(true);
      await changePassword(passwordData);
      setLoading(false);
      return true;
    } catch (err) {
      setError(err.detail || 'Failed to change password.');
      setLoading(false);
      return false;
    }
  };

  const value = {
    user,
    loading,
    error,
    login: handleLogin,
    logout: handleLogout,
    updateProfile,
    changePassword: handleChangePassword,
    isAuthenticated: isAuthenticated,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
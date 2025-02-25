import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './styles/global.css';

// Context Providers
import { AuthProvider } from './context/AuthContext';
import { PondProvider } from './context/PondContext';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Profile from './pages/Profile';
import RegisterPond from './pages/RegisterPond';
import ManagePonds from './pages/ManagePonds';

// Auth utility
import { isAuthenticated } from './services/auth';

// Protected route component
const ProtectedRoute = ({ children }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  // Track user activity to implement auto-logout
  const [lastActivity, setLastActivity] = useState(Date.now());

  // Update last activity timestamp on user interaction
  const handleUserActivity = () => {
    setLastActivity(Date.now());
  };

  useEffect(() => {
    // Add event listeners to track user activity
    window.addEventListener('mousemove', handleUserActivity);
    window.addEventListener('keydown', handleUserActivity);
    window.addEventListener('click', handleUserActivity);
    window.addEventListener('scroll', handleUserActivity);
    window.addEventListener('touchstart', handleUserActivity);

    return () => {
      // Clean up event listeners
      window.removeEventListener('mousemove', handleUserActivity);
      window.removeEventListener('keydown', handleUserActivity);
      window.removeEventListener('click', handleUserActivity);
      window.removeEventListener('scroll', handleUserActivity);
      window.removeEventListener('touchstart', handleUserActivity);
    };
  }, []);

  return (
    <Router>
      <AuthProvider lastActivity={lastActivity}>
        <PondProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/settings" 
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/profile" 
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/register-pond" 
              element={
                <ProtectedRoute>
                  <RegisterPond />
                </ProtectedRoute>
              } 
            />
            
            <Route 
              path="/manage-ponds" 
              element={
                <ProtectedRoute>
                  <ManagePonds />
                </ProtectedRoute>
              } 
            />
            
            {/* Redirect any other routes to dashboard */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </PondProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
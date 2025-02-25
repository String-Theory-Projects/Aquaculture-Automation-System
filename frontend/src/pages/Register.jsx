import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaCheck } from 'react-icons/fa';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Alert from '../components/common/Alert';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import '../styles/register.css';

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
    first_name: '',
    last_name: ''
  });
  
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  
  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);
  
  // Handle input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
    
    // Clear error for this field
    if (errors[name]) {
      setErrors({
        ...errors,
        [name]: null
      });
    }
  };
  
  // Validate form
  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }
    
    if (formData.password !== formData.password2) {
      newErrors.password2 = 'Passwords do not match';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');
    
    try {
      await api.post('/auth/register/', formData);
      
      setSuccessMessage('Registration successful! You can now log in.');
      
      // Redirect to login after a brief delay
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      console.error('Registration error:', err);
      
      // Handle API validation errors
      if (err.response?.data) {
        const apiErrors = err.response.data;
        const formattedErrors = {};
        
        // Map API errors to form fields
        Object.keys(apiErrors).forEach(key => {
          formattedErrors[key] = apiErrors[key][0];
        });
        
        setErrors(formattedErrors);
      } else {
        setErrorMessage('Registration failed. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className="register-container">
      <div className="register-card">
        <div className="register-header">
          <img src="/src/assets/logo-dark.svg" alt="Future Fish Logo" className="register-logo" />
          <p>Create Your Account</p>
        </div>
        
        {successMessage && (
          <Alert type="success" autoClose>
            <div className="success-message">
              <FaCheck className="success-icon" />
              {successMessage}
            </div>
          </Alert>
        )}
        
        {errorMessage && (
          <Alert type="danger" dismissible onClose={() => setErrorMessage('')}>
            {errorMessage}
          </Alert>
        )}
        
        <form className="register-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <Input
              id="username"
              name="username"
              label="Username"
              value={formData.username}
              onChange={handleChange}
              error={errors.username}
              required
            />
            
            <Input
              id="email"
              name="email"
              label="Email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              error={errors.email}
              required
            />
          </div>
          
          <div className="form-row">
            <Input
              id="password"
              name="password"
              label="Password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              error={errors.password}
              required
            />
            
            <Input
              id="password2"
              name="password2"
              label="Confirm Password"
              type="password"
              value={formData.password2}
              onChange={handleChange}
              error={errors.password2}
              required
            />
          </div>
          
          <div className="form-row">
            <Input
              id="first_name"
              name="first_name"
              label="First Name"
              value={formData.first_name}
              onChange={handleChange}
              error={errors.first_name}
            />
            
            <Input
              id="last_name"
              name="last_name"
              label="Last Name"
              value={formData.last_name}
              onChange={handleChange}
              error={errors.last_name}
            />
          </div>
          
          <Button 
            type="submit" 
            className="register-button" 
            disabled={isSubmitting}
            variant="primary"
            fullWidth
          >
            {isSubmitting ? 'Registering...' : 'Register'}
          </Button>
          
          <div className="login-link">
            Already have an account? <Link to="/login">Log in</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Register;

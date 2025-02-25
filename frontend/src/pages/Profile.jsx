import React, { useState } from 'react';
import { FaUser, FaLock, FaCheck } from 'react-icons/fa';
import MainLayout from '../components/layout/MainLayout';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Alert from '../components/common/Alert';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

const Profile = () => {
  const { user, updateProfile, changePassword, loading } = useAuth();
  
  // Profile form state
  const [profileForm, setProfileForm] = useState({
    username: user?.username || '',
    email: user?.email || '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
  });
  
  // Password form state
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });
  
  // Form validation states
  const [profileErrors, setProfileErrors] = useState({});
  const [passwordErrors, setPasswordErrors] = useState({});
  
  // UI states
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  
  // Handle profile form input changes
  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileForm({
      ...profileForm,
      [name]: value
    });
    
    // Clear error for this field
    if (profileErrors[name]) {
      setProfileErrors({
        ...profileErrors,
        [name]: null
      });
    }
  };
  
  // Handle password form input changes
  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordForm({
      ...passwordForm,
      [name]: value
    });
    
    // Clear error for this field
    if (passwordErrors[name]) {
      setPasswordErrors({
        ...passwordErrors,
        [name]: null
      });
    }
  };
  
  // Validate profile form
  const validateProfileForm = () => {
    const errors = {};
    
    if (!profileForm.username.trim()) {
      errors.username = 'Username is required';
    }
    
    if (!profileForm.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(profileForm.email)) {
      errors.email = 'Email is invalid';
    }
    
    setProfileErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  // Validate password form
  const validatePasswordForm = () => {
    const errors = {};
    
    if (!passwordForm.old_password) {
      errors.old_password = 'Current password is required';
    }
    
    if (!passwordForm.new_password) {
      errors.new_password = 'New password is required';
    } else if (passwordForm.new_password.length < 8) {
      errors.new_password = 'Password must be at least 8 characters';
    }
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      errors.confirm_password = 'Passwords do not match';
    }
    
    setPasswordErrors(errors);
    return Object.keys(errors).length === 0;
  };
  
  // Handle profile form submission
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateProfileForm()) {
      return;
    }
    
    try {
      const success = await updateProfile(profileForm);
      
      if (success) {
        setProfileSuccess(true);
        setTimeout(() => setProfileSuccess(false), 3000);
      } else {
        setErrorMessage('Failed to update profile. Please try again.');
      }
    } catch (err) {
      setErrorMessage(err.message || 'An error occurred. Please try again.');
    }
  };
  
  // Handle password form submission
  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    if (!validatePasswordForm()) {
      return;
    }
    
    try {
      const success = await changePassword({
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password,
      });
      
      if (success) {
        setPasswordSuccess(true);
        setPasswordForm({
          old_password: '',
          new_password: '',
          confirm_password: '',
        });
        setTimeout(() => setPasswordSuccess(false), 3000);
      } else {
        setErrorMessage('Failed to change password. Please try again.');
      }
    } catch (err) {
      setErrorMessage(err.message || 'An error occurred. Please try again.');
    }
  };
  
  return (
    <MainLayout title="Profile Settings">
      {errorMessage && (
        <Alert 
          type="danger" 
          dismissible 
          onClose={() => setErrorMessage(null)}
        >
          {errorMessage}
        </Alert>
      )}
      
      <div className="profile-container">
        {/* Profile Information Card */}
        <Card 
          title="Profile Information" 
          className="profile-card"
          subtitle="Update your account details"
          icon={<FaUser className="card-icon" />}
        >
          {profileSuccess && (
            <Alert type="success" autoClose>
              <div className="success-message">
                <FaCheck className="success-icon" />
                Profile updated successfully!
              </div>
            </Alert>
          )}
          
          <form onSubmit={handleProfileSubmit} className="profile-form">
            <div className="form-row">
              <Input
                id="username"
                name="username"
                label="Username"
                value={profileForm.username}
                onChange={handleProfileChange}
                error={profileErrors.username}
                required
              />
              
              <Input
                id="email"
                name="email"
                label="Email"
                type="email"
                value={profileForm.email}
                onChange={handleProfileChange}
                error={profileErrors.email}
                required
              />
            </div>
            
            <div className="form-row">
              <Input
                id="first_name"
                name="first_name"
                label="First Name"
                value={profileForm.first_name}
                onChange={handleProfileChange}
                error={profileErrors.first_name}
              />
              
              <Input
                id="last_name"
                name="last_name"
                label="Last Name"
                value={profileForm.last_name}
                onChange={handleProfileChange}
                error={profileErrors.last_name}
              />
            </div>
            
            <Button 
              type="submit" 
              variant="primary"
              disabled={loading}
              className="submit-button"
            >
              Update Profile
            </Button>
          </form>
        </Card>
        
        {/* Change Password Card */}
        <Card 
          title="Change Password" 
          className="password-card"
          subtitle="Update your password"
          icon={<FaLock className="card-icon" />}
        >
          {passwordSuccess && (
            <Alert type="success" autoClose>
              <div className="success-message">
                <FaCheck className="success-icon" />
                Password changed successfully!
              </div>
            </Alert>
          )}
          
          <form onSubmit={handlePasswordSubmit} className="password-form">
            <Input
              id="old_password"
              name="old_password"
              label="Current Password"
              type="password"
              value={passwordForm.old_password}
              onChange={handlePasswordChange}
              error={passwordErrors.old_password}
              required
            />
            
            <Input
              id="new_password"
              name="new_password"
              label="New Password"
              type="password"
              value={passwordForm.new_password}
              onChange={handlePasswordChange}
              error={passwordErrors.new_password}
              required
            />
            
            <Input
              id="confirm_password"
              name="confirm_password"
              label="Confirm New Password"
              type="password"
              value={passwordForm.confirm_password}
              onChange={handlePasswordChange}
              error={passwordErrors.confirm_password}
              required
            />
            
            <Button 
              type="submit" 
              variant="primary"
              disabled={loading}
              className="submit-button"
            >
              Change Password
            </Button>
          </form>
        </Card>
      </div>
    </MainLayout>
  );
};

export default Profile;
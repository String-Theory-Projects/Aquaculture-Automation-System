import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FaPlusCircle, FaEdit, FaTrash, FaCheck } from 'react-icons/fa';
import MainLayout from '../components/layout/MainLayout';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Alert from '../components/common/Alert';
import Loader from '../components/common/Loader';
import { usePond } from '../context/PondContext';
import { updatePond, deletePond } from '../services/pond';
import './ManagePonds.css';

const ManagePonds = () => {
  const { ponds, updatePond: updatePondInContext, deletePond: deletePondInContext, loading, error: contextError } = usePond();
  
  const [selectedPond, setSelectedPond] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [pondForm, setPondForm] = useState({
    name: '',
    wifi_config: {
      ssid: '',
      password: ''
    }
  });
  const [formErrors, setFormErrors] = useState({});
  const [actionLoading, setActionLoading] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);

  // Handle selecting a pond to edit
  const handleSelectPond = (pond) => {
    setSelectedPond(pond);
    setPondForm({
      name: pond.name,
      wifi_config: {
        ssid: pond.wifi_config?.ssid || '',
        password: pond.wifi_config?.password || ''
      }
    });
    setIsEditing(true);
    setFormErrors({});
  };

  // Handle canceling edit mode
  const handleCancel = () => {
    setIsEditing(false);
    setSelectedPond(null);
    setFormErrors({});
  };

  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    if (name.startsWith('wifi_')) {
      const wifiField = name.replace('wifi_', '');
      setPondForm({
        ...pondForm,
        wifi_config: {
          ...pondForm.wifi_config,
          [wifiField]: value
        }
      });
      
      // Clear errors
      if (formErrors[`wifi_config.${wifiField}`]) {
        setFormErrors({
          ...formErrors,
          [`wifi_config.${wifiField}`]: null
        });
      }
    } else {
      setPondForm({
        ...pondForm,
        [name]: value
      });
      
      // Clear errors
      if (formErrors[name]) {
        setFormErrors({
          ...formErrors,
          [name]: null
        });
      }
    }
  };

  // Validate form
  const validateForm = () => {
    const errors = {};
    
    if (!pondForm.name.trim()) {
      errors.name = 'Pond name is required';
    }
    
    if (pondForm.wifi_config.ssid.trim() && !pondForm.wifi_config.password.trim()) {
      errors['wifi_config.password'] = 'Password is required when SSID is provided';
    }
    
    if (!pondForm.wifi_config.ssid.trim() && pondForm.wifi_config.password.trim()) {
      errors['wifi_config.ssid'] = 'SSID is required when password is provided';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm() || !selectedPond) {
      return;
    }
    
    setActionLoading(true);
    setError(null);
    
    // Prepare data for API
    const updateData = {
      name: pondForm.name
    };
    
    // Only include wifi_config if both fields are filled
    if (pondForm.wifi_config.ssid.trim() && pondForm.wifi_config.password.trim()) {
      updateData.wifi_config = pondForm.wifi_config;
    }
    
    try {
      const updatedPond = await updatePond(selectedPond.id, updateData);
      
      // Update pond in context
      updatePondInContext(updatedPond);
      
      setSuccess('Pond updated successfully');
      setTimeout(() => setSuccess(null), 3000);
      
      setIsEditing(false);
      setSelectedPond(null);
    } catch (err) {
      setError(err.detail || 'Failed to update pond. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle pond deletion
  const handleDeletePond = async (pondId) => {
    if (!confirm('Are you sure you want to delete this pond? This action cannot be undone.')) {
      return;
    }
    
    setActionLoading(true);
    setError(null);
    
    try {
      await deletePond(pondId);
      
      // Update ponds in context
      deletePondInContext(pondId);
      
      setSuccess('Pond deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
      
      if (selectedPond && selectedPond.id === pondId) {
        setIsEditing(false);
        setSelectedPond(null);
      }
    } catch (err) {
      setError(err.detail || 'Failed to delete pond. Please try again.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <MainLayout title="Manage Ponds">
      {(error || contextError) && (
        <Alert 
          type="danger" 
          dismissible 
          onClose={() => setError(null)}
        >
          {error || contextError}
        </Alert>
      )}
      
      {success && (
        <Alert type="success" autoClose>
          <div className="success-message">
            <FaCheck className="success-icon" />
            {success}
          </div>
        </Alert>
      )}
      
      <div className="manage-ponds-container">
        <div className="ponds-list-container">
          <Card 
            title="Your Ponds" 
            className="ponds-list-card"
            subtitle="Select a pond to manage its settings"
          >
            {loading ? (
              <Loader text="Loading ponds..." />
            ) : ponds.length === 0 ? (
              <div className="no-ponds">
                <p>You don't have any ponds yet.</p>
                <Link to="/register-pond" className="register-pond-link">
                  <FaPlusCircle className="register-icon" /> Register New Pond
                </Link>
              </div>
            ) : (
              <>
                <div className="ponds-list">
                  {ponds.map(pond => (
                    <div 
                      key={pond.id} 
                      className={`pond-item ${selectedPond?.id === pond.id ? 'active' : ''}`}
                      onClick={() => handleSelectPond(pond)}
                    >
                      <div className="pond-name">{pond.name}</div>
                      <div className="pond-actions">
                        <button 
                          className="pond-action edit"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectPond(pond);
                          }}
                          title="Edit Pond"
                        >
                          <FaEdit />
                        </button>
                        <button 
                          className="pond-action delete"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeletePond(pond.id);
                          }}
                          title="Delete Pond"
                        >
                          <FaTrash />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <Link to="/register-pond" className="register-pond-link">
                  <FaPlusCircle className="register-icon" /> Register New Pond
                </Link>
              </>
            )}
          </Card>
        </div>
        
        <div className="pond-edit-container">
          {isEditing && selectedPond ? (
            <Card 
              title={`Edit ${selectedPond.name}`} 
              className="pond-edit-card"
            >
              <form onSubmit={handleSubmit} className="pond-edit-form">
                <Input
                  id="name"
                  name="name"
                  label="Pond Name"
                  value={pondForm.name}
                  onChange={handleInputChange}
                  error={formErrors.name}
                  required
                />
                
                <div className="wifi-section">
                  <h3 className="wifi-heading">WiFi Configuration</h3>
                  <p className="wifi-note">Leave both fields empty to keep the current configuration.</p>
                  
                  <Input
                    id="wifi_ssid"
                    name="wifi_ssid"
                    label="WiFi SSID"
                    value={pondForm.wifi_config.ssid}
                    onChange={handleInputChange}
                    error={formErrors['wifi_config.ssid']}
                  />
                  
                  <Input
                    id="wifi_password"
                    name="wifi_password"
                    type="password"
                    label="WiFi Password"
                    value={pondForm.wifi_config.password}
                    onChange={handleInputChange}
                    error={formErrors['wifi_config.password']}
                  />
                </div>
                
                <div className="form-actions">
                  <Button 
                    type="submit" 
                    variant="primary"
                    disabled={actionLoading}
                  >
                    {actionLoading ? 'Saving...' : 'Save Changes'}
                  </Button>
                  
                  <Button 
                    type="button"
                    variant="outline"
                    onClick={handleCancel}
                    disabled={actionLoading}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          ) : (
            <Card 
              title="Pond Management" 
              className="pond-info-card"
            >
              <div className="pond-instructions">
                <p>Select a pond from the list to edit its settings.</p>
                <p>You can update the pond's name and WiFi configuration, or delete the pond if needed.</p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default ManagePonds;

import React, { useState, useEffect } from 'react';
import { FaWifi, FaClock, FaPlus, FaTrash, FaEdit, FaPlay } from 'react-icons/fa';
import MainLayout from '../components/layout/MainLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Alert from '../components/common/Alert';
import Loader from '../components/common/Loader';
import { usePond } from '../context/PondContext';
import { 
  getWifiConfig, 
  createWifiConfig, 
  updateWifiConfig, 
  deleteWifiConfig,
  getSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  executeSchedule 
} from '../services/settings';
import { DAYS_OF_WEEK, AUTOMATION_TYPES } from '../utils/constants';
import './Settings.css';

const Settings = () => {
  const { selectedPond } = usePond();
  
  // States for WiFi configuration
  const [wifiConfig, setWifiConfig] = useState(null);
  const [isEditingWifi, setIsEditingWifi] = useState(false);
  const [wifiFormData, setWifiFormData] = useState({ ssid: '', password: '' });
  const [wifiErrors, setWifiErrors] = useState({});
  
  // States for automation schedules
  const [schedules, setSchedules] = useState([]);
  const [isAddingSchedule, setIsAddingSchedule] = useState(false);
  const [scheduleFormData, setScheduleFormData] = useState({
    automation_type: 'FEED',
    is_active: true,
    time: '08:00',
    days: [],
    feed_amount: 100,
    target_water_level: 90,
    drain_water_level: 10
  });
  const [scheduleErrors, setScheduleErrors] = useState({});
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  
  // States for general UI
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // Fetch WiFi config and schedules when selected pond changes
  useEffect(() => {
    if (selectedPond) {
      fetchWifiConfig();
      fetchSchedules();
    } else {
      setLoading(false);
    }
  }, [selectedPond]);
  
  // Fetch WiFi configuration
  const fetchWifiConfig = async () => {
    try {
      setLoading(true);
      const response = await getWifiConfig(selectedPond.id);
      setWifiConfig(response);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching WiFi config:', err);
      setWifiConfig(null);
      setLoading(false);
    }
  };
  
  // Fetch automation schedules
  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await getSchedules(selectedPond.id);
      setSchedules(response);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching schedules:', err);
      setError('Failed to load automation schedules. Please try again.');
      setLoading(false);
    }
  };
  
  // Handle WiFi form input change
  const handleWifiInputChange = (e) => {
    const { name, value } = e.target;
    setWifiFormData({
      ...wifiFormData,
      [name]: value
    });
    
    // Clear error for this field
    if (wifiErrors[name]) {
      setWifiErrors({
        ...wifiErrors,
        [name]: null
      });
    }
  };
  
  // Handle schedule form input change
  const handleScheduleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name === 'days') {
      // Handle days checkboxes
      const dayValue = e.target.value;
      const updatedDays = [...scheduleFormData.days];
      
      if (checked) {
        updatedDays.push(dayValue);
      } else {
        const index = updatedDays.indexOf(dayValue);
        if (index !== -1) {
          updatedDays.splice(index, 1);
        }
      }
      
      setScheduleFormData({
        ...scheduleFormData,
        days: updatedDays
      });
    } else if (type === 'checkbox') {
      setScheduleFormData({
        ...scheduleFormData,
        [name]: checked
      });
    } else {
      setScheduleFormData({
        ...scheduleFormData,
        [name]: value
      });
    }
    
    // Clear error for this field
    if (scheduleErrors[name]) {
      setScheduleErrors({
        ...scheduleErrors,
        [name]: null
      });
    }
  };
  
  // Start editing WiFi config
  const startEditingWifi = () => {
    setWifiFormData({
      ssid: wifiConfig ? wifiConfig.ssid : '',
      password: wifiConfig ? wifiConfig.password : ''
    });
    setIsEditingWifi(true);
  };
  
  // Cancel editing WiFi config
  const cancelEditingWifi = () => {
    setIsEditingWifi(false);
    setWifiErrors({});
  };
  
  // Validate WiFi form
  const validateWifiForm = () => {
    const newErrors = {};
    
    if (!wifiFormData.ssid.trim()) {
      newErrors.ssid = 'SSID is required';
    }
    
    if (!wifiFormData.password.trim()) {
      newErrors.password = 'Password is required';
    } else if (wifiFormData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }
    
    setWifiErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Save WiFi configuration
  const saveWifiConfig = async () => {
    if (!validateWifiForm()) {
      return;
    }
    
    try {
      setLoading(true);
      
      if (wifiConfig) {
        // Update existing config
        await updateWifiConfig(selectedPond.id, wifiFormData);
      } else {
        // Create new config
        await createWifiConfig(selectedPond.id, wifiFormData);
      }
      
      fetchWifiConfig();
      setIsEditingWifi(false);
      setSuccess('WiFi configuration saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error saving WiFi config:', err);
      setError('Failed to save WiFi configuration. Please try again.');
      setLoading(false);
    }
  };
  
  // Delete WiFi configuration
  const deleteWifiConfiguration = async () => {
    if (!confirm('Are you sure you want to delete the WiFi configuration?')) {
      return;
    }
    
    try {
      setLoading(true);
      await deleteWifiConfig(selectedPond.id);
      setWifiConfig(null);
      setIsEditingWifi(false);
      setSuccess('WiFi configuration deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error deleting WiFi config:', err);
      setError('Failed to delete WiFi configuration. Please try again.');
      setLoading(false);
    }
  };
  
  // Start adding a new schedule
  const startAddingSchedule = () => {
    setScheduleFormData({
      automation_type: 'FEED',
      is_active: true,
      time: '08:00',
      days: ['1', '2', '3', '4', '5'], // Monday to Friday
      feed_amount: 100,
      target_water_level: 90,
      drain_water_level: 10
    });
    setIsAddingSchedule(true);
    setEditingScheduleId(null);
  };
  
  // Start editing a schedule
  const startEditingSchedule = (schedule) => {
    // Format time (remove seconds)
    const timeWithoutSeconds = schedule.time.substring(0, 5);
    
    // Format days (convert to array)
    const daysArray = schedule.days.split(',');
    
    setScheduleFormData({
      automation_type: schedule.automation_type,
      is_active: schedule.is_active,
      time: timeWithoutSeconds,
      days: daysArray,
      feed_amount: schedule.feed_amount || 100,
      target_water_level: schedule.target_water_level || 90,
      drain_water_level: schedule.drain_water_level || 10
    });
    setIsAddingSchedule(true);
    setEditingScheduleId(schedule.id);
  };
  
  // Cancel adding/editing schedule
  const cancelScheduleForm = () => {
    setIsAddingSchedule(false);
    setEditingScheduleId(null);
    setScheduleErrors({});
  };
  
  // Validate schedule form
  const validateScheduleForm = () => {
    const newErrors = {};
    
    if (!scheduleFormData.time) {
      newErrors.time = 'Time is required';
    }
    
    if (scheduleFormData.days.length === 0) {
      newErrors.days = 'At least one day must be selected';
    }
    
    if (scheduleFormData.automation_type === 'FEED') {
      if (!scheduleFormData.feed_amount || scheduleFormData.feed_amount <= 0) {
        newErrors.feed_amount = 'Feed amount must be greater than 0';
      }
    } else if (scheduleFormData.automation_type === 'WATER') {
      if (!scheduleFormData.target_water_level || scheduleFormData.target_water_level <= 0 || scheduleFormData.target_water_level > 100) {
        newErrors.target_water_level = 'Target water level must be between 1-100%';
      }
      
      if (!scheduleFormData.drain_water_level || scheduleFormData.drain_water_level < 0 || scheduleFormData.drain_water_level >= scheduleFormData.target_water_level) {
        newErrors.drain_water_level = 'Drain level must be less than target level';
      }
    }
    
    setScheduleErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Save schedule
  const saveSchedule = async () => {
    if (!validateScheduleForm()) {
      return;
    }
    
    // Format days array to string
    const formattedData = {
      ...scheduleFormData,
      days: scheduleFormData.days.join(',')
    };
    
    try {
      setLoading(true);
      
      if (editingScheduleId) {
        // Update existing schedule
        await updateSchedule(editingScheduleId, formattedData);
      } else {
        // Create new schedule
        await createSchedule(selectedPond.id, formattedData);
      }
      
      fetchSchedules();
      setIsAddingSchedule(false);
      setEditingScheduleId(null);
      setSuccess('Automation schedule saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error saving schedule:', err);
      setError('Failed to save automation schedule. Please try again.');
      setLoading(false);
    }
  };
  
  // Delete schedule
  const handleDeleteSchedule = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this automation schedule?')) {
      return;
    }
    
    try {
      setLoading(true);
      await deleteSchedule(scheduleId);
      fetchSchedules();
      setSuccess('Automation schedule deleted successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error('Error deleting schedule:', err);
      setError('Failed to delete automation schedule. Please try again.');
      setLoading(false);
    }
  };
  
  // Execute schedule manually
  const handleExecuteSchedule = async (scheduleId) => {
    try {
      setLoading(true);
      await executeSchedule(scheduleId);
      setSuccess('Automation executed successfully');
      setTimeout(() => setSuccess(null), 3000);
      setLoading(false);
    } catch (err) {
      console.error('Error executing schedule:', err);
      setError('Failed to execute automation. Please try again.');
      setLoading(false);
    }
  };
  
  // Format time for display
  const formatTime = (timeString) => {
    try {
      // Convert 24-hour format to 12-hour format
      const [hours, minutes] = timeString.split(':');
      const hour = parseInt(hours, 10);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const hour12 = hour % 12 || 12;
      return `${hour12}:${minutes} ${ampm}`;
    } catch (err) {
      return timeString;
    }
  };
  
  // Format days for display
  const formatDays = (daysString) => {
    try {
      const daysArray = daysString.split(',');
      
      if (daysArray.length === 7) {
        return 'Every day';
      }
      
      if (daysArray.length === 5 && 
        daysArray.includes('1') && 
        daysArray.includes('2') && 
        daysArray.includes('3') && 
        daysArray.includes('4') && 
        daysArray.includes('5')) {
        return 'Weekdays';
      }
      
      if (daysArray.length === 2 && 
        daysArray.includes('0') && 
        daysArray.includes('6')) {
        return 'Weekends';
      }
      
      return daysArray.map(day => {
        const dayObj = DAYS_OF_WEEK.find(d => d.value === day);
        return dayObj ? dayObj.label.substring(0, 3) : day;
      }).join(', ');
    } catch (err) {
      return daysString;
    }
  };
  
  return (
    <MainLayout title="Settings">
      {error && (
        <Alert type="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert type="success" dismissible autoClose>
          {success}
        </Alert>
      )}
      
      {!selectedPond ? (
        <div className="no-pond-selected">
          <p>Please select a pond from the dropdown to view and manage settings.</p>
        </div>
      ) : loading && !wifiConfig && schedules.length === 0 ? (
        <Loader text="Loading settings..." />
      ) : (
        <div className="settings-container">
          {/* WiFi Configuration Section */}
          <Card 
            title="WiFi Configuration" 
            className="settings-card wifi-card"
            subtitle="Configure the WiFi settings for your device"
          >
            {isEditingWifi ? (
              <div className="wifi-form">
                <Input
                  id="ssid"
                  name="ssid"
                  label="SSID (Network Name)"
                  value={wifiFormData.ssid}
                  onChange={handleWifiInputChange}
                  placeholder="Enter WiFi network name"
                  error={wifiErrors.ssid}
                  required
                />
                
                <Input
                  id="password"
                  name="password"
                  type="password"
                  label="Password"
                  value={wifiFormData.password}
                  onChange={handleWifiInputChange}
                  placeholder="Enter WiFi password"
                  error={wifiErrors.password}
                  required
                />
                
                <div className="form-actions">
                  <Button 
                    onClick={saveWifiConfig} 
                    variant="primary"
                    disabled={loading}
                  >
                    Save Configuration
                  </Button>
                  
                  <Button 
                    onClick={cancelEditingWifi} 
                    variant="outline"
                    disabled={loading}
                  >
                    Cancel
                  </Button>
                  
                  {wifiConfig && (
                    <Button 
                      onClick={deleteWifiConfiguration} 
                      variant="danger"
                      disabled={loading}
                    >
                      Delete Configuration
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="wifi-display">
                {wifiConfig ? (
                  <>
                    <div className="wifi-info">
                      <div className="wifi-icon-container">
                        <FaWifi className="wifi-icon" />
                      </div>
                      <div className="wifi-details">
                        <div className="wifi-field">
                          <span className="wifi-label">SSID:</span>
                          <span className="wifi-value">{wifiConfig.ssid}</span>
                        </div>
                        <div className="wifi-field">
                          <span className="wifi-label">Password:</span>
                          <span className="wifi-value">••••••••</span>
                        </div>
                      </div>
                    </div>
                    
                    <Button 
                      onClick={startEditingWifi} 
                      variant="secondary"
                      disabled={loading}
                    >
                      <FaEdit className="button-icon" /> Edit Configuration
                    </Button>
                  </>
                ) : (
                  <div className="no-wifi-config">
                    <p>No WiFi configuration found. Set up WiFi for your device.</p>
                    <Button 
                      onClick={startEditingWifi} 
                      variant="primary"
                      disabled={loading}
                    >
                      <FaWifi className="button-icon" /> Setup WiFi
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>
          
          {/* Automation Schedules Section */}
          <Card 
            title="Automation Schedules" 
            className="settings-card schedules-card"
            subtitle="Create and manage automated tasks for your pond"
          >
            {isAddingSchedule ? (
              <div className="schedule-form">
                <div className="form-group">
                  <label className="form-label">Automation Type</label>
                  <div className="automation-type-selector">
                    {AUTOMATION_TYPES.map(type => (
                      <div 
                        key={type.value}
                        className={`automation-type-option ${scheduleFormData.automation_type === type.value ? 'active' : ''}`}
                        onClick={() => handleScheduleInputChange({ 
                          target: { name: 'automation_type', value: type.value } 
                        })}
                      >
                        {type.label}
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="form-row">
                  <Input
                    id="time"
                    name="time"
                    type="time"
                    label="Time"
                    value={scheduleFormData.time}
                    onChange={handleScheduleInputChange}
                    error={scheduleErrors.time}
                    required
                  />
                  
                  <div className="form-group">
                    <label className="form-label">
                      Active
                      <input
                        type="checkbox"
                        name="is_active"
                        checked={scheduleFormData.is_active}
                        onChange={handleScheduleInputChange}
                        className="active-checkbox"
                      />
                    </label>
                  </div>
                </div>
                
                <div className="form-group">
                  <label className="form-label">Days</label>
                  <div className="days-checkboxes">
                    {DAYS_OF_WEEK.map(day => (
                      <div key={day.value} className="day-checkbox">
                        <input
                          type="checkbox"
                          id={`day-${day.value}`}
                          name="days"
                          value={day.value}
                          checked={scheduleFormData.days.includes(day.value)}
                          onChange={handleScheduleInputChange}
                        />
                        <label htmlFor={`day-${day.value}`}>{day.label.substring(0, 3)}</label>
                      </div>
                    ))}
                  </div>
                  {scheduleErrors.days && <div className="error-message">{scheduleErrors.days}</div>}
                </div>
                
                {scheduleFormData.automation_type === 'FEED' ? (
                  <Input
                    id="feed_amount"
                    name="feed_amount"
                    type="number"
                    label="Feed Amount (g)"
                    value={scheduleFormData.feed_amount}
                    onChange={handleScheduleInputChange}
                    error={scheduleErrors.feed_amount}
                    min="0"
                    step="10"
                    required
                  />
                ) : (
                  <div className="form-row">
                    <Input
                      id="target_water_level"
                      name="target_water_level"
                      type="number"
                      label="Target Water Level (%)"
                      value={scheduleFormData.target_water_level}
                      onChange={handleScheduleInputChange}
                      error={scheduleErrors.target_water_level}
                      min="0"
                      max="100"
                      step="5"
                      required
                    />
                    
                    <Input
                      id="drain_water_level"
                      name="drain_water_level"
                      type="number"
                      label="Drain Level (%)"
                      value={scheduleFormData.drain_water_level}
                      onChange={handleScheduleInputChange}
                      error={scheduleErrors.drain_water_level}
                      min="0"
                      max="100"
                      step="5"
                      required
                    />
                  </div>
                )}
                
                <div className="form-actions">
                  <Button 
                    onClick={saveSchedule} 
                    variant="primary"
                    disabled={loading}
                  >
                    {editingScheduleId ? 'Update Schedule' : 'Add Schedule'}
                  </Button>
                  
                  <Button 
                    onClick={cancelScheduleForm} 
                    variant="outline"
                    disabled={loading}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="schedules-list">
                  {schedules.length === 0 ? (
                    <div className="no-schedules">
                      <p>No automation schedules found. Create a schedule to automate your pond tasks.</p>
                    </div>
                  ) : (
                    schedules.map(schedule => (
                      <div key={schedule.id} className="schedule-item">
                        <div className="schedule-indicator">
                          <div className={`schedule-status ${schedule.is_active ? 'active' : 'inactive'}`}></div>
                          <FaClock className="schedule-icon" />
                        </div>
                        
                        <div className="schedule-details">
                          <div className="schedule-header">
                            <h3 className="schedule-type">
                              {schedule.automation_type === 'FEED' ? 'Feed Fish' : 'Water Change'}
                            </h3>
                            <span className="schedule-time">{formatTime(schedule.time)}</span>
                          </div>
                          
                          <div className="schedule-days">{formatDays(schedule.days)}</div>
                          
                          {schedule.automation_type === 'FEED' ? (
                            <div className="schedule-specs">Feed amount: {schedule.feed_amount}g</div>
                          ) : (
                            <div className="schedule-specs">
                              Target: {schedule.target_water_level}% | Drain: {schedule.drain_water_level}%
                            </div>
                          )}
                          
                          <div className="schedule-status-text">
                            Status: <span className={schedule.is_active ? 'active-text' : 'inactive-text'}>
                              {schedule.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </div>
                        
                        <div className="schedule-actions">
                          <button
                            className="action-button edit-button"
                            onClick={() => startEditingSchedule(schedule)}
                            disabled={loading}
                            title="Edit"
                          >
                            <FaEdit />
                          </button>
                          
                          <button
                            className="action-button delete-button"
                            onClick={() => handleDeleteSchedule(schedule.id)}
                            disabled={loading}
                            title="Delete"
                          >
                            <FaTrash />
                          </button>
                          
                          <button
                            className="action-button execute-button"
                            onClick={() => handleExecuteSchedule(schedule.id)}
                            disabled={loading}
                            title="Execute Now"
                          >
                            <FaPlay />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                
                <Button 
                  onClick={startAddingSchedule} 
                  variant="secondary"
                  className="add-schedule-btn"
                  disabled={loading}
                >
                  <FaPlus className="button-icon" /> Add Schedule
                </Button>
              </>
            )}
          </Card>
        </div>
      )}
    </MainLayout>
  );
};

export default Settings;
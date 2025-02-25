import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Html5QrcodeScanner } from 'html5-qrcode';
import MainLayout from '../components/layout/MainLayout';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Alert from '../components/common/Alert';
import { registerPond } from '../services/pond';
import { usePond } from '../context/PondContext';
import './RegisterPond.css';

const RegisterPond = () => {
  const [pondData, setPondData] = useState({
    name: '',
    device_id: ''
  });
  const [errors, setErrors] = useState({});
  const [isScanning, setIsScanning] = useState(false);
  const [scannerReady, setScannerReady] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [alertMessage, setAlertMessage] = useState(null);
  
  const scannerRef = useRef(null);
  const qrScannerRef = useRef(null);
  const navigate = useNavigate();
  const { addPond } = usePond();
  
  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setPondData({
      ...pondData,
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
  
  // Start QR scanner
  const startScanner = () => {
    setIsScanning(true);
    
    // Short delay to ensure DOM is ready
    setTimeout(() => {
      if (qrScannerRef.current) {
        return;
      }
      
      try {
        qrScannerRef.current = new Html5QrcodeScanner('qr-scanner', {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          showTorchButtonIfSupported: true
        }, false);
        
        qrScannerRef.current.render(
          // Success callback
          (decodedText) => {
            handleQrCodeSuccess(decodedText);
          },
          // Error callback
          (error) => {
            console.error('QR scan error:', error);
          }
        );
        
        setScannerReady(true);
      } catch (err) {
        console.error('Failed to initialize scanner:', err);
        setAlertMessage({
          type: 'danger',
          text: 'Failed to initialize QR scanner. Please try again or enter device ID manually.'
        });
        setIsScanning(false);
      }
    }, 500);
  };
  
  // Handle successful QR scan
  const handleQrCodeSuccess = (deviceId) => {
    // Stop scanner
    if (qrScannerRef.current) {
      qrScannerRef.current.clear();
      qrScannerRef.current = null;
    }
    
    setPondData({
      ...pondData,
      device_id: deviceId
    });
    
    setIsScanning(false);
    setScannerReady(false);
    
    setAlertMessage({
      type: 'success',
      text: 'Device ID successfully scanned!'
    });
  };
  
  // Close scanner
  const closeScanner = () => {
    if (qrScannerRef.current) {
      qrScannerRef.current.clear();
      qrScannerRef.current = null;
    }
    
    setIsScanning(false);
    setScannerReady(false);
  };
  
  // Validate the form
  const validateForm = () => {
    const newErrors = {};
    
    if (!pondData.name.trim()) {
      newErrors.name = 'Pond name is required';
    }
    
    if (!pondData.device_id.trim()) {
      newErrors.device_id = 'Device ID is required';
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
    setAlertMessage(null);
    
    try {
      const response = await registerPond(pondData);
      
      // Add the new pond to context
      addPond(response);
      
      setAlertMessage({
        type: 'success',
        text: 'Pond registered successfully!'
      });
      
      // Navigate to dashboard after a brief delay
      setTimeout(() => {
        navigate('/');
      }, 1500);
    } catch (err) {
      setAlertMessage({
        type: 'danger',
        text: err.detail || 'Failed to register pond. Please try again.'
      });
      setIsSubmitting(false);
    }
  };
  
  return (
    <MainLayout title="Register New Pond">
      {alertMessage && (
        <Alert 
          type={alertMessage.type} 
          dismissible 
          onClose={() => setAlertMessage(null)}
        >
          {alertMessage.text}
        </Alert>
      )}
      
      <div className="register-pond-container">
        <Card className="register-pond-card">
          <form onSubmit={handleSubmit}>
            <Input
              id="name"
              name="name"
              label="Pond Name"
              value={pondData.name}
              onChange={handleChange}
              placeholder="Enter a name for your pond"
              error={errors.name}
              required
            />
            
            <Input
              id="device_id"
              name="device_id"
              label="Device ID"
              value={pondData.device_id}
              onChange={handleChange}
              placeholder="Enter device ID or scan QR code"
              error={errors.device_id}
              required
              disabled={isScanning}
            />
            
            {!isScanning ? (
              <Button 
                type="button" 
                variant="secondary" 
                onClick={startScanner}
                className="scan-button"
              >
                Scan QR Code
              </Button>
            ) : (
              <Button 
                type="button" 
                variant="outline" 
                onClick={closeScanner}
                className="scan-button"
              >
                Cancel Scanning
              </Button>
            )}
            
            {isScanning && (
              <div className="qr-scanner-container">
                <div id="qr-scanner" ref={scannerRef}></div>
                {!scannerReady && <div className="scanner-loading">Initializing camera...</div>}
              </div>
            )}
            
            <Button 
              type="submit" 
              variant="primary" 
              fullWidth
              disabled={isSubmitting || isScanning}
              className="submit-button"
            >
              {isSubmitting ? 'Registering...' : 'Register Pond'}
            </Button>
          </form>
        </Card>
      </div>
    </MainLayout>
  );
};

export default RegisterPond;
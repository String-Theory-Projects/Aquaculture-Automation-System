import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import './Alert.css';

const Alert = ({
  children,
  type = 'info',
  dismissible = false,
  autoClose = false,
  autoCloseTime = 5000,
  onClose
}) => {
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    let timer;
    if (autoClose && isVisible) {
      timer = setTimeout(() => {
        handleClose();
      }, autoCloseTime);
    }
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [autoClose, autoCloseTime, isVisible]);
  
  const handleClose = () => {
    setIsVisible(false);
    if (onClose) onClose();
  };
  
  if (!isVisible) return null;
  
  return (
    <div className={`alert alert-${type} ${dismissible ? 'alert-dismissible' : ''}`} role="alert">
      {children}
      {dismissible && (
        <button 
          type="button" 
          className="alert-close" 
          aria-label="Close" 
          onClick={handleClose}
        >
          &times;
        </button>
      )}
    </div>
  );
};

Alert.propTypes = {
  children: PropTypes.node.isRequired,
  type: PropTypes.oneOf(['success', 'warning', 'danger', 'info']),
  dismissible: PropTypes.bool,
  autoClose: PropTypes.bool,
  autoCloseTime: PropTypes.number,
  onClose: PropTypes.func
};

export default Alert;
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { FaWater, FaToggleOn, FaToggleOff } from 'react-icons/fa';
import Button from '../common/Button';
import './WaterControl.css';

const WaterControl = ({ 
  valveState, 
  onControlWaterValve, 
  disabled,
  waterLevel 
}) => {
  const [isChanging, setIsChanging] = useState(false);

  const handleToggleValve = () => {
    setIsChanging(true);
    
    // Call the parent component's handler
    onControlWaterValve(!valveState)
      .then(() => {
        setIsChanging(false);
      })
      .catch(() => {
        setIsChanging(false);
      });
  };

  return (
    <div className="water-control-container">
      <div className="water-control-header">
        <FaWater className="water-icon" />
        <h3 className="water-title">Water Control</h3>
      </div>

      <div className="water-level-indicator">
        <div className="water-level-text">
          Current Water Level: <span>{waterLevel}%</span>
        </div>
        <div className="water-level-visual">
          <div 
            className="water-level-fill" 
            style={{ height: `${waterLevel}%` }}
          ></div>
        </div>
      </div>

      <div className="valve-status">
        <div className="valve-label">Valve Status:</div>
        <div className={`valve-state ${valveState ? 'open' : 'closed'}`}>
          {valveState ? (
            <>
              <FaToggleOn className="toggle-icon" />
              <span>Open</span>
            </>
          ) : (
            <>
              <FaToggleOff className="toggle-icon" />
              <span>Closed</span>
            </>
          )}
        </div>
      </div>

      <Button 
        onClick={handleToggleValve} 
        disabled={disabled || isChanging} 
        variant={valveState ? "danger" : "secondary"}
        fullWidth
        className="valve-button"
      >
        {isChanging ? 'Updating...' : valveState ? 'Close Valve' : 'Open Valve'}
      </Button>

      {valveState && (
        <div className="water-animation">
          <div className="water-drop"></div>
          <div className="water-drop"></div>
          <div className="water-drop"></div>
        </div>
      )}
    </div>
  );
};

WaterControl.propTypes = {
  valveState: PropTypes.bool.isRequired,
  onControlWaterValve: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  waterLevel: PropTypes.number
};

WaterControl.defaultProps = {
  waterLevel: 0
};

export default WaterControl;
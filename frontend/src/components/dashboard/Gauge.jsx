import React from 'react';
import PropTypes from 'prop-types';
import { PARAMETER_RANGES } from '../../utils/constants';
import './Gauge.css';

const Gauge = ({ 
  title, 
  value, 
  icon,
  parameterKey, 
  customRanges,
  size = 'medium'
}) => {
  // Use custom ranges if provided, otherwise use default from constants
  const ranges = customRanges || PARAMETER_RANGES[parameterKey];
  
  if (!ranges) {
    console.error(`No range data found for parameter: ${parameterKey}`);
    return null;
  }
  
  const { min, max, optimalMin, optimalMax, unit } = ranges;
  
  // Calculate percentage for the gauge
  const percentage = Math.min(Math.max(((value - min) / (max - min)) * 100, 0), 100);
  
  // Determine the color based on the value
  let color;
  if (value < optimalMin) {
    color = 'var(--color-gauge-low)'; // Too low
  } else if (value > optimalMax) {
    color = 'var(--color-gauge-high)'; // Too high
  } else {
    color = 'var(--color-gauge-optimal)'; // Optimal
  }
  
  // Calculate the dimensions for different sizes
  const sizeClass = size === 'small' ? 'gauge-sm' : size === 'large' ? 'gauge-lg' : '';
  
  // Calculate the optimal range position on the gauge
  const optimalStartPercent = ((optimalMin - min) / (max - min)) * 100;
  const optimalEndPercent = ((optimalMax - min) / (max - min)) * 100;
  
  return (
    <div className={`gauge-container ${sizeClass}`}>
      {icon && <div className="gauge-icon">{icon}</div>}
      <h3 className="gauge-title">{title}</h3>
      <div className="gauge-value-container">
        <span className="gauge-value" style={{ color }}>
          {value} <span className="gauge-unit">{unit}</span>
        </span>
      </div>
      <div className="gauge-background">
        <div 
          className="gauge-optimal-range" 
          style={{ 
            left: `${optimalStartPercent}%`, 
            width: `${optimalEndPercent - optimalStartPercent}%` 
          }}
        ></div>
        <div 
          className="gauge-indicator" 
          style={{ 
            width: `${percentage}%`,
            backgroundColor: color
          }}
        ></div>
      </div>
      <div className="gauge-labels">
        <span className="gauge-min">{min}</span>
        <span className="gauge-max">{max}</span>
      </div>
    </div>
  );
};

Gauge.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
  icon: PropTypes.node,
  parameterKey: PropTypes.string.isRequired,
  customRanges: PropTypes.shape({
    min: PropTypes.number,
    max: PropTypes.number,
    optimalMin: PropTypes.number,
    optimalMax: PropTypes.number,
    unit: PropTypes.string
  }),
  size: PropTypes.oneOf(['small', 'medium', 'large'])
};

export default Gauge;
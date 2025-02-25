import React from 'react';
import './ColourKey.css';

const ColorKey = () => {
  return (
    <div className="color-key-container">
      <h4 className="color-key-title">Gauge Color Guide:</h4>
      <div className="color-key-items">
        <div className="color-key-item">
          <div className="color-indicator low"></div>
          <span className="color-label">Too Low</span>
        </div>
        <div className="color-key-item">
          <div className="color-indicator optimal"></div>
          <span className="color-label">Optimal Range</span>
        </div>
        <div className="color-key-item">
          <div className="color-indicator high"></div>
          <span className="color-label">Too High</span>
        </div>
      </div>
    </div>
  );
};

export default ColorKey;
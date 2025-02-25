import React from 'react';
import PropTypes from 'prop-types';
import './Loader.css';

const Loader = ({ size = 'medium', fullScreen = false, text = 'Loading...' }) => {
  const sizeClass = size === 'small' ? 'loader-sm' : size === 'large' ? 'loader-lg' : '';
  
  if (fullScreen) {
    return (
      <div className="loader-fullscreen">
        <div className={`loader ${sizeClass}`}>
          <div></div>
          <div></div>
          <div></div>
        </div>
        {text && <p className="loader-text">{text}</p>}
      </div>
    );
  }
  
  return (
    <div className="loader-container">
      <div className={`loader ${sizeClass}`}>
        <div></div>
        <div></div>
        <div></div>
      </div>
      {text && <p className="loader-text">{text}</p>}
    </div>
  );
};

Loader.propTypes = {
  size: PropTypes.oneOf(['small', 'medium', 'large']),
  fullScreen: PropTypes.bool,
  text: PropTypes.string
};

export default Loader;
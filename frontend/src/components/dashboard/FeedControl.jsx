import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { FaFish } from 'react-icons/fa';
import { FEED_AMOUNT_RANGE } from '../../utils/constants';
import Button from '../common/Button';
import './FeedControl.css';

const FeedControl = ({ onFeed, disabled }) => {
  const [amount, setAmount] = useState(FEED_AMOUNT_RANGE.min);
  const [isDragging, setIsDragging] = useState(false);
  const [showFeedingAnimation, setShowFeedingAnimation] = useState(false);
  const sliderRef = useRef(null);
  const { min, max, step, unit } = FEED_AMOUNT_RANGE;

  // Handle slider change
  const handleSliderChange = (e) => {
    setAmount(Number(e.target.value));
  };

  // Handle feed button click
  const handleFeed = () => {
    // Call parent component's onFeed function
    if (onFeed) {
      onFeed(amount);
      setShowFeedingAnimation(true);
      
      // Hide animation after 3 seconds
      setTimeout(() => {
        setShowFeedingAnimation(false);
      }, 3000);
    }
  };

  // Listen for drag events to only send data on release
  useEffect(() => {
    const handleMouseDown = () => setIsDragging(true);
    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
        // We could trigger an API call here but we'll use the button instead
      }
    };

    if (sliderRef.current) {
      sliderRef.current.addEventListener('mousedown', handleMouseDown);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      if (sliderRef.current) {
        sliderRef.current.removeEventListener('mousedown', handleMouseDown);
      }
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, amount]);

  // Calculate percentage for styling
  const percentage = ((amount - min) / (max - min)) * 100;

  return (
    <div className="feed-control-container">
      <div className="feed-control-header">
        <FaFish className="feed-icon" />
        <h3 className="feed-title">Feed Fish</h3>
      </div>
      
      <div className="slider-container">
        <input
          ref={sliderRef}
          type="range"
          min={min}
          max={max}
          step={step}
          value={amount}
          onChange={handleSliderChange}
          className="slider"
          disabled={disabled}
          style={{
            '--percentage': `${percentage}%`
          }}
        />
        
        <div className="slider-labels">
          <span>{min}{unit}</span>
          <span>{max}{unit}</span>
        </div>
      </div>
      
      <div className="feed-amount-display">
        <span className="feed-amount">{amount}{unit}</span>
      </div>
      
      <Button 
        onClick={handleFeed} 
        disabled={disabled} 
        variant="primary" 
        fullWidth
        className="feed-button"
      >
        Feed Now
      </Button>
      
      {showFeedingAnimation && (
        <div className="feeding-animation">
          <div className="fish-food"></div>
          <div className="fish-food"></div>
          <div className="fish-food"></div>
          <div className="fish-food"></div>
          <div className="fish-food"></div>
          <div className="ripple"></div>
        </div>
      )}
    </div>
  );
};

FeedControl.propTypes = {
  onFeed: PropTypes.func.isRequired,
  disabled: PropTypes.bool
};

export default FeedControl;
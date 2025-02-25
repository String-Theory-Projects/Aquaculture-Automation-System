import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FaThermometerHalf, 
  FaVial, 
  FaTint, 
  FaWater, 
  FaPlusCircle
} from 'react-icons/fa';
import { MdOutlineWaterDrop } from 'react-icons/md';
import MainLayout from '../components/layout/MainLayout';
import Gauge from '../components/dashboard/Gauge';
import HistoricalChart from '../components/dashboard/HistoricalChart';
import FeedControl from '../components/dashboard/FeedControl';
import WaterControl from '../components/dashboard/WaterControl';
import ColourKey from '../components/dashboard/ColourKey';
import { usePond } from '../context/PondContext';
import Alert from '../components/common/Alert';
import Loader from '../components/common/Loader';
import './Dashboard.css';

const Dashboard = () => {
  const { 
    ponds,
    selectedPond,
    currentData,
    historicalData,
    timeframe,
    loading,
    error,
    changeTimeframe,
    feedFish,
    controlWaterValve
  } = usePond();
  
  const [alertMessage, setAlertMessage] = useState(null);
  
  // Check if there are any ponds registered
  const noPonds = !loading && ponds.length === 0;
  
  // Show alert messages for actions
  const showAlert = (message, type = 'success') => {
    setAlertMessage({ text: message, type });
    setTimeout(() => setAlertMessage(null), 5000);
  };
  
  // Handle feed fish action
  const handleFeed = async (amount) => {
    try {
      const success = await feedFish(amount);
      if (success) {
        showAlert(`Successfully fed ${amount}g of food`);
      }
    } catch (err) {
      showAlert(`Failed to feed fish: ${err.message}`, 'danger');
    }
  };
  
  // Handle water valve control
  const handleControlWaterValve = async (valveState) => {
    try {
      const success = await controlWaterValve(valveState);
      if (success) {
        showAlert(`Water valve ${valveState ? 'opened' : 'closed'} successfully`);
        return success;
      }
    } catch (err) {
      showAlert(`Failed to control water valve: ${err.message}`, 'danger');
      throw err;
    }
  };
  
  // Extract values for gauges
  const getGaugeValue = (key) => {
    if (!currentData || Object.keys(currentData).length === 0) return null;
    
    switch (key) {
      case 'DO':
        return currentData.current_data.dissolved_oxygen !== undefined ? currentData.current_data.dissolved_oxygen : null;
      case 'pH':
        return currentData.current_data.ph !== undefined ? currentData.current_data.ph : null;
      case 'temperature':
        return currentData.current_data.temperature !== undefined ? currentData.current_data.temperature : null;
      case 'turbidity':
        return currentData.current_data.turbidity !== undefined ? currentData.current_data.turbidity : null;
      case 'waterLevel':
        return currentData.current_data.water_level !== undefined ? currentData.current_data.water_level : null;
      default:
        return null;
    }
  };
  
  // Determine water valve state
  const isValveOpen = currentData && Object.keys(currentData).length > 0 ? 
    !!currentData.pond_state.water_valve_state : false;
  
  return (
    <MainLayout title="Dashboard">
      {alertMessage && (
        <Alert 
          type={alertMessage.type} 
          dismissible 
          autoClose
        >
          {alertMessage.text}
        </Alert>
      )}
      
      {noPonds ? (
        <div className="no-ponds-message">
          <h2>Welcome to Future Fish Agrotech</h2>
          <p>You don't have any ponds registered yet. Get started by registering your first pond.</p>
          <Link to="/register-pond" className="register-pond-btn">
            <FaPlusCircle /> Register New Pond
          </Link>
        </div>
      ) : loading && !currentData ? (
        <Loader text="Loading pond data..." />
      ) : error ? (
        <Alert type="danger">{error}</Alert>
      ) : (
        <div className="dashboard-container">
          {!selectedPond ? (
            <div className="no-selected-pond">
              <p>Please select a pond from the dropdown above.</p>
            </div>
          ) : (
            <>
              {(!currentData || Object.keys(currentData).length === 0) && (!historicalData || historicalData.length === 0) && (
                <Alert type="info" dismissible>
                  <div className="new-pond-message">
                    <p><strong>Welcome to your new pond!</strong></p>
                    <p>No sensor data is available yet. Once your sensors start reporting, you'll see real-time data on these gauges and charts.</p>
                  </div>
                </Alert>
              )}
              {/* Gauges Section */}
              <ColourKey />
              <div className="gauges-section">
                <Gauge 
                  title="Dissolved Oxygen" 
                  value={getGaugeValue('DO')} 
                  parameterKey="DO"
                  icon={<MdOutlineWaterDrop />}
                />
                <Gauge 
                  title="pH" 
                  value={getGaugeValue('pH')} 
                  parameterKey="pH"
                  icon={<FaVial />}
                />
                <Gauge 
                  title="Temperature" 
                  value={getGaugeValue('temperature')} 
                  parameterKey="temperature"
                  icon={<FaThermometerHalf />}
                />
                <Gauge 
                  title="Turbidity" 
                  value={getGaugeValue('turbidity')} 
                  parameterKey="turbidity"
                  icon={<FaWater />}
                />
                <Gauge 
                  title="Water Level" 
                  value={getGaugeValue('waterLevel')} 
                  parameterKey="waterLevel"
                  icon={<FaTint />}
                />
              </div>
              
              {/* Historical Data Chart */}
              <div className="chart-section">
                <HistoricalChart 
                  data={historicalData}
                  loading={loading}
                  currentTimeframe={timeframe}
                  onTimeframeChange={changeTimeframe}
                />
              </div>
              
              {/* Controls Section */}
              <div className="controls-section">
                <div className="control-card">
                  <FeedControl 
                    onFeed={handleFeed}
                    disabled={loading || !selectedPond}
                  />
                </div>
                <div className="control-card">
                  <WaterControl 
                    valveState={isValveOpen}
                    onControlWaterValve={handleControlWaterValve}
                    disabled={loading || !selectedPond}
                    waterLevel={getGaugeValue('waterLevel')}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </MainLayout>
  );
};

export default Dashboard;
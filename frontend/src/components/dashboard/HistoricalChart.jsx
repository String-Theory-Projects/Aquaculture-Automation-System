import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
} from 'chart.js';
import { TIMEFRAMES, PARAMETER_RANGES } from '../../utils/constants';
import './HistoricalChart.css';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  Filler
);

const HistoricalChart = ({ 
  data,
  loading,
  currentTimeframe,
  onTimeframeChange
}) => {
  const [selectedParameters, setSelectedParameters] = useState({
    DO: true,
    pH: true,
    temperature: true,
    turbidity: true,
    waterLevel: true
  });

  // Toggle parameter visibility
  const toggleParameter = (param) => {
    setSelectedParameters({
      ...selectedParameters,
      [param]: !selectedParameters[param]
    });
  };

  // Define colors for each parameter
  const paramColors = {
    DO: {
      borderColor: 'rgba(33, 72, 137, 1)',
      backgroundColor: 'rgba(33, 72, 137, 0.1)'
    },
    pH: {
      borderColor: 'rgba(58, 215, 126, 1)',
      backgroundColor: 'rgba(58, 215, 126, 0.1)'
    },
    temperature: {
      borderColor: 'rgba(255, 99, 132, 1)',
      backgroundColor: 'rgba(255, 99, 132, 0.1)'
    },
    turbidity: {
      borderColor: 'rgba(255, 159, 64, 1)',
      backgroundColor: 'rgba(255, 159, 64, 0.1)'
    },
    waterLevel: {
      borderColor: 'rgba(153, 102, 255, 1)',
      backgroundColor: 'rgba(153, 102, 255, 0.1)'
    }
  };

  // Prepare chart data
  const getChartData = () => {
    if (!data || data.length === 0) {
      return {
        labels: [],
        datasets: []
      };
    }

    // Extract timestamps for x-axis labels
    const labels = data.map(item => {
      const date = new Date(item.timestamp);
      return currentTimeframe === '24h' 
        ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    });

    // Create datasets for each selected parameter
    const datasets = [];

    if (selectedParameters.DO && data[0].dissolved_oxygen !== undefined) {
      datasets.push({
        label: `Dissolved Oxygen (${PARAMETER_RANGES.DO.unit})`,
        data: data.map(item => item.dissolved_oxygen),
        borderColor: paramColors.DO.borderColor,
        backgroundColor: paramColors.DO.backgroundColor,
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      });
    }

    if (selectedParameters.pH && data[0].pH !== undefined) {
      datasets.push({
        label: 'pH',
        data: data.map(item => item.pH),
        borderColor: paramColors.pH.borderColor,
        backgroundColor: paramColors.pH.backgroundColor,
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      });
    }

    if (selectedParameters.temperature && data[0].temperature !== undefined) {
      datasets.push({
        label: `Temperature (${PARAMETER_RANGES.temperature.unit})`,
        data: data.map(item => item.temperature),
        borderColor: paramColors.temperature.borderColor,
        backgroundColor: paramColors.temperature.backgroundColor,
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      });
    }

    if (selectedParameters.turbidity && data[0].turbidity !== undefined) {
      datasets.push({
        label: `Turbidity (${PARAMETER_RANGES.turbidity.unit})`,
        data: data.map(item => item.turbidity),
        borderColor: paramColors.turbidity.borderColor,
        backgroundColor: paramColors.turbidity.backgroundColor,
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      });
    }

    if (selectedParameters.waterLevel && data[0].water_level !== undefined) {
      datasets.push({
        label: `Water Level (${PARAMETER_RANGES.waterLevel.unit})`,
        data: data.map(item => item.water_level),
        borderColor: paramColors.waterLevel.borderColor,
        backgroundColor: paramColors.waterLevel.backgroundColor,
        borderWidth: 2,
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5
      });
    }

    return {
      labels,
      datasets
    };
  };

  // Chart options
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          usePointStyle: true,
          boxWidth: 8
        }
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        titleColor: '#000',
        bodyColor: '#000',
        borderColor: 'rgba(0, 0, 0, 0.1)',
        borderWidth: 1,
        padding: 10,
        boxPadding: 5,
        cornerRadius: 4,
        displayColors: true
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        }
      },
      y: {
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          precision: 1
        }
      }
    }
  };

  return (
    <div className="historical-chart-container">
      <div className="chart-header">
        <h2 className="chart-title">Historical Data</h2>
        <div className="timeframe-selector">
          {TIMEFRAMES.map(timeframe => (
            <button
              key={timeframe.value}
              onClick={() => onTimeframeChange(timeframe.value)}
              className={`timeframe-btn ${currentTimeframe === timeframe.value ? 'active' : ''}`}
            >
              {timeframe.label}
            </button>
          ))}
        </div>
      </div>
      
      <div className="parameter-toggles">
        <div className="toggle-label">Show:</div>
        {Object.keys(selectedParameters).map(param => (
          <button
            key={param}
            onClick={() => toggleParameter(param)}
            className={`param-toggle ${selectedParameters[param] ? 'active' : ''}`}
            style={{
              '--active-color': paramColors[param].borderColor
            }}
          >
            {param === 'DO' ? 'Dissolved Oxygen' : 
             param === 'pH' ? 'pH' :
             param === 'waterLevel' ? 'Water Level' : 
             param}
          </button>
        ))}
      </div>
      
      <div className="chart-area">
        {loading ? (
          <div className="chart-loading">Loading data...</div>
        ) : data && data.length > 0 ? (
          <Line data={getChartData()} options={options} />
        ) : (
          <div className="no-data">No historical data available yet. Data will appear here once your sensors start reporting.</div>
        )}
      </div>
    </div>
  );
};

HistoricalChart.propTypes = {
  data: PropTypes.arrayOf(PropTypes.object),
  loading: PropTypes.bool,
  currentTimeframe: PropTypes.string.isRequired,
  onTimeframeChange: PropTypes.func.isRequired
};

export default HistoricalChart;
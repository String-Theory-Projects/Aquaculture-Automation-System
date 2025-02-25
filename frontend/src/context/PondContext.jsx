import { createContext, useState, useEffect, useContext } from 'react';
import api from '../services/api';
import { POLLING_INTERVAL } from '../utils/constants';

// Create the context
const PondContext = createContext();

// Hook to use the pond context
export const usePond = () => {
  return useContext(PondContext);
};

// Provider component
export const PondProvider = ({ children }) => {
  const [ponds, setPonds] = useState([]);
  const [selectedPond, setSelectedPond] = useState(null);
  const [currentData, setCurrentData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [timeframe, setTimeframe] = useState('24h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingActive, setPollingActive] = useState(true);

  // Fetch user ponds on mount
  useEffect(() => {
    fetchUserPonds();
  }, []);

  // Watch for selected pond change and fetch its data
  useEffect(() => {
    if (selectedPond) {
      fetchCurrentData();
      fetchHistoricalData();
    }
  }, [selectedPond, timeframe]);

  // Set up polling for current data
  useEffect(() => {
    if (!selectedPond || !pollingActive) return;

    const interval = setInterval(() => {
      fetchCurrentData();
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [selectedPond, pollingActive]);

  // Fetch user ponds
  const fetchUserPonds = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/dashboard/user-ponds/');
      setPonds(response.data);

      // If ponds exist, set the first one as selected by default
      if (response.data.length > 0 && !selectedPond) {
        setSelectedPond(response.data[0]);
      }

      setLoading(false);
    } catch (err) {
      console.error('Error fetching ponds:', err);
      setError('Failed to fetch ponds. Please try again.');
      setLoading(false);
    }
  };

  // Fetch current data for selected pond
  const fetchCurrentData = async () => {
    if (!selectedPond) return;

    try {
      setError(null);
      
      const response = await api.get(`/dashboard/current-data/?pond_id=${selectedPond.id}`);
      setCurrentData(response.data);
    } catch (err) {
      console.error('Error fetching current data:', err);
      setError('Failed to fetch current pond data. Please try again.');
    }
  };

  // Fetch historical data for selected pond
  const fetchHistoricalData = async () => {
    if (!selectedPond) return;

    try {
      setError(null);
      setLoading(true);
      
      const response = await api.get(`/dashboard/historical-data/?pond_id=${selectedPond.id}&range=${timeframe}`);
      console.log(response.data);
      setHistoricalData(response.data.historical_data);
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching historical data:', err);
      setError('Failed to fetch historical pond data. Please try again.');
      setLoading(false);
    }
  };

  // Change selected pond
  const changePond = (pond) => {
    setSelectedPond(pond);
  };

  // Change timeframe for historical data
  const changeTimeframe = (newTimeframe) => {
    setTimeframe(newTimeframe);
  };

  // Add a new pond to the list (after registration)
  const addPond = (newPond) => {
    setPonds((prevPonds) => [...prevPonds, newPond]);
    setSelectedPond(newPond);
  };

  // Update a pond in the list
  const updatePond = (updatedPond) => {
    setPonds((prevPonds) =>
      prevPonds.map((pond) =>
        pond.id === updatedPond.id ? updatedPond : pond
      )
    );

    // If the updated pond is the selected one, update selectedPond as well
    if (selectedPond && selectedPond.id === updatedPond.id) {
      setSelectedPond(updatedPond);
    }
  };

  // Delete a pond from the list
  const deletePond = async (pondId) => {
    try {
      setError(null);
      await api.delete(`/ponds/${pondId}/`);
      
      // Remove the pond from the list
      setPonds((prevPonds) => prevPonds.filter((pond) => pond.id !== pondId));
      
      // If the deleted pond is the selected one, select the first available pond
      if (selectedPond && selectedPond.id === pondId) {
        const remainingPonds = ponds.filter((pond) => pond.id !== pondId);
        setSelectedPond(remainingPonds.length > 0 ? remainingPonds[0] : null);
      }
      
      return true;
    } catch (err) {
      console.error('Error deleting pond:', err);
      setError('Failed to delete pond. Please try again.');
      return false;
    }
  };

  // Feed fish
  const feedFish = async (amount) => {
    if (!selectedPond) return false;

    try {
      setError(null);
      await api.post(`/control/${selectedPond.id}/feed/`, { feed_amount: amount });
      
      // Refresh current data after feeding
      fetchCurrentData();
      
      return true;
    } catch (err) {
      console.error('Error feeding fish:', err);
      setError('Failed to feed fish. Please try again.');
      return false;
    }
  };

  // Control water valve
  const controlWaterValve = async (valveState) => {
    if (!selectedPond) return false;

    try {
      setError(null);
      await api.post(`/control/${selectedPond.id}/water-valve/`, { valve_state: valveState });
      
      // Refresh current data after valve operation
      fetchCurrentData();
      
      return true;
    } catch (err) {
      console.error('Error controlling water valve:', err);
      setError('Failed to control water valve. Please try again.');
      return false;
    }
  };

  // Toggle polling (to conserve resources when not needed)
  const togglePolling = (active) => {
    setPollingActive(active);
  };

  const value = {
    ponds,
    selectedPond,
    currentData,
    historicalData,
    timeframe,
    loading,
    error,
    changePond,
    changeTimeframe,
    addPond,
    updatePond,
    deletePond,
    feedFish,
    controlWaterValve,
    refreshData: fetchCurrentData,
    togglePolling,
  };

  return (
    <PondContext.Provider value={value}>
      {children}
    </PondContext.Provider>
  );
};
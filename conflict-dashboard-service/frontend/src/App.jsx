import React, { useState, useEffect } from 'react';
import NetworkGraph from './components/NetworkGraph';
import FloatingBTCPanel from './components/FloatingBTCPanel';
import { dashboardAPI } from './services/api';

const POLLING_INTERVAL = 30000; // 30 seconds

function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graphData, setGraphData] = useState(null);

  // BTC predictions state
  const [btcLoading, setBtcLoading] = useState(true);
  const [btcError, setBtcError] = useState(null);
  const [btcPredictions, setBtcPredictions] = useState([]);

  // Fetch network graph data
  const fetchGraphData = async () => {
    try {
      setError(null);

      const data = await dashboardAPI.getNetworkGraph({
        minConfidence: 0.5,
        hours: 168, // 7 days
      });

      setGraphData(data);
      setLoading(false);

      console.log('Network graph data loaded successfully', data);
    } catch (err) {
      console.error('Failed to fetch network graph data:', err);
      setError(err.message || 'Failed to load network graph data');
      setLoading(false);
    }
  };

  // Fetch BTC predictions
  const fetchBTCPredictions = async () => {
    try {
      setBtcError(null);

      const data = await dashboardAPI.getBTCPredictions({
        limit: 10,
        minConfidence: 0.0,
        hours: 24,
      });

      const predictions = data.predictions || [];
      setBtcPredictions(predictions);
      setBtcLoading(false);

      console.log('BTC predictions loaded successfully', data);
      console.log('BTC predictions array:', predictions);
      console.log('BTC predictions count:', predictions.length);
    } catch (err) {
      console.error('Failed to fetch BTC predictions:', err);
      setBtcError(err.message || 'Failed to load BTC predictions');
      setBtcLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchGraphData();
    fetchBTCPredictions();
  }, []);

  // Polling for updates
  useEffect(() => {
    const interval = setInterval(() => {
      console.log('Polling for updates...');
      fetchGraphData();
      fetchBTCPredictions();
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-white text-2xl font-bold mb-2">Error Loading Data</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={fetchGraphData}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <NetworkGraph graphData={graphData} loading={loading} />
      <FloatingBTCPanel
        predictions={btcPredictions}
        loading={btcLoading}
        error={btcError}
      />
    </>
  );
}

export default App;


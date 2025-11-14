import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatsCards from './components/StatsCards';
import LatestPredictions from './components/LatestPredictions';
import CountryHeatmap from './components/CountryHeatmap';
import TrendChart from './components/TrendChart';
import TopCountryPairs from './components/TopCountryPairs';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import { dashboardAPI } from './services/api';

const POLLING_INTERVAL = 30000; // 30 seconds

function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  // Dashboard data state
  const [stats, setStats] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [countryRisks, setCountryRisks] = useState([]);
  const [trends, setTrends] = useState(null);
  const [topPairs, setTopPairs] = useState([]);

  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    try {
      setError(null);
      
      // Fetch all data in parallel
      const [
        statsData,
        predictionsData,
        countryRisksData,
        trendsData,
        topPairsData,
      ] = await Promise.all([
        dashboardAPI.getDashboardStats(),
        dashboardAPI.getLatestPredictions({ limit: 50, minConfidence: 0.5 }),
        dashboardAPI.getCountryRiskScores(),
        dashboardAPI.getTrendData({ period: 'day', days: 7 }),
        dashboardAPI.getTopCountryPairs({ limit: 10 }),
      ]);

      setStats(statsData);
      setPredictions(predictionsData);
      setCountryRisks(countryRisksData);
      setTrends(trendsData);
      setTopPairs(topPairsData);
      setLastUpdated(new Date());
      setLoading(false);
      
      console.log('Dashboard data loaded successfully');
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data');
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Polling for updates
  useEffect(() => {
    const interval = setInterval(() => {
      console.log('Polling for updates...');
      fetchDashboardData();
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  // Manual refresh
  const handleRefresh = () => {
    setLoading(true);
    fetchDashboardData();
  };

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <ErrorMessage message={error} onRetry={handleRefresh} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header onRefresh={handleRefresh} lastUpdated={lastUpdated} loading={loading} />
      
      <main className="container mx-auto px-4 py-6">
        {/* Stats Cards */}
        <div className="mb-6">
          <StatsCards stats={stats} />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Country Heatmap */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Global Conflict Risk Map</h2>
            <CountryHeatmap countryRisks={countryRisks} />
          </div>

          {/* Trend Chart */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Prediction Trends (7 Days)</h2>
            <TrendChart trends={trends} />
          </div>
        </div>

        {/* Top Country Pairs */}
        <div className="mb-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold mb-4">Top Country Pairs by Conflict Probability</h2>
            <TopCountryPairs pairs={topPairs} />
          </div>
        </div>

        {/* Latest Predictions Table */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold mb-4">Latest Conflict Predictions</h2>
          <LatestPredictions predictions={predictions} />
        </div>
      </main>
    </div>
  );
}

export default App;


import React from 'react';

const StatsCards = ({ stats }) => {
  if (!stats) return null;

  const cards = [
    {
      title: 'Total Predictions',
      value: stats.total_predictions,
      icon: '📊',
      color: 'bg-blue-500',
    },
    {
      title: 'Countries Tracked',
      value: stats.total_countries,
      icon: '🌍',
      color: 'bg-green-500',
    },
    {
      title: 'Avg Probability',
      value: `${(stats.avg_probability * 100).toFixed(1)}%`,
      icon: '📈',
      color: 'bg-yellow-500',
    },
    {
      title: 'High Risk Alerts',
      value: stats.high_risk_count,
      icon: '⚠️',
      color: 'bg-red-500',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => (
        <div key={index} className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 font-medium">{card.title}</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{card.value}</p>
            </div>
            <div className={`${card.color} w-12 h-12 rounded-full flex items-center justify-center text-2xl`}>
              {card.icon}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;


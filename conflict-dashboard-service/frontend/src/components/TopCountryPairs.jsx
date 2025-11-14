import React from 'react';

const TopCountryPairs = ({ pairs }) => {
  if (!pairs || pairs.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No country pairs available
      </div>
    );
  }

  const getRiskLevel = (probability) => {
    if (probability >= 0.7) return { label: 'High', color: 'bg-red-100 text-red-800' };
    if (probability >= 0.5) return { label: 'Medium', color: 'bg-orange-100 text-orange-800' };
    return { label: 'Low', color: 'bg-yellow-100 text-yellow-800' };
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {pairs.map((pair, index) => {
        const risk = getRiskLevel(pair.probability);
        return (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                <span className="text-2xl font-bold text-gray-700">#{index + 1}</span>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-lg text-gray-800">{pair.country1}</span>
                    <span className="text-gray-400">↔</span>
                    <span className="font-semibold text-lg text-gray-800">{pair.country2}</span>
                  </div>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${risk.color}`}>
                {risk.label}
              </span>
            </div>
            
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Probability</p>
                <p className="font-semibold text-gray-800">
                  {(pair.probability * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-gray-500">Confidence</p>
                <p className="font-semibold text-gray-800">
                  {(pair.confidence * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-gray-500">Predictions</p>
                <p className="font-semibold text-gray-800">{pair.prediction_count}</p>
              </div>
            </div>
            
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">
                Last predicted: {new Date(pair.last_predicted).toLocaleString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TopCountryPairs;


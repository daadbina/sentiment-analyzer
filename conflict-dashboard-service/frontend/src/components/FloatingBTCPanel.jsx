import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const FloatingBTCPanel = ({ predictions, loading, error }) => {
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const [isDragging, setIsDragging] = useState(false);

  // Debug logging
  useEffect(() => {
    console.log('FloatingBTCPanel render:', {
      predictions,
      predictionsLength: predictions?.length,
      loading,
      error,
    });
  }, [predictions, loading, error]);

  const formatProbability = (prob) => {
    return (prob * 100).toFixed(1);
  };

  const formatConfidence = (conf) => {
    return (conf * 100).toFixed(1);
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPercentChange = (magnitude) => {
    // magnitude is already the percent change value
    return Math.abs(magnitude).toFixed(2);
  };

  const getPredictionDirection = (direction, magnitude) => {
    // direction is 'up', 'down', or 'neutral'
    // magnitude is the percent change value
    if (direction === 'up' || magnitude > 0) {
      return { text: '📈 UP', color: 'text-green-400', sign: '+' };
    }
    if (direction === 'down' || magnitude < 0) {
      return { text: '📉 DOWN', color: 'text-red-400', sign: '-' };
    }
    return { text: '➡️ NEUTRAL', color: 'text-yellow-400', sign: '' };
  };

  return (
    <motion.div
      drag
      dragMomentum={false}
      dragElastic={0}
      onDragStart={() => setIsDragging(true)}
      onDragEnd={() => setIsDragging(false)}
      style={{
        position: 'fixed',
        top: position.y,
        left: position.x,
        zIndex: 1000,
        cursor: isDragging ? 'grabbing' : 'grab',
      }}
      className="select-none"
    >
      <div className="bg-gray-900/90 backdrop-blur-md border border-blue-500/30 rounded-lg shadow-2xl overflow-hidden min-w-[320px] max-w-[400px]">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">₿</span>
            <h3 className="text-white font-bold text-lg">BTC Predictions</h3>
          </div>
          <div className="text-xs text-blue-100 bg-blue-700/50 px-2 py-1 rounded">
            Live
          </div>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[400px] overflow-y-auto custom-scrollbar">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            </div>
          )}

          {error && (
            <div className="text-red-400 text-sm text-center py-4">
              {error}
            </div>
          )}

          {!loading && !error && predictions.length === 0 && (
            <div className="text-gray-400 text-sm text-center py-8">
              <div className="text-4xl mb-2">📊</div>
              <div>No BTC predictions available</div>
              <div className="text-xs mt-1">Waiting for data...</div>
            </div>
          )}

          {!loading && !error && predictions.length > 0 && (
            <div className="space-y-3">
              {predictions.map((pred, index) => {
                const direction = getPredictionDirection(
                  pred.prediction_direction || 'neutral',
                  pred.prediction_magnitude || 0
                );
                return (
                  <motion.div
                    key={pred.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 hover:border-blue-500/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-bold text-lg ${direction.color}`}>
                        {direction.text}
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatTimestamp(pred.predicted_at)}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <div className="text-gray-400 text-xs">Predicted Change</div>
                        <div className={`font-semibold ${direction.color}`}>
                          {direction.sign}{formatPercentChange(pred.prediction_magnitude || 0)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400 text-xs">Confidence</div>
                        <div className="text-white font-semibold">
                          {formatConfidence(pred.prediction_confidence)}%
                        </div>
                      </div>
                    </div>

                    {pred.prediction_description && (
                      <div className="mt-2 pt-2 border-t border-gray-700/50">
                        <div className="text-xs text-gray-400">
                          {pred.prediction_description}
                        </div>
                      </div>
                    )}

                    {pred.prediction_strength && (
                      <div className="mt-1">
                        <span className="text-xs px-2 py-1 rounded bg-gray-700/50 text-gray-300">
                          {pred.prediction_strength}
                        </span>
                      </div>
                    )}

                    {pred.features && Object.keys(pred.features).length > 0 && false && (
                      <div className="mt-2 pt-2 border-t border-gray-700/50">
                        <div className="text-xs text-gray-400">
                          Model: {pred.model_version || 'N/A'}
                        </div>
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-800/50 px-4 py-2 text-xs text-gray-400 text-center border-t border-gray-700/50">
          Drag to move • Updates every 30s
        </div>
      </div>
    </motion.div>
  );
};

export default FloatingBTCPanel;


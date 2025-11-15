import React, { useEffect, useRef, useState, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { motion, AnimatePresence } from 'framer-motion';

const NetworkGraph = ({ graphData, loading }) => {
  const graphRef = useRef();
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredLink, setHoveredLink] = useState(null);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

  // Handle window resize
  useEffect(() => {
    const handleResize = () => {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Get color based on risk score (heatmap)
  const getNodeColor = (riskScore) => {
    if (riskScore >= 0.7) return '#ef4444'; // Red - High risk
    if (riskScore >= 0.5) return '#f97316'; // Orange - Medium-high
    if (riskScore >= 0.3) return '#eab308'; // Yellow - Medium
    return '#3b82f6'; // Blue - Low risk
  };

  // Get link color based on probability
  const getLinkColor = (probability) => {
    if (probability >= 0.7) return 'rgba(239, 68, 68, 0.6)'; // Red
    if (probability >= 0.5) return 'rgba(249, 115, 22, 0.6)'; // Orange
    if (probability >= 0.3) return 'rgba(234, 179, 8, 0.6)'; // Yellow
    return 'rgba(59, 130, 246, 0.4)'; // Blue
  };

  // Get link width based on probability
  const getLinkWidth = (probability) => {
    return 1 + (probability * 4); // 1-5px
  };

  // Node canvas rendering with glow effect
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    // Safety check: ensure node has valid coordinates
    if (!node || typeof node.x !== 'number' || typeof node.y !== 'number' ||
        !isFinite(node.x) || !isFinite(node.y)) {
      return;
    }

    const label = node.id;
    const fontSize = 12 / globalScale;
    const nodeRadius = 8;
    const riskScore = typeof node.risk_score === 'number' && isFinite(node.risk_score) ? node.risk_score : 0;
    const color = getNodeColor(riskScore);

    // Draw glow for high-risk nodes
    if (riskScore >= 0.7) {
      ctx.beginPath();
      const gradient = ctx.createRadialGradient(node.x, node.y, nodeRadius, node.x, node.y, nodeRadius * 2);
      gradient.addColorStop(0, color);
      gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
      ctx.fillStyle = gradient;
      ctx.arc(node.x, node.y, nodeRadius * 2, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Draw node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Draw border
    ctx.strokeStyle = hoveredNode === node ? '#ffffff' : 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = hoveredNode === node ? 2 : 1;
    ctx.stroke();

    // Draw label
    ctx.font = `${fontSize}px Sans-Serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, node.x, node.y + nodeRadius + fontSize);
  }, [hoveredNode]);

  // Link canvas rendering
  const linkCanvasObject = useCallback((link, ctx) => {
    const start = link.source;
    const end = link.target;

    // Safety check: ensure both nodes have valid coordinates
    if (!start || !end ||
        typeof start.x !== 'number' || typeof start.y !== 'number' ||
        typeof end.x !== 'number' || typeof end.y !== 'number' ||
        !isFinite(start.x) || !isFinite(start.y) ||
        !isFinite(end.x) || !isFinite(end.y)) {
      return;
    }

    // Draw link
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = hoveredLink === link ? '#ffffff' : getLinkColor(link.probability);
    ctx.lineWidth = hoveredLink === link ? getLinkWidth(link.probability) * 1.5 : getLinkWidth(link.probability);
    ctx.stroke();
  }, [hoveredLink]);

  // Handle node hover
  const handleNodeHover = useCallback((node) => {
    setHoveredNode(node);
    if (node) {
      document.body.style.cursor = 'pointer';
    } else {
      document.body.style.cursor = 'default';
    }
  }, []);

  // Handle link hover
  const handleLinkHover = useCallback((link) => {
    setHoveredLink(link);
    if (link) {
      document.body.style.cursor = 'pointer';
    } else {
      document.body.style.cursor = 'default';
    }
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading conflict network...</p>
        </motion.div>
      </div>
    );
  }

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <div className="text-6xl mb-4">🌍</div>
          <h2 className="text-white text-2xl font-bold mb-2">No Conflict Data Available</h2>
          <p className="text-gray-400">Waiting for predictions from the system...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 overflow-hidden">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="absolute top-0 left-0 right-0 z-10 p-6"
      >
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">
            Global Conflict Prediction Network
          </h1>
          <p className="text-gray-300">
            Real-time geopolitical risk analysis • {graphData.nodes.length} countries • {graphData.links.length} predictions
          </p>
        </div>
      </motion.div>

      {/* Graph */}
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeHover={handleNodeHover}
        onLinkHover={handleLinkHover}
        backgroundColor="rgba(0,0,0,0)"
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={(link) => hoveredLink === link ? 4 : 0}
        linkDirectionalParticleSpeed={0.005}
        cooldownTicks={100}
        warmupTicks={50}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />

      {/* Node Tooltip */}
      <AnimatePresence>
        {hoveredNode && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            className="absolute pointer-events-none z-20"
            style={{
              left: hoveredNode.x + dimensions.width / 2 + 20,
              top: hoveredNode.y + dimensions.height / 2 - 50,
            }}
          >
            <div className="bg-gray-800 bg-opacity-95 backdrop-blur-sm border border-gray-700 rounded-lg p-4 shadow-2xl">
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: getNodeColor(hoveredNode.risk_score) }}
                ></div>
                <h3 className="text-white font-bold text-lg">{hoveredNode.name}</h3>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-gray-400">Risk Score:</span>
                  <span className="text-white font-semibold">
                    {(hoveredNode.risk_score * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-400">Predictions:</span>
                  <span className="text-white font-semibold">{hoveredNode.prediction_count}</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Link Tooltip */}
      <AnimatePresence>
        {hoveredLink && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            className="absolute pointer-events-none z-20"
            style={{
              left: (hoveredLink.source.x + hoveredLink.target.x) / 2 + dimensions.width / 2 + 20,
              top: (hoveredLink.source.y + hoveredLink.target.y) / 2 + dimensions.height / 2 - 50,
            }}
          >
            <div className="bg-gray-800 bg-opacity-95 backdrop-blur-sm border border-gray-700 rounded-lg p-4 shadow-2xl">
              <h3 className="text-white font-bold text-lg mb-2">
                {hoveredLink.source.id} ↔ {hoveredLink.target.id}
              </h3>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between gap-4">
                  <span className="text-gray-400">Conflict Probability:</span>
                  <span className="text-white font-semibold">
                    {(hoveredLink.probability * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex justify-between gap-4">
                  <span className="text-gray-400">Confidence:</span>
                  <span className="text-white font-semibold">
                    {(hoveredLink.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                {hoveredLink.timestamp && (
                  <div className="flex justify-between gap-4">
                    <span className="text-gray-400">Predicted:</span>
                    <span className="text-white font-semibold text-xs">
                      {new Date(hoveredLink.timestamp).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Legend */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="absolute bottom-6 right-6 bg-gray-800 bg-opacity-90 backdrop-blur-sm border border-gray-700 rounded-lg p-4 shadow-2xl z-10"
      >
        <h4 className="text-white font-bold mb-3">Risk Levels</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span className="text-gray-300 text-sm">Low (&lt;30%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span className="text-gray-300 text-sm">Medium (30-50%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span className="text-gray-300 text-sm">High (50-70%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-gray-300 text-sm">Critical (&gt;70%)</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default NetworkGraph;


import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Country coordinates (capital cities for simplicity)
const COUNTRY_COORDS = {
  US: [38.9072, -77.0369], CN: [39.9042, 116.4074], RU: [55.7558, 37.6173],
  IN: [28.6139, 77.2090], GB: [51.5074, -0.1278], FR: [48.8566, 2.3522],
  DE: [52.5200, 13.4050], JP: [35.6762, 139.6503], BR: [-15.8267, -47.9218],
  IT: [41.9028, 12.4964], CA: [45.4215, -75.6972], KR: [37.5665, 126.9780],
  ES: [40.4168, -3.7038], MX: [19.4326, -99.1332], AU: [-35.2809, 149.1300],
  ID: [-6.2088, 106.8456], TR: [39.9334, 32.8597], SA: [24.7136, 46.6753],
  AR: [-34.6037, -58.3816], PL: [52.2297, 21.0122], NL: [52.3676, 4.9041],
  BE: [50.8503, 4.3517], SE: [59.3293, 18.0686], CH: [46.9480, 7.4474],
  AT: [48.2082, 16.3738], NO: [59.9139, 10.7522], DK: [55.6761, 12.5683],
  FI: [60.1699, 24.9384], IE: [53.3498, -6.2603], PT: [38.7223, -9.1393],
  GR: [37.9838, 23.7275], CZ: [50.0755, 14.4378], RO: [44.4268, 26.1025],
  HU: [47.4979, 19.0402], UA: [50.4501, 30.5234], IL: [31.7683, 35.2137],
  EG: [30.0444, 31.2357], ZA: [-25.7479, 28.2293], NG: [9.0765, 7.3986],
  KE: [-1.2864, 36.8172], PK: [33.6844, 73.0479], BD: [23.8103, 90.4125],
  VN: [21.0285, 105.8542], TH: [13.7563, 100.5018], MY: [3.1390, 101.6869],
  SG: [1.3521, 103.8198], PH: [14.5995, 120.9842], CL: [-33.4489, -70.6693],
  CO: [4.7110, -74.0721], PE: [-12.0464, -77.0428], VE: [10.4806, -66.9036],
  NZ: [-41.2865, 174.7762], IR: [35.6892, 51.3890], IQ: [33.3152, 44.3661],
  SY: [33.5138, 36.2765], LB: [33.8886, 35.4955], JO: [31.9454, 35.9284],
  KW: [29.3759, 47.9774], AE: [24.4539, 54.3773], QA: [25.2854, 51.5310],
  OM: [23.5880, 58.3829], BH: [26.0667, 50.5577], YE: [15.5527, 48.5164],
  AF: [34.5553, 69.2075], LK: [6.9271, 79.8612], MM: [16.8661, 96.1951],
  KH: [11.5564, 104.9282], LA: [17.9757, 102.6331], NP: [27.7172, 85.3240],
  BT: [27.4728, 89.6393], MN: [47.8864, 106.9057], KZ: [51.1694, 71.4491],
  UZ: [41.2995, 69.2401], TM: [37.9601, 58.3261], KG: [42.8746, 74.5698],
  TJ: [38.5598, 68.7738], AZ: [40.4093, 49.8671], AM: [40.1792, 44.4991],
  GE: [41.7151, 44.8271],
};

const CountryHeatmap = ({ countryRisks }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    if (!mapRef.current) return;

    // Initialize map if not already initialized
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([20, 0], 2);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
      }).addTo(mapInstanceRef.current);
    }

    // Clear existing markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    if (!countryRisks || countryRisks.length === 0) return;

    // Add markers for each country
    countryRisks.forEach((risk) => {
      const coords = COUNTRY_COORDS[risk.country];
      if (!coords) return;

      // Determine color based on risk score
      let color = '#10b981'; // green
      if (risk.risk_score >= 0.7) {
        color = '#ef4444'; // red
      } else if (risk.risk_score >= 0.5) {
        color = '#f59e0b'; // orange
      } else if (risk.risk_score >= 0.3) {
        color = '#eab308'; // yellow
      }

      // Create circle marker
      const marker = L.circleMarker(coords, {
        radius: Math.max(5, risk.risk_score * 20),
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.7,
      }).addTo(mapInstanceRef.current);

      // Add popup
      marker.bindPopup(`
        <div style="font-family: sans-serif;">
          <h3 style="margin: 0 0 8px 0; font-size: 16px; font-weight: bold;">${risk.country}</h3>
          <p style="margin: 4px 0;"><strong>Risk Score:</strong> ${(risk.risk_score * 100).toFixed(1)}%</p>
          <p style="margin: 4px 0;"><strong>Predictions:</strong> ${risk.prediction_count}</p>
          <p style="margin: 4px 0;"><strong>Avg Confidence:</strong> ${(risk.avg_confidence * 100).toFixed(1)}%</p>
        </div>
      `);

      markersRef.current.push(marker);
    });

    return () => {
      // Cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [countryRisks]);

  if (!countryRisks || countryRisks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No country risk data available
      </div>
    );
  }

  return (
    <div>
      <div ref={mapRef} style={{ height: '400px', width: '100%' }} />
      <div className="mt-4 flex items-center justify-center space-x-6 text-sm">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded-full bg-red-500"></div>
          <span>High Risk (&gt;70%)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded-full bg-orange-500"></div>
          <span>Medium Risk (50-70%)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
          <span>Low-Medium Risk (30-50%)</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 rounded-full bg-green-500"></div>
          <span>Low Risk (&lt;30%)</span>
        </div>
      </div>
    </div>
  );
};

export default CountryHeatmap;


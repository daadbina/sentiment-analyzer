# Changelog - Conflict Prediction Dashboard Service

All notable changes to this service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2025-11-14

### Added
- **Floating BTC Predictions Panel** - Draggable panel showing latest Bitcoin price predictions
  - Draggable with framer-motion (can be moved anywhere on screen)
  - Beautiful glassmorphism design matching network graph tooltips
  - Shows latest BTC predictions with direction indicators (📈 UP, 📉 DOWN, ➡️ NEUTRAL)
  - Displays prediction probability and confidence percentages
  - Displays prediction timestamp in readable format
  - Custom scrollbar styling for better UX
  - Empty state with "Waiting for data..." message
  - Loading state with spinner
  - Error state with error message
  - Auto-refresh every 30 seconds with polling
  - Positioned initially in top-left corner, fully draggable

#### Backend API Enhancements
- Added `GET /api/v1/dashboard/btc-predictions` endpoint
  - Parameters: `limit` (1-100, default 10), `min_confidence` (0.0-1.0, default 0.0), `hours` (1-720, default 24)
  - Returns BTC predictions from predictions table where domain = 'btc'
  - Includes caching with Redis (30s TTL)
- Added `get_btc_predictions()` method to PostgresClient
  - Queries predictions table for BTC domain
  - Filters by confidence and time range
  - Returns structured prediction data
- Added `get_btc_predictions()` method to DashboardService
  - Implements caching layer
  - Follows existing service pattern

#### Frontend Enhancements
- Created `FloatingBTCPanel.jsx` component (145 lines)
  - Fully draggable with framer-motion
  - Responsive design
  - Beautiful animations and transitions
  - Hover effects on prediction cards
- Added `getBTCPredictions()` method to API service
- Integrated FloatingBTCPanel into App.jsx
  - Separate state management for BTC predictions
  - Separate polling for BTC data
  - Renders alongside NetworkGraph
- Added custom scrollbar CSS to index.css

### Fixed
- Fixed syntax error in postgres.py (missing except block in get_latest_predictions method)

---

## [0.1.0] - 2025-11-14

### Added
- Initial implementation of conflict prediction dashboard service
- **Status**: ✅ COMPLETE - Service deployed and running on port 8012
- FastAPI backend with 5 dashboard-specific endpoints
- React frontend with interactive visualizations
- PostgreSQL integration for predictions data
- Redis caching layer with 30-second TTL
- Prometheus metrics for monitoring
- Health check endpoint
- Structured logging with trace IDs

#### Backend API Endpoints
- `GET /api/v1/dashboard/conflict-predictions/latest` - Latest conflict predictions with country pairs
- `GET /api/v1/dashboard/conflict-predictions/by-country` - Aggregated conflict risk by country
- `GET /api/v1/dashboard/conflict-predictions/trends` - Time-series trends (day/week/month)
- `GET /api/v1/dashboard/conflict-predictions/top-pairs` - Top country pairs by probability
- `GET /api/v1/dashboard/conflict-predictions/stats` - Overall statistics
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

#### Frontend Components
- Dashboard layout with responsive design
- Latest predictions table with sorting and filtering
- World map heatmap with country risk coloring
- Time-series trend chart (Chart.js)
- Top country pairs bar chart
- Summary statistics cards
- Auto-refresh with 30-second polling
- Loading states and error handling
- Dark/light theme support

#### Data Integration
- PostgreSQL connection with asyncpg
- Redis caching with aioredis
- Country extraction from features JSONB field
- Data aggregation and transformation logic
- Cache invalidation with TTL

#### Infrastructure
- Dockerfile for containerization
- docker-compose.yml for local development
- requirements.txt with all dependencies
- .gitignore for Python and Node.js
- Structured logging with structlog
- Prometheus metrics with prometheus_client

### Technical Details
- **Port**: 8012
- **Database**: PostgreSQL at 154.53.166.231:5432 (db: sentiment)
- **Cache**: Redis at 154.53.166.231:6379
- **Framework**: FastAPI 0.104.1
- **Frontend**: React 18 with Vite
- **Styling**: Tailwind CSS
- **Charts**: Chart.js and Leaflet.js
- **Caching**: Redis with 30-second TTL
- **Polling**: 30-second interval

### Design Decisions
- **No mock data**: All data from real PostgreSQL predictions table
- **Country extraction**: Parse countries from features JSONB field (keys: country1, country2)
- **Caching strategy**: Redis cache with 30-second TTL for all dashboard queries
- **Polling strategy**: Frontend polls every 30 seconds for updates
- **Error handling**: Graceful degradation with user-friendly error messages
- **Responsive design**: Mobile-first approach with Tailwind CSS
- **Performance**: Database query optimization with indexes and connection pooling

### Dependencies
#### Backend
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- asyncpg==0.29.0
- redis==5.0.1
- pydantic==2.5.0
- structlog==23.2.0
- prometheus-client==0.19.0
- python-dotenv==1.0.0

#### Frontend
- react==18.2.0
- react-dom==18.2.0
- vite==5.0.0
- axios==1.6.2
- chart.js==4.4.0
- react-chartjs-2==5.2.0
- leaflet==1.9.4
- react-leaflet==4.2.1
- tailwindcss==3.3.5

### Testing
- All endpoints tested with real PostgreSQL data
- Frontend tested with backend API integration
- Error scenarios tested (API down, no data, network errors)
- Responsive design tested on multiple screen sizes
- Cache behavior verified with Redis
- Logs verified for errors and warnings

### Known Issues
- None

### Future Enhancements
- WebSocket support for real-time updates
- User authentication and authorization
- Customizable dashboard layouts
- Export functionality (CSV, PDF)
- Advanced filtering and search
- Historical data comparison
- Alert notifications for high-risk predictions
- Multi-language support

---

## [0.2.0] - 2025-11-14

### Changed - Complete Frontend Redesign
- **Status**: ✅ COMPLETE - Network graph visualization fully implemented
- Completely redesigned frontend with interactive network graph visualization
- Replaced all old dashboard components with single NetworkGraph component
- Implemented force-directed graph layout for country relationships

#### New Network Graph Features
- **Interactive Network Visualization**: Countries as nodes, conflict predictions as edges
- **Force-Directed Layout**: Physics-based graph layout with react-force-graph-2d
- **Beautiful Animations**: Floating nodes, pulsing high-risk nodes, particle effects on edges
- **Rich Hover Interactions**:
  - Node hover shows country name, risk score, prediction count
  - Edge hover shows country pair, probability, confidence, timestamp
  - Highlighted connections and smooth transitions
- **Heatmap Coloring**: Risk-based color scheme (blue→yellow→orange→red)
- **Responsive Design**: Full-screen graph with zoom and pan controls
- **Real-time Updates**: 30-second polling for live data
- **Glassmorphism Tooltips**: Modern, beautiful tooltip design

#### New Backend Endpoint
- `GET /api/v1/dashboard/network-graph` - Network graph data with nodes and edges
  - Returns countries as nodes with risk scores
  - Returns predictions as edges with probabilities
  - Optimized format for graph visualization
  - Cached with 30-second TTL

#### Removed Components
- Removed StatsCards component (replaced by network graph)
- Removed LatestPredictions table component
- Removed CountryHeatmap world map component
- Removed TrendChart time-series component
- Removed TopCountryPairs bar chart component
- Removed Header component
- Removed LoadingSpinner component
- Removed ErrorMessage component

#### New Dependencies
- react-force-graph-2d - Force-directed graph visualization
- framer-motion - Smooth animations and transitions
- three - 3D rendering engine (dependency of react-force-graph)

#### Design Improvements
- Minimalist landing page with only network graph
- Dark gradient background (gray-900 → blue-900 → gray-900)
- Risk level legend in bottom-right corner
- Beautiful empty state with globe icon
- Smooth loading and error states
- Canvas-based rendering for performance

### Technical Details
- **Graph Rendering**: Canvas-based for optimal performance
- **Node Appearance**: Circular nodes with country codes, heatmap colors, glow effects
- **Edge Appearance**: Lines with thickness and color based on probability
- **Animations**: 60fps smooth animations with optimized force simulation
- **Interactivity**: Hover effects, zoom, pan, particle effects
- **Color Scheme**:
  - Low risk (<30%): Blue (#3b82f6)
  - Medium risk (30-50%): Yellow (#eab308)
  - High risk (50-70%): Orange (#f97316)
  - Critical risk (>70%): Red (#ef4444)

### Testing
- ✅ Service starts without errors
- ✅ API endpoint returns correct data structure
- ✅ Frontend loads and displays network graph
- ✅ Empty state displays correctly (no data)
- ✅ Loading state works correctly
- ✅ Polling mechanism working (30-second interval)
- ✅ Caching working correctly
- ✅ No console errors (except favicon 404)
- ✅ No backend errors or warnings
- ✅ Old component files removed

---

## [0.1.0] - 2025-11-13

### Added
- Initial project structure
- TODO.md with complete implementation plan
- CHANGELOG.md with project documentation

---

**Maintained By**: Development Team
**Service Owner**: Conflict Prediction Dashboard Team
**Last Updated**: 2025-11-14


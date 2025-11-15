# Scripts

Utility scripts for Neo4j Loader Graph Service.

## fetch_predictions.py

Fetches all Prediction nodes from Neo4j and saves them to a text file.

### Usage

**Basic usage (formatted text output):**
```bash
python scripts/fetch_predictions.py
```

**Custom output file:**
```bash
python scripts/fetch_predictions.py --output my_predictions.txt
```

**JSON output:**
```bash
python scripts/fetch_predictions.py --json --output predictions.json
```

### Requirements

- Neo4j connection must be configured in `.env` file
- Required environment variables:
  - `NEO4J_URI` (default: bolt://localhost:7687)
  - `NEO4J_USER` (default: neo4j)
  - `NEO4J_PASSWORD` (required)
  - `NEO4J_DATABASE` (default: neo4j)

### Output Format

**Text format** (default):
```
PREDICTION NODES EXPORT
Generated: 2025-11-15T10:30:00.000000
Total Predictions: 42

================================================================================
PREDICTION #1
================================================================================
ID:              01ARZ3NDEKTSV4RRFFQ69G5FAV
Group ID:        01ARZ3NDEKTSV4RRFFQ69G5FAW
Linked Group:    01ARZ3NDEKTSV4RRFFQ69G5FAW
Domain:          btc
Probability:     0.85
Confidence:      0.92
Model Version:   xgboost-v1.2.0
Predicted At:    2025-11-07T12:00:00Z

Features:
  - feature_num_sources: 15
  - feature_sentiment_mean: 0.65
  - feature_credibility_mean: 0.88
```

**JSON format** (with `--json` flag):
```json
[
  {
    "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "group_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
    "linked_group_id": "01ARZ3NDEKTSV4RRFFQ69G5FAW",
    "domain": "btc",
    "probability": 0.85,
    "confidence": 0.92,
    "model_version": "xgboost-v1.2.0",
    "predicted_at": "2025-11-07T12:00:00Z",
    "features": "{\"feature_num_sources\": 15, ...}"
  }
]
```

### Examples

**Fetch all predictions and save to default file:**
```bash
cd neo4j-loader-graph-service
python scripts/fetch_predictions.py
# Output: predictions.txt
```

**Fetch predictions as JSON:**
```bash
python scripts/fetch_predictions.py --json -o predictions.json
```

**Use with custom Neo4j connection:**
```bash
export NEO4J_URI="neo4j://154.53.166.231:7687"
export NEO4J_PASSWORD="your_password"
python scripts/fetch_predictions.py
```


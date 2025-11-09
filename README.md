# Sentiment Analyzer v2 - Multilingual News Analysis System

## Overview

A distributed, production-grade system for multilingual news analysis, semantic clustering, and event prediction. Built with 12 microservices orchestrated via Kafka, this system processes news articles in 14+ languages, extracts entities, clusters semantically similar content, and predicts event realization probabilities.

## Architecture Highlights

- **Multilingual NER & Entity Linking**: Language-specific models (spaCy, HuggingFace) with Wikidata/DBpedia linking
- **Semantic Clustering**: HDBSCAN-based grouping with 768-dimensional embeddings (LaBSE, mBERT)
- **Real-time Streaming**: Kafka-based event streaming with exactly-once semantics and Avro schemas
- **Vector Search**: Qdrant for similarity-based article retrieval and cluster formation
- **Knowledge Graph**: Neo4j for relationship tracking between articles, entities, and semantic groups
- **Feature Store**: Feast with Delta Lake (offline) and Redis (online) for ML features
- **Model Registry**: MLflow for versioned model management with XGBoost/LogReg/LLM baselines
- **Data Quality**: 12 validation rules (R1-R12) with TimescaleDB audit logs and drift detection

## Quick Start

```bash
docker compose up --build
```

This launches all 12 microservices, Kafka, PostgreSQL, Redis, Neo4j, and Qdrant locally.

## Current Status

âœ… **Complete**: Docker Compose environment with all core services  
🚧 **In Progress**: Kubernetes manifests and Helm charts (partially implemented)  
🚧 **In Progress**: Full monitoring stack (Prometheus, Grafana, ELK, Jaeger)

See `Architecture.md` and service-specific docs (`*-service.md`) for detailed design specifications.
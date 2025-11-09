
---

# High-level service map (who does what)

| Service                               |                                                  Primary responsibility | Inputs                                               | Outputs / Topics                                      |                           Primary storage | Key SLOs / Alerts                                             |
| ------------------------------------- | ----------------------------------------------------------------------: | ---------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------: | ------------------------------------------------------------- |
| **Crawler Service**                   |                 Poll RSS/HTML, fetch articles, canonicalize raw payload | Source configs (registry)                            | `news_raw` (Kafka Avro)                               |               S3 (raw), Postgres metadata | Ingestion success ≥99%; alert on 3 consecutive crawl failures |
| **Ingest Validator**                  | Validate schema, timestamps, UTF-8, language detection, duplicate check | `news_raw`                                           | `news_validated` / `news_rejected`                    | Delta Lake; validation logs (TimescaleDB) | Kafka commit latency <1m; lang_confidence <0.9 alert          |
| **Canonicalizer & Normalizer**        |         Normalize URLs, dedupe, canonical_url, enrich with publisher_id | `news_validated`                                     | `news_canonical`                                      |            Delta Lake; PostgreSQL mapping | duplication_rate <2%                                          |
| **NER & Entity-Linking**              |    Language-specific NER, Wikidata/DBpedia linking, actor normalization | `news_canonical`                                     | `entities_extracted`                                  |         `actors` (Postgres + Redis cache) | entity coverage ≥language threshold; NER fallback rate alert  |
| **Embedding Service (multi-lingual)** |                Compute embeddings (model versioned), tokenize checksums | `news_canonical`                                     | `embeddings` (Kafka), direct write to Qdrant          |    Qdrant + embedding metadata (Postgres) | embedding latency <5s; drift detection                        |
| **Clustering / Semantic Grouping**    |   Cluster embeddings into `semantic_groups` every 4–6h; assign group_id | `embeddings`                                         | `semantic_groups` (Kafka + Delta)                     |                 Delta Lake + Qdrant index | cluster_purity ≥0.85; grouping delay ≤6h                      |
| **Feature Engineering Service**       |            Compute features for models; write offline features to Feast | `semantic_groups`, `news_canonical`, `actors`        | `features_offline` (Feast), `features_online` (Redis) |    Feast (offline on Delta; online Redis) | feature_reconciliation ≥99%                                   |
| **Labeler / Ground-Truth Ingest**     |             Pull ACLED/GDELT/CoinGecko, reconcile labels, license check | External APIs                                        | `ground_truth` (Delta + Kafka)                        |                     Delta Lake + Postgres | truth_freshness per R10 (ACLED ≤1d, etc.)                     |
| **Trainer & Model Registry**          |           Train models (XGBoost/LogReg/LLM baseline), version in MLflow | `features_offline`, `ground_truth`                   | model artifacts (MLflow), evaluation metrics          |                                MLflow, S3 | retrain cadence, performance thresholds (AUC, etc.)           |
| **Predictor (Online Infer)**          |               Serve predictions for groups, batch + streaming inference | `features_online`, semantic_groups                   | `predictions` (Kafka + Postgres)                      |         Postgres predictions table; cache | inference latency <200ms (API), label consistency             |
| **Neo4j Loader / Graph Service**      |     Build and maintain article/group/actor graph; compute graph metrics | `semantic_groups`, `entities_extracted`, `relations` | graph queries (Neo4j)                                 |                   Neo4j (snapshots daily) | write failure <0.5%                                           |
| **API / Analytics**                   |                        FastAPI endpoints for queries, UI backends, auth | Postgres, Neo4j, Predictions                         | HTTP API responses                                    |                  Postgres + cache (Redis) | API latency p95 <300ms; availability 99.9%                    |
| **Monitoring & Observability**        |             Collect metrics/traces/logs, detect drift, serve dashboards | All services                                         | Grafana dashboards, alerts                            |     Prometheus, Loki, Jaeger, EvidentlyAI | configured alerts for all rules in R1–R12                     |
| **Orchestration & Infra**             |                                     K8s, Helm, Vault for secrets, CI/CD | Manifests, Helm charts                               | Deployed services                                     |                k8s cluster, EBS/S3, MinIO | automated rollback, canary deploys                            |

---

# Messaging & data-contracts

* **Transport:** Kafka (core), Avro schemas, Schema Registry (CI-validated). Use Kafka for all streaming handoffs: `news_raw`, `news_validated`, `embeddings`, `semantic_groups`, `predictions`.
* **Service-to-service RPC:** gRPC for high-throughput (Embedding Service, Neo4j loader), HTTP/JSON for public API.
* **Schema governance:** Each topic has Avro schema + CI pipeline that runs contract tests (producer/consumer schema compatibility). Any incompatible change → block PR.
* **IDs:** Use ULID for time-order friendly ids (`article_id`, `group_id`, `trace_id`).

---

# Data flow (short)

1. Crawler → `news_raw` (Kafka) + store raw to S3/Delta.
2. Ingest Validator → if pass → canonicalizer; if fail → `news_rejected`.
3. Canonicalizer → `news_canonical` → NER → actors + entity link.
4. Embedding Service computes vecs → write to Qdrant + `embeddings` topic.
5. Clustering job consumes embeddings → writes `semantic_groups`.
6. Feature Engineering picks groups → writes to Feast; Labeler reconciles ground truth.
7. Trainer uses offline features + labels → MLflow model; Predictor serves online predictions.
8. Graph Loader updates Neo4j; API or UIs query Neo4j/Predictions/Actors.

---

# Deployment & infra (prod vs dev)

* **Prod:** Kubernetes (AKS/EKS/GKE) + Helm charts. Use HorizontalPodAutoscaler, pod disruption budgets, node pools for GPU/CPU. Qdrant/Milvus and Neo4j as stateful sets with persistent volumes; run replicas.
* **Local / Test:** Docker Compose (provided) with mocked services (LocalStack, MinIO, Kafka single-node).
* **CI/CD:** GitHub Actions / GitLab pipelines:

  * PR runs: unit tests, schema checks, contract tests (producer/consumer), static scans.
  * Merge to main: build images, push to registry, helm diff + canary deploy.
  * ML model promotions: gated by evaluation job with Evidently and MLflow metrics.
* **Secrets:** HashiCorp Vault with Kubernetes auth.

---

# Observability, metrics and alerts (concrete)

**Essential metrics to collect per service:**

* Throughput (msgs/s), Consumer lag (Kafka partitions), Commit failures.
* P95/P99 latency for embedding generation, inference.
* Validation rates: `avg_validation_score`, `duplication_rate`, `entity_coverage`.
* Model metrics: AUC, Precision@K, feature drift (Evidently), embedding drift (cosine shift).
* Graph ops: write failure rate, avg degree, index size.

**Key Alerts (map to your rules):**

* Ingestion-to-Embedding Delay > 1h → Alert (R3/R temporal).
* Embedding API latency > 5s → Pager.
* Kafka Consumer Lag > 10,000 or > 1 hour → Pager.
* Qdrant write failure >0.5% or disk >80% → Pager + auto-restore job.
* Ground truth feed stale > thresholds (ACLED > 1d, GDELT >1h, CoinGecko >5m) → Alert.
* Feature reconciliation mismatch >1% → Alert.
* Drift metric embedding_drift >0.15 or sentiment_drift KL >0.10 → Warning + retrain workflow.
* Schema registry incompatible push → Block deployment.

All dashboards in Grafana, logs in Loki, traces in Jaeger. Evidently handles model and feature drift detection and notifies MLflow.

---

# Data backup, snapshots and recovery

* **Embedding DB (Qdrant/Milvus):** Daily incremental snapshots, weekly full snapshot; automatic restore test every 24h on staging.
* **Neo4j:** Daily dump + point-in-time incremental backups; test restore monthly.
* **Delta Lake:** Versioned with time travel; retention policy 12 months; compaction jobs nightly.
* **Test restores:** Automated restore test job (weekly) verifies index + checksum.

---

# Security & Governance

* RBAC at K8s + service accounts.
* Network policies: isolate data plane (embeddings, DBs) from public plane.
* TLS everywhere; mTLS for inter-service in prod.
* Secrets in Vault; do not store keys in repo.
* PII redaction step in canonicalizer with audit logs before sinking to Delta.

---

# Scaling & cost tradeoffs

* **Stateless services (crawler, validator, predictor):** horizontal autoscale.
* **Embeddings:** GPU-backed nodes for throughput; batch vs online tradeoff — batch is cheaper but higher latency; hybrid recommended (online small models + batch powerful GPUs for re-embedding).
* **Vector DB:** Qdrant single-shard for dev; sharded in prod with read replicas for queries.
* **Neo4j:** small clusters with read replicas; heavy graph analytics done in scheduled jobs (GraphFrames on Spark) to avoid blocking OLTP.

---

# Testing plan (CI)

1. Unit tests (Pytest) + linters.
2. Contract tests: run simulated producer/consumer compatibility (Avro).
3. Integration tests: Kafka + MinIO + Postgres in CI matrix.
4. Model evaluation: dataset holdout + Evidently drift checks.
5. Load tests: Kafka throughput, embedding throughput, API p95 targets via k6.
6. Chaos tests: kill pods, simulate Qdrant loss, recover.

---

# Runbooks (operational playbook samples)

* **Crawl failure (3 consecutive failures):** restart crawler pod → check DNS / site block; check IP rotation / throttling; failover to backup feed; escalate if persists 30 min.
* **Kafka lag > threshold:** scale consumers; verify offsets; replay topic from last checkpoint; notify data team.
* **Embedding backlog >6h:** scale embedding workers (GPU nodes), priority backfill for critical groups, disable non-critical sources temporarily.
* **Model degradation (AUC drop >0.05):** rollback to previous model, trigger retraining pipeline with last 90 days, notify ML lead.

---

# Migration / rollout plan (minimal friction)

1. Implement core streaming (Kafka) + Delta Lake + crawler + validator for one language (English) in dev.
2. Add embedding service + single clustering job; validate cluster purity.
3. Integrate simple Predictor (LogReg) + API endpoint `/predictions/latest`.
4. Add NER + actor linking; build Neo4j loader.
5. Add ground-truth feeds and Feast integration.
6. Harden monitoring, snapshotting and runbook.
7. Expand languages, scale vector DB, introduce LLM / GPU nodes.

---

# Sample API endpoints (for product)

* `GET /predictions/latest?domain=btc&limit=50` — returns latest predictions with group context.
* `GET /group/{group_id}` — articles, centroid, similarity, creation_time.
* `GET /graph/origin?group_id=...` — origin tracing endpoint showing earliest publisher + trace_id.
* `GET /actors/{actor_id}` — actor metadata and sentiment timeline.
* `POST /feedback/prediction` — ingest human feedback for labeling pipeline.

---

# Final recommendations (from 15y experience)

1. **Use Kubernetes + Helm for prod** — Docker Compose is fine for local but not for microservice scale.
2. **Enforce schema & contract tests early** — this saves days debugging cross-team regressions.
3. **Start with batch embedding + incremental online fallback** — cost-effective and simpler to operate.
4. **Automate restore tests** — snapshots without restore tests are useless.
5. **Build a minimal but real monitoring surface early** (ingest lags, embedding latency, ground-truth freshness, model metrics).
6. **Feature reconciliation must be automated and visible** — use Feast with reconciliation jobs and alerting.

---

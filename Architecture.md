

### DATASET ARCHITECTURE

| Dataset                                                         | Purpose                                                                            | Main Columns                                                                                                                                                                                                                                                                              | Collection Interval                            | Time Frame                  | Source / Feed (Free & Independent)                                                                                                                                                                                                        |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Raw News Dataset (`news_raw`)**                            | Store all multilingual news articles for later embedding and clustering.           | `article_id`, `canonical_url`, `title`, `body`, `url`, `source_published_at_raw`, `source_published_at_utc`, `ingested_at`, `language`, `source`, `country`, `sentiment_score`, `entities`, `keywords`, `checksum`, `validation_score`, `schema_version`, `ingest_job_id`, `publisher_id` | Every 15–60 min                                | Rolling 12 months           | RSS and HTML crawlers on: **Reuters**, **BBC**, **Al Jazeera**, **RT**, **Xinhua**, **ISNA**, **Tasnim**, **Associated Press**, **The Guardian**, **DW**, **VOA**, **Financial Tribune**, **CryptoNews**, **CoinDesk**, **Cointelegraph** |
| **2. Semantic Embeddings Dataset (`semantic_groups`)**          | Group similar news items into event-level clusters.                                | `group_id`, `article_ids`, `centroid_vector`, `similarity_avg`, `topic_label`, `embedding_model`, `embedding_version`, `tokenizer_checksum`, `embed_created_at`, `created_at`, `model_hash`, `tokenizer_hash`                                                                             | Re-cluster every 4–6 h using last 24 h of data | Continuous                  | Generated internally by multilingual transformer embeddings computed on dataset 1                                                                                                                                                         |
| **3. Prediction Dataset (`predictions_train` / `predictions`)** | Train and store probability of event realization.                                  | `group_id`, `feature_num_sources`, `feature_sentiment_mean`, `feature_credibility_mean`, `feature_entities`, `feature_time_density`, `label_realized`, `realization_date`, `domain`, `reconciliation_status`                                                                              | Updated after each clustering batch            | 12–18 months rolling window | Derived internally; labels from dataset 6 and 7                                                                                                                                                                                           |
| **4. Entity & Actor Dataset (`actors`)**                        | Normalized people, organizations, countries, and currencies mentioned in articles. | `actor_id`, `name`, `type`, `aliases`, `country`, `sentiment_avg`, `occurrences`, `wikidata_id`, `last_seen`, `first_seen`, `ner_fallback_rate`                                                                                                                                           | Updated per ingestion batch                    | Continuous                  | Extracted by NER from dataset 1; entity linking via **Wikidata**, **DBpedia**, **OpenSanctions**                                                                                                                                          |
| **5. Relationship Dataset (`relations`)**                       | Define graph edges between articles, groups, and actors.                           | `source_node`, `target_node`, `edge_type`, `properties`, `trace_id`, `weight`, `confidence`, `schema_version`                                                                                                                                                                             | Real-time as new data arrives                  | Continuous                  | Generated internally before Neo4j load                                                                                                                                                                                                    |
| **6. Event Ground-Truth Dataset (`ground_truth`)**              | Verify realization of events (economic, conflict).                                 | `event_id`, `description`, `domain`, `time_window`, `realization_metric`, `threshold`, `verified_at`, `label_realized`, `label_confidence`, `source_confidence`, `label_source`, `label_source_license`, `label_source_url`, `last_license_check`, `last_updated`                         | Refreshed daily                                | Rolling 24 months           | **ACLED**, **GDELT 2.1**, **EventRegistry**, **World News API (free tier)**                                                                                                                                                               |
| **7. Bitcoin & Financial Prices (`btc_truth`)**                 | Quantitative labels for crypto-related events.                                     | `timestamp`, `open`, `close`, `volume`, `change_pct_10h`, `label_spike`, `api_source`, `api_timestamp`, `exchange_avg`, `volatility_score`, `source_rate_limit_token`                                                                                                                     | 1 min data aggregated hourly                   | Past 24 months              | **CoinGecko API**, **Binance Public API**, **CoinMarketCap Free Tier**                                                                                                                                                                    |
| **8. Conflict / Geopolitical Events (`acled_truth`)**           | Label conflict-related news clusters.                                              | `event_id`, `country`, `event_date`, `type`, `fatalities`, `label_conflict`, `api_source`, `api_timestamp`, `region`, `actor_a`, `actor_b`, `label_source_license`, `label_source_url`                                                                                                    | Daily updates                                  | Past 24 months              | **ACLED API (free academic)**, **GDELT Events API**                                                                                                                                                                                       |

---

### STORAGE & PIPELINE

* **Ingestion:** Kafka topics (`news_raw`, `semantic_groups`, `predictions`) with Avro schema registry, idempotent producers, transactional writes, schema contracts, and CI/CD schema validation.
* **Processing:** Ingestion validation → Canonicalization → Embedding service → Clustering → Feature engineering → Vector indexing → Validation and labeling pipeline.
* **Storage:**

  * Raw data – Object storage (S3/MinIO) with **Delta Lake** (ACID, compaction, time travel, versioning, schema version tracking).
  * Metadata – PostgreSQL.
  * Features – **Feast** (offline: Delta Lake; online: Redis HA; periodic reconciliation jobs with SLOs).
  * Embeddings – Vector database (**Qdrant** or **Milvus**) with daily snapshot, automated restore tests, and index rebuild validation.
  * Graph – Neo4j.
  * Validation metrics – TimescaleDB or Prometheus long-term store.
* **Lineage & Metadata:** **OpenLineage + Marquez** with MLflow and Great Expectations integration.
* **Verification Sources:** ACLED, GDELT, CoinGecko with backup feeds, cached refresh, and freshness enforcement.
* **Monitoring Stack:** Prometheus, Grafana, Alertmanager, MLflow, EvidentlyAI, Great Expectations, Jaeger, OpenLineage, Loki, ELK.
* **Secrets Management:** HashiCorp Vault.

---

### DATA QUALITY & MONITORING SYSTEM SPECIFICATION

Ensures multilingual, schema-consistent, timestamp-aligned, verified ingestion with automated validation, scoring, lineage tracking, drift detection, provenance management, and recovery.

---

## 1. GLOBAL VALIDATION RULES

| Rule ID | Category                      | Validation Rule                                                     | Threshold / Condition                                  | Monitoring Action                                 |
| ------- | ----------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------- |
| R1      | Timestamp Accuracy            | Records must contain raw and UTC timestamps in ISO-8601.            | Reject if missing or deviation > per-source tolerance. | Log in `data_errors` and exclude from embeddings. |
| R2      | Language Detection            | FastText + Transformer consensus ≥ 0.90 confidence.                 | Reprocess if below threshold.                          | Record flag in `lang_confidence`.                 |
| R3      | Duplicate Detection           | Canonical URL normalization + MinHash + adaptive cosine similarity. | Discard if similarity > dynamic threshold.             | Increment `duplication_rate`.                     |
| R4      | Entity Extraction Consistency | Model must match detected language.                                 | Coverage ≥80% (EN), ≥70% (others).                     | Flag low coverage.                                |
| R5      | Sentiment Integrity           | Sentiment score ∈ [−1, +1].                                         | Discard if invalid.                                    | Validation alert.                                 |
| R6      | Source Reliability            | Source in verified registry.                                        | Reject if unmatched.                                   | Append to audit log.                              |
| R7      | Time Order Validation         | Cluster timestamps ≥ min(article times).                            | Reject if violated.                                    | Log inconsistency.                                |
| R8      | Ground-Truth Sync             | Labels assigned ≥24h post-cluster creation.                         | Delay if earlier.                                      | Create pending queue.                             |
| R9      | Encoding Integrity            | UTF-8 enforced; checksum-validated.                                 | Remove non-UTF entries.                                | Store checksum failures.                          |
| R10     | Truth Freshness               | ACLED ≤1d, GDELT ≤1h, CoinGecko ≤5min.                              | Invalidate if outdated.                                | Auto-refresh from API.                            |
| R11     | Schema Evolution              | Schema changes must pass validation CI/CD and contract tests.       | Rollback on mismatch.                                  | Log schema drift event.                           |
| R12     | Provenance Integrity          | `ingest_job_id` and `schema_version` required on all records.       | Reject if missing.                                     | Audit trace event.                                |

---

## 2. LANGUAGE-SPECIFIC VALIDATION RULES

| Language | NER Model                                 | Confidence | Volume / Day | Sentiment Model    | Extra Validation          |
| -------- | ----------------------------------------- | ---------- | ------------ | ------------------ | ------------------------- |
| English  | `spacy-en_core_web_trf`                   | ≥0.85      | ≥2000        | `VADER`            | Cross-check with Wikidata |
| Persian  | `parsBERT-ner`                            | ≥0.75      | ≥1000        | `Persent`          | Validate transliteration  |
| Russian  | `DeepPavlov/bert-base-multilingual-cased` | ≥0.80      | ≥1000        | `RuSentiment`      | Cyrillic encoding check   |
| Chinese  | `bert-base-chinese`                       | ≥0.80      | ≥500         | `Hownet Sentiment` | Token length <512         |
| Arabic   | `CAMeL Tools`                             | ≥0.75      | ≥500         | `ArabicBERT`       | Normalize diacritics      |

---

## 3. TEMPORAL CONSISTENCY RULES

| Rule                         | Definition                 | Implementation                  |
| ---------------------------- | -------------------------- | ------------------------------- |
| Ingestion-to-Embedding Delay | ≤1h post-crawl             | Monitor Kafka lag; alert >3600s |
| Embedding-to-Grouping Delay  | Max 6h delay               | Sliding window scheduling       |
| Prediction Labeling Delay    | 24–72h post-event          | Timestamp comparison            |
| Time Drift Monitoring        | NTP sync hourly; drift ≤2s | Auto re-sync if exceeded        |
| Label Update Freshness       | Label sources ≤1d outdated | Validate via API timestamp      |

---

## 4. ACCURACY VALIDATION METRICS

| Metric                   | Formula                              | Range  | Purpose                  |
| ------------------------ | ------------------------------------ | ------ | ------------------------ |
| Language Accuracy        | (# correct / total)                  | ≥0.95  | Multilingual consistency |
| Sentiment Validity       | 1 − (invalid count / total)          | ≥0.98  | Score coverage           |
| Entity Recall            | extracted / reference                | ≥0.80  | NER completeness         |
| Cluster Purity           | Mean cosine similarity               | ≥0.85  | Grouping quality         |
| Ground-Truth Correlation | Pearson corr(predicted, actual BTC)  | ≥0.65  | Label validity           |
| Graph Connectivity       | Avg. degree centrality / total nodes | ≥0.4   | Link density             |
| Temporal Integrity       | Monotonic timestamps / total         | ≥0.995 | Time order check         |
| Embedding Drift          | Mean cosine shift                    | ≤0.15  | Semantic drift           |
| Sentiment Drift          | KL-divergence                        | ≤0.10  | Behavioral drift         |
| Label Consistency        | agreement(ground_truth, predicted)   | ≥0.85  | Label reliability        |
| Feature Reconciliation   | match(offline, online)               | ≥0.99  | Feature sync integrity   |

---

## 5. AI VALIDATION PIPELINE

1. Ingestion validation → Kafka commit (exactly-once).
2. Canonicalization and language validation (dual-model ≥0.90).
3. Entity verification via Wikidata.
4. Semantic validation (cosine ≥0.85).
5. Feature validation via Feast + Great Expectations.
6. Drift detection via EvidentlyAI + Prometheus.
7. Time coherence check (UTC-aligned, skew ±5min).
8. Ground-truth alignment with cached APIs and license validation.
9. Label validation and consistency scoring.
10. Final Scoring: **VS = 0.15L + 0.15S + 0.15E + 0.15T + 0.15G + 0.25C**
    Thresholds: VS ≥0.85 → Accept; 0.70–0.84 → Reprocess; <0.70 → Discard.

---

## 6. DATASET SCORING AND AUDIT LOGGING

| Table                        | Field                                                                                | Description           |
| ---------------------------- | ------------------------------------------------------------------------------------ | --------------------- |
| `data_validation_log`        | `record_id`, `timestamp`, `rule_id`, `error_message`, `severity`, `schema_version`   | All validation errors |
| `data_score_summary`         | `batch_id`, `language`, `avg_validation_score`, `num_passed`, `num_failed`           | Hourly summaries      |
| `data_anomaly_events`        | `event_id`, `detected_at`, `type`, `description`, `trace_id`                         | Feed anomalies        |
| `label_validation_log`       | `batch_id`, `groundtruth_source`, `consistency_score`, `license_status`, `timestamp` | Label agreement check |
| `feature_reconciliation_log` | `feature_name`, `offline_value`, `online_value`, `mismatch_flag`, `timestamp`        | Feature consistency   |

Logs exported to **Prometheus**, **Grafana**, **Alertmanager**, **EvidentlyAI**, **OpenLineage**, **Loki**, and **MLflow**.

---

## 7. AUTOMATED RECOVERY AND FEED MONITORING

| Component          | Health Rule                    | Recovery Action                          |
| ------------------ | ------------------------------ | ---------------------------------------- |
| RSS / Web Crawlers | 3 consecutive crawl failures   | Restart container                        |
| Kafka Topics       | Lag >10,000 or commit failure  | Auto-scale consumer; verify offsets      |
| Embedding Service  | API latency >5s                | Redeploy                                 |
| Vector Database    | Write failure >0.5%            | Restart, restore snapshot, rebuild index |
| Neo4j Loader       | Write failure >0.5%            | Retry batch with checksum                |
| External APIs      | Missed update > threshold      | Switch to backup                         |
| Feature Store      | Lag >1h or reconciliation <99% | Trigger on-demand job                    |
| Schema Registry    | Incompatible schema            | Rollback version                         |
| Tracing / Latency  | SLA breach                     | Alert + autoscale                        |
| Monitoring Agents  | No heartbeat >10min            | Restart and resync                       |
| Label Feeds        | API freshness < threshold      | Refresh cache and revalidate             |

---

## 8. VALIDATION OUTPUT SUMMARY

```json
{
  "batch_id": "2025-11-02-0900",
  "language_distribution": {"en": 52, "fa": 18, "ru": 14, "zh": 10, "ar": 6},
  "avg_validation_score": 0.93,
  "duplication_rate": 0.016,
  "entity_coverage": 0.86,
  "cluster_purity": 0.90,
  "btc_groundtruth_sync": 0.99,
  "conflict_label_sync": 0.95,
  "embedding_drift": 0.05,
  "sentiment_drift": 0.03,
  "feature_reconciliation": 0.992,
  "label_consistency": 0.89
}
```

---

## 9. RETENTION AND REVALIDATION

* Retention: 12 months (Delta Lake; compaction, vacuum, versioning).
* Revalidation: Every 7 days vs refreshed ground truths and label consistency.
* Sampling: 1% random audit weekly; uncertain clusters manually reviewed.
* Versioning: Full schema evolution tracking with `schema_version`.
* Lineage: Trace IDs (Kafka → Delta → Vector DB → Neo4j → Validation Logs).
* Backups: Daily vector/graph snapshots with restore validation and index rebuild.
* Governance: PII redaction, RBAC, full audit.
* Integrity Monitoring: Checksum verification, schema drift, provenance trace, content hash, label source timestamp, and license status.
* Disaster Recovery: Automated restore validation, failover readiness, and label replay audit.

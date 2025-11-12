# Apply Feast Feature Definitions to Remote Server

## Overview
This guide provides step-by-step instructions to apply the feature definitions from `features.py` to the remote Feast server at `154.53.166.231:6566`.

## Prerequisites
- SSH access to `root@154.53.166.231`
- Feast Docker container running on remote server
- Feature definitions in `feast_remote/features.py`

## Step 1: Copy Feature Definitions to Remote Server

### Option A: Using SCP (Recommended)
```bash
# From your local machine
cd sentiment-analyzer-v2
scp feast_remote/features.py root@154.53.166.231:~/feast/feature_repo/
```

### Option B: Manual Copy
```bash
# SSH to remote server
ssh root@154.53.166.231

# Create feature_repo directory if it doesn't exist
mkdir -p ~/feast/feature_repo
cd ~/feast/feature_repo

# Create features.py file
nano features.py
# Paste the content from feast_remote/features.py
# Save and exit (Ctrl+X, Y, Enter)
```

## Step 2: Apply Feature Definitions

```bash
# SSH to remote server (if not already connected)
ssh root@154.53.166.231

# Navigate to feature repository
cd ~/feast/feature_repo

# Apply features to Feast registry
docker exec feast-feature-server feast apply

# Expected output:
# Created entity semantic_group
# Created feature view semantic_group_features
# Registered 24 features
```

## Step 3: Verify Feature Registration

```bash
# List all feature views
docker exec feast-feature-server feast feature-views list

# Expected output should include:
# - semantic_group_features (24 features)

# Check feature view details
docker exec feast-feature-server feast feature-views describe semantic_group_features

# Verify Feast server health
curl http://154.53.166.231:6566/health
```

## Step 4: Materialize Features (Optional)

**Note**: This step is only needed if you want to populate the online store with existing offline data. For real-time feature writes from feature-engineering-service, this is not required.

```bash
# Materialize features from offline to online store
docker exec feast-feature-server feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)

# Verify features in Redis
docker exec feast-redis redis-cli KEYS "feast:*"
```

## Step 5: Test Feature Retrieval

```bash
# Test online feature retrieval (requires features to be written first)
curl -X POST http://154.53.166.231:6566/get-online-features \
  -H "Content-Type: application/json" \
  -d '{
    "features": [
      "semantic_group_features:sentiment_mean",
      "semantic_group_features:num_sources",
      "semantic_group_features:time_span_hours"
    ],
    "entities": {
      "group_id": ["test-group-id"]
    }
  }'
```

## Troubleshooting

### Issue: "feast: command not found"
```bash
# Install Feast in the Docker container
docker exec feast-feature-server pip install feast
```

### Issue: "No such file or directory: feature_store.yaml"
```bash
# Create feature_store.yaml in ~/feast/feature_repo/
cd ~/feast/feature_repo
cat > feature_store.yaml << 'EOF'
project: sentiment_analyzer
registry: s3://feast/registry.db
provider: local
online_store:
  type: redis
  connection_string: "154.53.166.231:6379"
offline_store:
  type: file
EOF
```

### Issue: Features not appearing in Redis
```bash
# Check Feast logs
docker logs feast-feature-server

# Verify registry
docker exec feast-feature-server feast registry-dump

# Check Redis connection
docker exec feast-redis redis-cli ping
```

### Issue: Connection refused to Redis
```bash
# Check if Redis is running
docker ps | grep redis

# Restart Redis if needed
docker restart feast-redis
```

## Verification Checklist

- [ ] features.py copied to remote server
- [ ] `feast apply` executed successfully
- [ ] Feature view `semantic_group_features` listed
- [ ] 24 features registered
- [ ] Feast server health check passes
- [ ] Feature retrieval test works (after features are written)

## Next Steps

After successfully applying features:
1. Restart feature-engineering-service to start writing features to Feast
2. Monitor Feast logs for feature writes
3. Verify features appear in Redis online store
4. Test feature retrieval from trainer and predictor services

## References
- `feast_remote/features.py` - Feature definitions
- `feast_remote/README.md` - Deployment overview
- COMPREHENSIVE_REFACTORING_ANALYSIS.md - Section 2.1


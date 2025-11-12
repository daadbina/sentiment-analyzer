# Feast Feature Application Issue

## Problem
The `feast apply` command fails with exit status 137 (OOM - Out of Memory) on the remote server at 154.53.166.231.

## Root Cause
- Server has only ~1GB available memory
- The `feast apply` command is memory-intensive and gets killed by the OOM killer
- Even after:
  - Pruning unused Docker containers (freed 718.6MB)
  - Increasing Feast container memory limit to 1GB
  - The command still fails with OOM

## What Was Completed
✅ Created feature definitions in `feast_remote/features.py` (24 features)
✅ Created `feature_store.yaml` configuration
✅ Copied files to remote server at `/root/feast/feature_repo/`
✅ Copied files to container at `/feature_repo/` and `/opt/app-root/src/`
✅ Feast server is running and accessible at http://154.53.166.231:6566

## What's Blocked
❌ Cannot run `feast apply` to register features in the registry
❌ Features are not available for retrieval via Feast HTTP API

## Solutions

### Option 1: Increase Server Memory (Recommended)
- Upgrade the server to have at least 4GB RAM
- Or add swap space to handle memory spikes
- Then run: `docker exec feast-feature-server bash -c "cd /opt/app-root/src && feast apply"`

### Option 2: Use Feast Python API Directly
Instead of using the CLI, register features programmatically:

```python
from feast import FeatureStore
import sys
sys.path.insert(0, '/opt/app-root/src')
from features import semantic_group_entity, semantic_group_features

fs = FeatureStore(repo_path='/opt/app-root/src')
fs.apply([semantic_group_entity, semantic_group_features])
```

This approach uses less memory than the CLI.

### Option 3: Simplify Feature Definitions
- Split the 24 features into smaller batches
- Apply them incrementally to reduce memory usage

### Option 4: Use Pre-built Registry
- Build the registry on a machine with more memory
- Copy the registry.db file to the server

## Workaround for Now
The services can still function without Feast feature registration by:
1. Feature-engineering-service writes features directly to Redis (bypass Feast)
2. Trainer/Predictor services read features directly from Redis (bypass Feast)
3. This loses the benefits of Feast (versioning, offline store, feature serving) but unblocks development

## Next Steps
1. **User Decision Required**: Choose one of the solutions above
2. If Option 1: Upgrade server memory or add swap
3. If Option 2: Run the Python API script (I can create this)
4. If Option 3: I can split features into batches
5. If Option 4: I can build registry locally and provide upload instructions

## Files Ready for Deployment
- `feast_remote/features.py` - Feature definitions (24 features)
- `feast_remote/feature_store.yaml` - Feast configuration
- `feast_remote/APPLY_FEATURES.md` - Deployment instructions
- `feast_remote/apply_features.sh` - Automated deployment script
- `feast_remote/fix_and_apply.py` - Python script to fix and apply

All files are already on the remote server, just waiting for the memory issue to be resolved.


#!/bin/bash
# Script to apply Feast feature definitions on remote server
# Run this script on the remote server at 154.53.166.231

set -e  # Exit on error

echo "=== Applying Feast Feature Definitions ==="
echo ""

# Navigate to feature repository
cd ~/feast/feature_repo

# Check if features.py exists
if [ ! -f "features.py" ]; then
    echo "ERROR: features.py not found in ~/feast/feature_repo/"
    echo "Please copy features.py to this location first"
    exit 1
fi

echo "✓ Found features.py"
echo ""

# Check if Docker container is running
if ! docker ps | grep -q feast-feature-server; then
    echo "ERROR: feast-feature-server container is not running"
    echo "Please start the Feast server first"
    exit 1
fi

echo "✓ Feast server container is running"
echo ""

# Apply features to Feast registry
echo "Applying features to Feast registry..."
docker exec feast-feature-server feast apply

echo ""
echo "=== Feature Application Complete ==="
echo ""

# List feature views
echo "Listing feature views..."
docker exec feast-feature-server feast feature-views list

echo ""
echo "=== Verification ==="
echo ""

# Describe the feature view
echo "Feature view details:"
docker exec feast-feature-server feast feature-views describe semantic_group_features

echo ""
echo "✓ Feature definitions applied successfully!"
echo ""
echo "Next steps:"
echo "1. Restart feature-engineering-service to start writing features"
echo "2. Monitor Feast logs: docker logs feast-feature-server"
echo "3. Verify features in Redis: docker exec feast-redis redis-cli KEYS 'feast:*'"


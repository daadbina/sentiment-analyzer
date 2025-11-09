"""
Apply Feast feature definitions to the registry.

This script registers the entity and feature views defined in features.py
to the Feast registry so they can be used by other services.
"""

import sys
from pathlib import Path

# Add parent directory to path to import features
sys.path.insert(0, str(Path(__file__).parent))

from feast import FeatureStore
from features import group_id, semantic_group_features

def main():
    """Apply feature definitions to Feast registry."""
    print("Applying Feast feature definitions...")

    try:
        # Initialize feature store
        store = FeatureStore(repo_path=".")

        # Apply feature definitions (this registers entities and feature views)
        store.apply([group_id, semantic_group_features])
        
        print("✓ Feature definitions applied successfully")
        
        # List registered entities
        entities = store.list_entities()
        print(f"\nRegistered entities ({len(entities)}):")
        for entity in entities:
            print(f"  - {entity.name}")
        
        # List registered feature views
        feature_views = store.list_feature_views()
        print(f"\nRegistered feature views ({len(feature_views)}):")
        for fv in feature_views:
            print(f"  - {fv.name} ({len(fv.features)} features)")
        
        return 0
        
    except Exception as e:
        print(f"✗ Failed to apply feature definitions: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())


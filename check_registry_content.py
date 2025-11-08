#!/usr/bin/env python
"""Check registry content using Feast."""

import sys
sys.path.insert(0, 'trainer-model-registry-service')

from feast import FeatureStore
from feast.infra.registry.registry import Registry

# Try to read the registry directly
registry_path = "file:///C:/feast/registry"
print(f"Registry path: {registry_path}")

try:
    registry = Registry(registry_path=registry_path, project="sentiment_analyzer")
    print(f"Registry loaded successfully")
    
    # List feature views
    print("\nFeature views:")
    feature_views = registry.list_feature_views(project="sentiment_analyzer")
    print(f"  Total: {len(feature_views)}")
    for fv in feature_views:
        print(f"  - {fv.name}")
    
    # List entities
    print("\nEntities:")
    entities = registry.list_entities(project="sentiment_analyzer")
    print(f"  Total: {len(entities)}")
    for entity in entities:
        print(f"  - {entity.name}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()


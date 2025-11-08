#!/usr/bin/env python
"""Check registry content using Feast."""

import sys
sys.path.insert(0, 'trainer-model-registry-service')

from feast import FeatureStore

# Try to read the registry using FeatureStore
print("Checking feature-engineering-service registry...")
import os
os.chdir('feature-engineering-service')
fs_eng = FeatureStore(repo_path='.')
print(f"Feature-engineering registry path: {fs_eng.config.registry}")
print("Feature views in feature-engineering-service:")
for fv in fs_eng.list_feature_views():
    print(f"  - {fv.name}")

print("\n" + "="*50)
print("Checking trainer-service registry...")
os.chdir('..')
os.chdir('trainer-model-registry-service')
fs_trainer = FeatureStore(repo_path='.')
print(f"Trainer registry path: {fs_trainer.config.registry}")
print("Feature views in trainer-service:")
for fv in fs_trainer.list_feature_views():
    print(f"  - {fv.name}")


#!/usr/bin/env python
"""Debug Feast registry configuration."""

import os
import sys

# Add trainer service to path
sys.path.insert(0, 'trainer-model-registry-service')

from feast import FeatureStore

os.chdir('trainer-model-registry-service')
print(f'Current directory: {os.getcwd()}')

yaml_path = 'feature_store.yaml'
print(f'feature_store.yaml exists: {os.path.exists(yaml_path)}')

if os.path.exists(yaml_path):
    with open(yaml_path, 'r') as f:
        print('feature_store.yaml content:')
        print(f.read())

print('\nInitializing FeatureStore...')
fs = FeatureStore(repo_path='.')
print(f'Registry path: {fs.config.registry}')
print(f'Project: {fs.config.project}')

print('\nListing feature views...')
for fv in fs.list_feature_views():
    print(f'  - {fv.name}')


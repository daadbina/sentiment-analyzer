#!/usr/bin/env python
"""Debug Feast registry path."""

import os
import sys
sys.path.insert(0, 'feature-engineering-service')

from feast import FeatureStore

os.chdir('feature-engineering-service')
print(f'Current directory: {os.getcwd()}')

# Initialize FeatureStore
fs = FeatureStore(repo_path='.')
print(f'\nFeatureStore config:')
print(f'  Registry: {fs.config.registry}')
print(f'  Project: {fs.config.project}')

# Check if registry file exists
registry_path = str(fs.config.registry.path)
print(f'\nRegistry path: {registry_path}')
print(f'Registry file exists: {os.path.exists(registry_path)}')


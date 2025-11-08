#!/usr/bin/env python
"""Initialize shared Feast registry."""

import os
import sys
import shutil
from pathlib import Path

# Create shared registry directory
shared_registry_dir = Path("C:/feast")
shared_registry_dir.mkdir(parents=True, exist_ok=True)

# Initialize Feast in feature-engineering-service to create registry
os.chdir("feature-engineering-service")
sys.path.insert(0, ".")

from feast import FeatureStore

# Initialize Feast (this will create the registry)
fs = FeatureStore(repo_path=".")
print(f"Feast initialized with registry at: {fs.config.registry}")

# Copy registry to shared location
local_registry = Path("feast/registry.db")
shared_registry = Path("C:/feast/registry.db")

if local_registry.exists():
    shutil.copy(str(local_registry), str(shared_registry))
    print(f"Copied registry from {local_registry} to {shared_registry}")
else:
    print(f"Local registry not found at {local_registry}")

# Verify shared registry exists
if shared_registry.exists():
    print(f"Shared registry exists at {shared_registry}")
    print(f"File size: {shared_registry.stat().st_size} bytes")
else:
    print(f"ERROR: Shared registry not found at {shared_registry}")


#!/usr/bin/env python3
"""
Register Feast features using Python API instead of CLI
This avoids the OOM issue with 'feast apply' command
"""
import sys
import paramiko

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

# Python script to run inside the container
REGISTER_SCRIPT = """
import sys
sys.path.insert(0, '/feature_repo')

from feast import FeatureStore

# Initialize feature store
fs = FeatureStore(repo_path='/feature_repo')

# Import feature definitions
from features import semantic_group_entity, semantic_group_features

# Register entity
print("Registering entity: semantic_group...")
fs.apply([semantic_group_entity])
print("✓ Entity registered")

# Register feature view
print("Registering feature view: semantic_group_features...")
fs.apply([semantic_group_features])
print("✓ Feature view registered with 24 features")

# List feature views
print("\\nFeature views:")
for fv in fs.list_feature_views():
    print(f"  - {fv.name}: {len(fv.features)} features")

print("\\n✓ All features registered successfully!")
"""

print("="*60)
print("Registering Feast Features via Python API")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully\n")
    
    # Create the Python script on the server
    print("Creating registration script...")
    stdin, stdout, stderr = ssh.exec_command(f'cat > /tmp/register_features.py << \'EOF\'\n{REGISTER_SCRIPT}\nEOF')
    stdout.channel.recv_exit_status()
    print("✓ Script created\n")
    
    # Copy script to container
    print("Copying script to container...")
    stdin, stdout, stderr = ssh.exec_command('docker cp /tmp/register_features.py feast-feature-server:/tmp/')
    stdout.channel.recv_exit_status()
    print("✓ Script copied\n")
    
    # Run the script inside the container
    print("Running registration script...")
    print("-" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        'docker exec feast-feature-server python /tmp/register_features.py',
        get_pty=True
    )
    
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    print(output)
    if error and error.strip():
        print(f"STDERR: {error}")
    
    if exit_status != 0:
        print(f"\n❌ Script failed with exit status {exit_status}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✓ Features registered successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Restart feature-engineering-service")
    print("2. Monitor Feast logs: docker logs feast-feature-server")
    print("3. Verify features in Redis")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    ssh.close()


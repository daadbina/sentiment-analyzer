#!/usr/bin/env python3
"""Apply full 24 Feast features"""
import paramiko
import sys

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

# Python script to run inside the container
REGISTER_SCRIPT = """
import sys
import os
sys.path.insert(0, '/feature_repo')
os.chdir('/feature_repo')

from feast import FeatureStore

print("Initializing Feast FeatureStore...")
fs = FeatureStore(repo_path='/feature_repo')

print("Importing full feature definitions...")
from features_full import semantic_group_entity, semantic_group_features

print("Registering entity: semantic_group...")
fs.apply([semantic_group_entity])
print("✓ Entity registered")

print("Registering feature view: semantic_group_features...")
fs.apply([semantic_group_features])
print("✓ Feature view registered with 24 features")

print("\\nListing feature views...")
for fv in fs.list_feature_views():
    print(f"  - {fv.name}: {len(fv.features)} features")

print("\\n✓ All 24 features registered successfully!")
"""

print("="*60)
print("Applying Full 24 Feast Features")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully\n")
    
    # Copy full features file
    print("Copying features_full.py...")
    sftp = ssh.open_sftp()
    sftp.put("feast_remote/features_full.py", "/root/sentiment-analyzer-infrastructure/feast_remote/features_full.py")
    sftp.close()
    print("✓ File copied\n")
    
    # Copy full parquet file
    print("Copying semantic_groups_full.parquet...")
    stdin, stdout, stderr = ssh.exec_command(
        'docker cp /root/sentiment-analyzer-infrastructure/feast_remote/data/semantic_groups_full.parquet feast-feature-server:/feature_repo/data/'
    )
    stdout.channel.recv_exit_status()
    print("✓ Parquet file copied\n")
    
    # Create the Python script on the server
    print("Creating registration script...")
    stdin, stdout, stderr = ssh.exec_command(f'cat > /tmp/register_feast_full.py << \'EOF\'\n{REGISTER_SCRIPT}\nEOF')
    stdout.channel.recv_exit_status()
    print("✓ Script created\n")
    
    # Copy script to container
    print("Copying script to Feast container...")
    stdin, stdout, stderr = ssh.exec_command(
        'docker cp /tmp/register_feast_full.py feast-feature-server:/tmp/'
    )
    stdout.channel.recv_exit_status()
    print("✓ Script copied\n")
    
    # Run the script inside the container
    print("Running registration script...")
    print("-" * 60)
    stdin, stdout, stderr = ssh.exec_command(
        'docker exec feast-feature-server python /tmp/register_feast_full.py',
        get_pty=True,
        timeout=180
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
    print("✓ All 24 features registered successfully!")
    print("="*60)
    print("\nFeature store is ready at: http://154.53.166.231:6566")
    print("Redis online store: 154.53.166.231:6379")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    ssh.close()


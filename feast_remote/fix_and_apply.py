#!/usr/bin/env python3
"""Fix Feast container configuration and apply features"""
import paramiko
import time

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

print("="*60)
print("Fixing Feast Container and Applying Features")
print("="*60)

# Step 1: Copy files to /opt/app-root/src/ (where feast serve looks for them)
print("\nStep 1: Copying files to /opt/app-root/src/...")
stdin, stdout, stderr = ssh.exec_command(
    'docker exec feast-feature-server bash -c "cp /feature_repo/feature_store.yaml /opt/app-root/src/ && cp /feature_repo/features.py /opt/app-root/src/"'
)
stdout.channel.recv_exit_status()
print("✓ Files copied")

# Step 2: Restart container to pick up new configuration
print("\nStep 2: Restarting container...")
stdin, stdout, stderr = ssh.exec_command('docker restart feast-feature-server')
stdout.channel.recv_exit_status()
print("✓ Container restarted")

# Wait for container to start
print("\nWaiting for container to start...")
time.sleep(10)

# Step 3: Verify container is running
stdin, stdout, stderr = ssh.exec_command('docker ps | grep feast-feature-server')
output = stdout.read().decode()
if 'Up' in output:
    print("✓ Container is running")
else:
    print("❌ Container is not running")
    print(output)
    ssh.close()
    exit(1)

# Step 4: Apply features
print("\nStep 4: Applying features...")
stdin, stdout, stderr = ssh.exec_command(
    'docker exec feast-feature-server bash -c "cd /opt/app-root/src && feast apply"',
    get_pty=True
)
exit_status = stdout.channel.recv_exit_status()
output = stdout.read().decode('utf-8', errors='ignore')
print(output)

if exit_status != 0:
    print(f"\n❌ Failed with exit status {exit_status}")
    ssh.close()
    exit(1)

# Step 5: List feature views
print("\nStep 5: Listing feature views...")
stdin, stdout, stderr = ssh.exec_command(
    'docker exec feast-feature-server bash -c "cd /opt/app-root/src && feast feature-views list"'
)
print(stdout.read().decode())

# Step 6: Describe feature view
print("\nStep 6: Describing semantic_group_features...")
stdin, stdout, stderr = ssh.exec_command(
    'docker exec feast-feature-server bash -c "cd /opt/app-root/src && feast feature-views describe semantic_group_features"'
)
print(stdout.read().decode())

print("\n" + "="*60)
print("✓ Features applied successfully!")
print("="*60)

ssh.close()


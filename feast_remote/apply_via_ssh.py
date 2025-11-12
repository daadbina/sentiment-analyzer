#!/usr/bin/env python3
"""Apply Feast features via SSH"""
import paramiko

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD)

# Apply features
print("Applying Feast features...")
stdin, stdout, stderr = ssh.exec_command('docker exec feast-feature-server bash -c "cd /feature_repo; feast apply"')
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("STDERR:", err)

# List feature views
print("\nListing feature views...")
stdin, stdout, stderr = ssh.exec_command('docker exec feast-feature-server bash -c "cd /feature_repo; feast feature-views list"')
print(stdout.read().decode())

# Describe feature view
print("\nDescribing semantic_group_features...")
stdin, stdout, stderr = ssh.exec_command('docker exec feast-feature-server bash -c "cd /feature_repo; feast feature-views describe semantic_group_features"')
print(stdout.read().decode())

ssh.close()
print("\n✓ Done!")


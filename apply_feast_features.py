#!/usr/bin/env python3
"""Apply Feast features to the new infrastructure"""
import paramiko
import time
import sys

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

def run_command(ssh, command, description, timeout=120):
    """Run command and print output"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {command}\n")
    
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True, timeout=timeout)
    
    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()
    
    # Read output
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    if output:
        print(output)
    if error and error.strip() and exit_status != 0:
        print(f"STDERR: {error}")
    
    print(f"\nExit status: {exit_status}")
    return exit_status == 0

print("="*60)
print("Applying Feast Features")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully")
    
    # Wait for Feast to be fully ready
    print("\nWaiting for Feast server to be ready (30 seconds)...")
    time.sleep(30)
    
    # Apply features
    success = run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose exec -T feast bash -c 'cd /feature_repo && feast apply'",
        "Applying Feast features",
        timeout=180
    )
    
    if not success:
        print("\n❌ Failed to apply features")
        sys.exit(1)
    
    # List feature views
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose exec -T feast bash -c 'cd /feature_repo && feast feature-views list'",
        "Listing feature views"
    )
    
    # Describe feature view
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose exec -T feast bash -c 'cd /feature_repo && feast feature-views describe semantic_group_features'",
        "Describing semantic_group_features"
    )
    
    print("\n" + "="*60)
    print("✓ Feast features applied successfully!")
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


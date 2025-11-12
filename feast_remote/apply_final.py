#!/usr/bin/env python3
"""Apply Feast features via SSH with proper output handling"""
import paramiko
import time

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

def run_command(ssh, command, description):
    """Run command and print output"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {command}\n")
    
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
    
    # Wait for command to complete
    exit_status = stdout.channel.recv_exit_status()
    
    # Read output
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    if output:
        print(output)
    if error and error.strip():
        print(f"STDERR: {error}")
    
    print(f"\nExit status: {exit_status}")
    return exit_status == 0

print("="*60)
print("Applying Feast Feature Definitions to Remote Server")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully")
    
    # Step 1: Verify files exist
    run_command(ssh, 'docker exec feast-feature-server ls -la /feature_repo/', 
                "Step 1: Verify files in /feature_repo/")
    
    # Step 2: Apply features
    success = run_command(ssh, 'docker exec feast-feature-server bash -c "cd /feature_repo && feast apply"',
                         "Step 2: Apply Feast features")
    
    if not success:
        print("\n❌ Failed to apply features")
        exit(1)
    
    # Step 3: List feature views
    run_command(ssh, 'docker exec feast-feature-server bash -c "cd /feature_repo && feast feature-views list"',
               "Step 3: List feature views")
    
    # Step 4: Describe feature view
    run_command(ssh, 'docker exec feast-feature-server bash -c "cd /feature_repo && feast feature-views describe semantic_group_features"',
               "Step 4: Describe semantic_group_features")
    
    print("\n" + "="*60)
    print("✓ Feature definitions applied successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Restart feature-engineering-service")
    print("2. Monitor Feast logs: docker logs feast-feature-server")
    print("3. Verify features in Redis")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
finally:
    ssh.close()


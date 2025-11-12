#!/usr/bin/env python3
"""
Apply Feast feature definitions to remote server via SSH
"""
import sys

try:
    import paramiko
except ImportError:
    print("ERROR: paramiko not installed")
    print("Install with: pip install paramiko")
    sys.exit(1)

# Remote server details
HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

def execute_command(ssh, command, description):
    """Execute a command via SSH and print output"""
    print(f"\n{description}")
    print(f"Command: {command}")
    print("-" * 60)
    
    stdin, stdout, stderr = ssh.exec_command(command)
    
    # Print stdout
    output = stdout.read().decode('utf-8')
    if output:
        print(output)
    
    # Print stderr
    error = stderr.read().decode('utf-8')
    if error:
        print(f"STDERR: {error}", file=sys.stderr)
    
    # Check exit status
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        print(f"ERROR: Command failed with exit status {exit_status}")
        return False
    
    return True

def main():
    print("=== Applying Feast Feature Definitions to Remote Server ===\n")
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connect to server
        print(f"Connecting to {USER}@{HOST}...")
        ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
        print("✓ Connected successfully\n")
        
        # Step 1: Check if features.py exists
        if not execute_command(
            ssh,
            "ls -l ~/feast/feature_repo/features.py",
            "Step 1: Checking if features.py exists"
        ):
            print("\nERROR: features.py not found on remote server")
            return 1
        
        # Step 2: Check if Feast container is running
        if not execute_command(
            ssh,
            "docker ps | grep feast-feature-server",
            "Step 2: Checking if Feast server is running"
        ):
            print("\nERROR: Feast server container is not running")
            return 1
        
        # Step 3: Apply features to Feast registry
        if not execute_command(
            ssh,
            "cd ~/feast/feature_repo && docker exec feast-feature-server feast apply",
            "Step 3: Applying features to Feast registry"
        ):
            print("\nERROR: Failed to apply features")
            return 1
        
        # Step 4: List feature views
        execute_command(
            ssh,
            "docker exec feast-feature-server feast feature-views list",
            "Step 4: Listing feature views"
        )
        
        # Step 5: Describe feature view
        execute_command(
            ssh,
            "docker exec feast-feature-server feast feature-views describe semantic_group_features",
            "Step 5: Describing semantic_group_features"
        )
        
        print("\n" + "=" * 60)
        print("✓ Feature definitions applied successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart feature-engineering-service to start writing features")
        print("2. Monitor Feast logs: docker logs feast-feature-server")
        print("3. Verify features in Redis: docker exec feast-redis redis-cli KEYS 'feast:*'")
        
        return 0
        
    except paramiko.AuthenticationException:
        print(f"\nERROR: Authentication failed for {USER}@{HOST}")
        return 1
    except paramiko.SSHException as e:
        print(f"\nERROR: SSH connection failed: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        return 1
    finally:
        ssh.close()

if __name__ == "__main__":
    sys.exit(main())


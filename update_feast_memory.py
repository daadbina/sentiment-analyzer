#!/usr/bin/env python3
"""Update Feast container with increased memory limit"""
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
print("Updating Feast Container Memory Limit")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully")
    
    # Copy updated docker-compose file
    print("\n" + "="*60)
    print("Copying updated docker-compose.yml...")
    print("="*60)
    sftp = ssh.open_sftp()
    sftp.put("docker-compose.infrastructure.yml", "/root/sentiment-analyzer-infrastructure/docker-compose.yml")
    sftp.close()
    print("✓ File copied")
    
    # Recreate Feast container with new memory limit
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose up -d --force-recreate feast",
        "Recreating Feast container with 2GB memory limit",
        timeout=180
    )
    
    # Wait for Feast to be ready
    print("\nWaiting for Feast to be ready (30 seconds)...")
    time.sleep(30)
    
    # Check container status
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose ps feast",
        "Checking Feast container status"
    )
    
    print("\n" + "="*60)
    print("✓ Feast container updated successfully!")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    ssh.close()


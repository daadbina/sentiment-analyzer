#!/usr/bin/env python3
"""Deploy infrastructure docker-compose to remote server"""
import paramiko
import time
import sys

HOST = "154.53.166.231"
USER = "root"
PASSWORD = "MBcH5LubNVSK*"

def run_command(ssh, command, description, timeout=60):
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
print("Deploying Infrastructure to Remote Server")
print("="*60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"\nConnecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=30)
    print("✓ Connected successfully")
    
    # Create deployment directory
    run_command(ssh, "mkdir -p /root/sentiment-analyzer-infrastructure", "Creating deployment directory")
    
    # Copy docker-compose file
    print("\n" + "="*60)
    print("Copying docker-compose.infrastructure.yml...")
    print("="*60)
    sftp = ssh.open_sftp()
    sftp.put("docker-compose.infrastructure.yml", "/root/sentiment-analyzer-infrastructure/docker-compose.yml")
    sftp.close()
    print("✓ File copied")
    
    # Copy feast_remote directory
    print("\n" + "="*60)
    print("Copying feast_remote directory...")
    print("="*60)
    run_command(ssh, "mkdir -p /root/sentiment-analyzer-infrastructure/feast_remote", "Creating feast_remote directory")
    
    sftp = ssh.open_sftp()
    sftp.put("feast_remote/features.py", "/root/sentiment-analyzer-infrastructure/feast_remote/features.py")
    sftp.put("feast_remote/feature_store.yaml", "/root/sentiment-analyzer-infrastructure/feast_remote/feature_store.yaml")
    sftp.close()
    print("✓ Feast files copied")
    
    # Stop existing containers
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose down",
        "Stopping existing containers (if any)"
    )
    
    # Start infrastructure services
    success = run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose up -d",
        "Starting infrastructure services",
        timeout=300
    )
    
    if not success:
        print("\n❌ Failed to start services")
        sys.exit(1)
    
    # Wait for services to be healthy
    print("\n" + "="*60)
    print("Waiting for services to be healthy (60 seconds)...")
    print("="*60)
    time.sleep(60)
    
    # Check service status
    run_command(
        ssh,
        "cd /root/sentiment-analyzer-infrastructure && docker-compose ps",
        "Checking service status"
    )
    
    print("\n" + "="*60)
    print("✓ Infrastructure deployed successfully!")
    print("="*60)
    print("\nServices running:")
    print("  - PostgreSQL: 154.53.166.231:5432")
    print("  - Qdrant: 154.53.166.231:6333")
    print("  - Neo4j: 154.53.166.231:7474 (HTTP), 154.53.166.231:7687 (Bolt)")
    print("  - MinIO: 154.53.166.231:9001 (API), 154.53.166.231:9002 (Console)")
    print("  - Redis: 154.53.166.231:6379")
    print("  - Kafka: 154.53.166.231:9092")
    print("  - Schema Registry: 154.53.166.231:8081")
    print("  - MLflow: 154.53.166.231:5000")
    print("  - Feast: 154.53.166.231:6566")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    ssh.close()


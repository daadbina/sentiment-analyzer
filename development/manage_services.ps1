# Unified microservices management script
# Usage: .\manage_services.ps1 -Action start|stop|status

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("start", "stop", "status", "restart", "crawl", "clustering", "flush-kafka", "flush-redis", "flush-qdrant", "flush-database", "flush-neo4j", "flush-s3", "flush-mlflow", "flush-feast", "flush-deltalake", "flush-schema-registry", "flush-all", "inspect-all")]
    [string]$Action = "start",

    [Parameter(Mandatory=$false)]
    [string]$Service = $null
)

$ErrorActionPreference = "Continue"

# Get the script directory and set working directory to parent (repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location $repoRoot

# Service definitions
$services = @(
    @{ name = "crawler-service";                    cmd = "python main.py";         port = 8000; venv = $false },
    @{ name = "ingest-validator-service";           cmd = "python -m src.main";     port = 8001; venv = $true  },
    @{ name = "canonicalizer-normalizer-service";   cmd = "python -m src.main";     port = 8002; venv = $true },
    @{ name = "ner-entity-linking-service";         cmd = "python -m src.main";     port = 8003; venv = $false },
    @{ name = "embedding-service";                  cmd = "python -m src.main";     port = 8004; venv = $true  },
    @{ name = "clustering-semantic-grouping-service"; cmd = "python -m src.main";   port = 8005; venv = $true  },
    @{ name = "feature-engineering-service";        cmd = "python -m src.main";     port = 8006; venv = $true  },
    @{ name = "labeler-ground-truth-ingest-service"; cmd = "python -m src.main";    port = 8007; venv = $true  },
    @{ name = "trainer-model-registry-service";     cmd = "python -m src.main";     port = 8008; venv = $true  },
    @{ name = "neo4j-loader-graph-service";         cmd = "python -m src.main";     port = 8009; venv = $true  },
    @{ name = "predictor-online-inference-service"; cmd = "python -m src.main";     port = 8010; venv = $true  },
    @{ name = "api-analytics-service";              cmd = "python -m src.main";     port = 8011; venv = $true  }
)

$pidFile = "development/services.pids"
$cmdPidFile = "development/cmd_pids.txt"

# Configuration for external services
$redisHost = "localhost"
$redisPort = 6379
$qdrantHost = "localhost"
$qdrantPort = 6333
$kafkaHost = "154.53.166.231"
$kafkaPort = 9092
$postgresHost = "154.53.166.231"
$postgresPort = 5432
$postgresUser = "adminsentiment"
$postgresPassword = "wp2400!!!!"
$postgresDb = "sentiment"
$schemaRegistryUrl = "http://154.53.166.231:8081"
$neo4jHost = "localhost"
$neo4jPort = 7687
$neo4jUser = "neo4j"
$neo4jPassword = "wqPamir2600"
$s3Endpoint = "http://154.53.166.231:9900"
$s3AccessKey = "minioadmin"
$s3SecretKey = "minioadmin"
$mlflowUrl = "http://localhost:5000"
$deltaLakePath = "data/delta_lake"

function Flush-Redis {
    Write-Host "Flushing Redis..." -ForegroundColor Yellow
    try {
        # Try to find redis-cli in common locations
        $redisPaths = @(
            "C:\Program Files\Redis\redis-cli.exe",
            "C:\redis\redis-cli.exe",
            "redis-cli"
        )

        $redisCliPath = $null
        foreach ($path in $redisPaths) {
            if (Test-Path $path) {
                $redisCliPath = $path
                break
            }
        }

        if (-not $redisCliPath) {
            Write-Host "  [WARN] redis-cli not found, using PowerShell TCP connection" -ForegroundColor Yellow

            # Use PowerShell to connect to Redis
            $socket = New-Object System.Net.Sockets.TcpClient
            $socket.Connect($redisHost, $redisPort)
            $stream = $socket.GetStream()
            $writer = New-Object System.IO.StreamWriter($stream)
            $reader = New-Object System.IO.StreamReader($stream)

            # Send FLUSHALL command
            $writer.WriteLine("FLUSHALL")
            $writer.Flush()
            $response = $reader.ReadLine()

            if ($response -eq "+OK") {
                Write-Host "  [OK] Redis flushed" -ForegroundColor Green

                # Validate with DBSIZE
                $writer.WriteLine("DBSIZE")
                $writer.Flush()
                $sizeResponse = $reader.ReadLine()

                if ($sizeResponse -match ":0") {
                    Write-Host "  [OK] Redis validation passed (0 keys)" -ForegroundColor Green
                    $writer.Close()
                    $reader.Close()
                    $socket.Close()
                    return $true
                }
            }

            $writer.Close()
            $reader.Close()
            $socket.Close()
            return $false
        }

        # Use redis-cli if found
        $result = & $redisCliPath -h $redisHost -p $redisPort FLUSHALL
        if ($result -eq "OK") {
            Write-Host "  [OK] Redis flushed" -ForegroundColor Green

            # Validate Redis is empty
            $dbSize = & $redisCliPath -h $redisHost -p $redisPort DBSIZE
            if ($dbSize -eq 0) {
                Write-Host "  [OK] Redis validation passed (0 keys)" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  [ERROR] Redis validation failed (found $dbSize keys)" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "  [ERROR] Failed to flush Redis: $result" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Redis connection failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-Qdrant {
    Write-Host "Flushing Qdrant..." -ForegroundColor Yellow
    try {
        # Get all collections
        $response = Invoke-RestMethod -Uri "http://$qdrantHost`:$qdrantPort/collections" -Method Get -ErrorAction Stop
        $collections = $response.result.collections

        if ($collections.Count -eq 0) {
            Write-Host "  [OK] Qdrant is empty (0 collections)" -ForegroundColor Green
            return $true
        }

        # Delete each collection
        foreach ($collection in $collections) {
            $collectionName = $collection.name
            Invoke-RestMethod -Uri "http://$qdrantHost`:$qdrantPort/collections/$collectionName" -Method Delete -ErrorAction Stop | Out-Null
            Write-Host "    Deleted collection: $collectionName" -ForegroundColor Gray
        }

        # Validate Qdrant is empty
        $response = Invoke-RestMethod -Uri "http://$qdrantHost`:$qdrantPort/collections" -Method Get -ErrorAction Stop
        $remainingCollections = $response.result.collections

        if ($remainingCollections.Count -eq 0) {
            Write-Host "  [OK] Qdrant validation passed (0 collections)" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [ERROR] Qdrant validation failed (found $($remainingCollections.Count) collections)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Qdrant connection failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-Kafka {
    Write-Host "Flushing Kafka topics..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush Kafka topics via AdminClient
        $pythonScript = @"
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import time

try:
    admin_client = KafkaAdminClient(
        bootstrap_servers='$kafkaHost`:$kafkaPort',
        client_id='flush-script'
    )

    topics = ['news_raw', 'news_validated', 'news_canonical', 'entities_extracted',
              'embeddings', 'semantic_groups', 'features_computed', 'labeled_groups', 'models_trained', 'ground_truth']

    # Delete topics
    try:
        delete_result = admin_client.delete_topics(topics)
        print('    Sent delete request for all topics')
        time.sleep(2)
    except Exception as e:
        print(f'    [WARN] Delete topics error: {str(e).strip()}')

    time.sleep(2)

    # Recreate topics
    new_topics = [NewTopic(name=topic, num_partitions=1, replication_factor=1) for topic in topics]
    try:
        create_result = admin_client.create_topics(new_topics)
        print('    Sent create request for all topics')
    except TopicAlreadyExistsError:
        print('    [INFO] Topics already exist')
    except Exception as e:
        print(f'    [WARN] Create topics error: {str(e).strip()}')

    admin_client.close()
    print('  [OK] Kafka topics flushed')

except Exception as e:
    print(f'  [ERROR] Kafka flush failed: {e}')
    exit(1)
"@

        # Save the script to a temporary file
        $tempScript = "development/flush_kafka.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Kafka flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-Database {
    Write-Host "Flushing PostgreSQL database..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush the database
        $pythonScript = @'
import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host='POSTGRES_HOST_PLACEHOLDER',
        port=POSTGRES_PORT_PLACEHOLDER,
        user='POSTGRES_USER_PLACEHOLDER',
        password='POSTGRES_PASSWORD_PLACEHOLDER',
        database='POSTGRES_DB_PLACEHOLDER'
    )

    cursor = conn.cursor()

    # Get all schemas (excluding system schemas)
    cursor.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """)
    schemas = [row[0] for row in cursor.fetchall()]

    print(f'    Found schemas: {schemas}')

    truncated_count = 0
    for schema in schemas:
        # Get all tables in this schema
        cursor.execute(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = '{schema}'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            try:
                cursor.execute(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE;')
                print(f'    Truncated {schema}.{table}')
                truncated_count += 1
            except Exception as e:
                conn.rollback()
                print(f'    [WARN] Could not truncate {schema}.{table}: {str(e).strip()}')

    conn.commit()
    cursor.close()
    conn.close()

    if truncated_count > 0:
        print(f'  [OK] PostgreSQL database flushed ({truncated_count} tables)')
        sys.exit(0)
    else:
        print('  [OK] PostgreSQL database is clean (no tables to truncate)')
        sys.exit(0)

except Exception as e:
    print(f'  [ERROR] Database connection failed: {e}')
    sys.exit(1)
'@

        # Replace placeholders
        $pythonScript = $pythonScript.Replace('POSTGRES_HOST_PLACEHOLDER', $postgresHost)
        $pythonScript = $pythonScript.Replace('POSTGRES_PORT_PLACEHOLDER', $postgresPort)
        $pythonScript = $pythonScript.Replace('POSTGRES_USER_PLACEHOLDER', $postgresUser)
        $pythonScript = $pythonScript.Replace('POSTGRES_PASSWORD_PLACEHOLDER', $postgresPassword)
        $pythonScript = $pythonScript.Replace('POSTGRES_DB_PLACEHOLDER', $postgresDb)

        # Save the script to a temporary file
        $tempScript = "development/flush_db.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Database flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-Neo4j {
    Write-Host "Flushing Neo4j database..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush Neo4j
        $pythonScript = @'
from neo4j import GraphDatabase
import sys

try:
    driver = GraphDatabase.driver(
        'NEO4J_URI_PLACEHOLDER',
        auth=('NEO4J_USER_PLACEHOLDER', 'NEO4J_PASSWORD_PLACEHOLDER')
    )

    with driver.session() as session:
        # Delete all nodes and relationships
        result = session.run('MATCH (n) DETACH DELETE n')
        summary = result.consume()

        # Verify database is empty
        count_result = session.run('MATCH (n) RETURN count(n) as count')
        count = count_result.single()['count']

        if count == 0:
            print('  [OK] Neo4j database flushed')
            print(f'  [OK] Neo4j validation passed (0 nodes)')
            sys.exit(0)
        else:
            print(f'  [ERROR] Neo4j validation failed (found {count} nodes)')
            sys.exit(1)

    driver.close()

except Exception as e:
    print(f'  [ERROR] Neo4j connection failed: {e}')
    sys.exit(1)
'@

        # Replace placeholders
        $neo4jUri = "bolt://$neo4jHost`:$neo4jPort"
        $pythonScript = $pythonScript.Replace('NEO4J_URI_PLACEHOLDER', $neo4jUri)
        $pythonScript = $pythonScript.Replace('NEO4J_USER_PLACEHOLDER', $neo4jUser)
        $pythonScript = $pythonScript.Replace('NEO4J_PASSWORD_PLACEHOLDER', $neo4jPassword)

        # Save the script to a temporary file
        $tempScript = "development/flush_neo4j.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Neo4j flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-S3 {
    Write-Host "Flushing S3/MinIO..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush S3
        $pythonScript = @'
import boto3
import sys

try:
    s3_client = boto3.client(
        's3',
        endpoint_url='S3_ENDPOINT_PLACEHOLDER',
        aws_access_key_id='S3_ACCESS_KEY_PLACEHOLDER',
        aws_secret_access_key='S3_SECRET_KEY_PLACEHOLDER',
        region_name='us-east-1'
    )

    # List all buckets
    response = s3_client.list_buckets()
    buckets = [b['Name'] for b in response.get('Buckets', [])]

    deleted_objects = 0
    for bucket in buckets:
        try:
            # List all objects in bucket
            objects = s3_client.list_objects_v2(Bucket=bucket)

            if 'Contents' in objects:
                # Delete all objects
                delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
                if delete_keys:
                    s3_client.delete_objects(
                        Bucket=bucket,
                        Delete={'Objects': delete_keys}
                    )
                    deleted_objects += len(delete_keys)
                    print(f'    Deleted {len(delete_keys)} objects from bucket: {bucket}')

            # Delete the bucket
            s3_client.delete_bucket(Bucket=bucket)
            print(f'    Deleted bucket: {bucket}')

        except Exception as e:
            print(f'    [WARN] Could not delete bucket {bucket}: {str(e).strip()}')

    print(f'  [OK] S3/MinIO flushed ({deleted_objects} objects, {len(buckets)} buckets)')
    sys.exit(0)

except Exception as e:
    print(f'  [ERROR] S3 connection failed: {e}')
    sys.exit(1)
'@

        # Replace placeholders
        $pythonScript = $pythonScript.Replace('S3_ENDPOINT_PLACEHOLDER', $s3Endpoint)
        $pythonScript = $pythonScript.Replace('S3_ACCESS_KEY_PLACEHOLDER', $s3AccessKey)
        $pythonScript = $pythonScript.Replace('S3_SECRET_KEY_PLACEHOLDER', $s3SecretKey)

        # Save the script to a temporary file
        $tempScript = "development/flush_s3.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] S3 flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-MLflow {
    Write-Host "Flushing MLflow..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush MLflow
        $pythonScript = @'
import mlflow
import sys

try:
    # Set tracking URI
    mlflow.set_tracking_uri('MLFLOW_URL_PLACEHOLDER')

    # Get all experiments
    experiments = mlflow.search_experiments()

    deleted_count = 0
    for exp in experiments:
        exp_id = exp.experiment_id
        exp_name = exp.name

        # Skip default experiment
        if exp_name == 'Default':
            continue

        try:
            # Delete experiment
            mlflow.delete_experiment(exp_id)
            print(f'    Deleted experiment: {exp_name}')
            deleted_count += 1
        except Exception as e:
            print(f'    [WARN] Could not delete experiment {exp_name}: {str(e).strip()}')

    print(f'  [OK] MLflow flushed ({deleted_count} experiments)')
    sys.exit(0)

except Exception as e:
    print(f'  [ERROR] MLflow connection failed: {e}')
    sys.exit(1)
'@

        # Replace placeholders
        $pythonScript = $pythonScript.Replace('MLFLOW_URL_PLACEHOLDER', $mlflowUrl)

        # Save the script to a temporary file
        $tempScript = "development/flush_mlflow.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] MLflow flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-Feast {
    Write-Host "Flushing Feast feature store..." -ForegroundColor Yellow
    try {
        $feastPaths = @(
            "data/feast",
            "feast",
            "feature-engineering-service/data/feast"
        )

        $deleted = $false
        foreach ($path in $feastPaths) {
            if (Test-Path $path) {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "    Deleted: $path" -ForegroundColor Gray
                $deleted = $true
            }
        }

        if ($deleted) {
            Write-Host "  [OK] Feast feature store flushed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [OK] Feast feature store is clean (no directories found)" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "  [ERROR] Feast flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-DeltaLake {
    Write-Host "Flushing Delta Lake..." -ForegroundColor Yellow
    try {
        $deltaLakePaths = @(
            "data/delta_lake",
            "data/feast/offline_store",
            "feature-engineering-service/data/feast/offline_store"
        )

        $deleted = $false
        foreach ($path in $deltaLakePaths) {
            if (Test-Path $path) {
                Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "    Deleted: $path" -ForegroundColor Gray
                $deleted = $true
            }
        }

        if ($deleted) {
            Write-Host "  [OK] Delta Lake flushed" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [OK] Delta Lake is clean (no directories found)" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "  [ERROR] Delta Lake flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Flush-SchemaRegistry {
    Write-Host "Flushing Schema Registry..." -ForegroundColor Yellow
    try {
        # Create a Python script to flush Schema Registry
        $pythonScript = @'
import requests
import sys

try:
    # Get all subjects
    response = requests.get('SCHEMA_REGISTRY_URL_PLACEHOLDER/subjects', timeout=5)
    subjects = response.json()

    deleted_count = 0
    for subject in subjects:
        try:
            # Step 1: Soft delete (required before hard delete)
            soft_delete_response = requests.delete(
                f'SCHEMA_REGISTRY_URL_PLACEHOLDER/subjects/{subject}',
                timeout=5
            )

            # Step 2: Hard delete (permanent)
            hard_delete_response = requests.delete(
                f'SCHEMA_REGISTRY_URL_PLACEHOLDER/subjects/{subject}?permanent=true',
                timeout=5
            )

            if hard_delete_response.status_code in [200, 204]:
                print(f'    Deleted subject: {subject}')
                deleted_count += 1
            else:
                print(f'    [WARN] Could not delete subject {subject}: HTTP {hard_delete_response.status_code}')
        except Exception as e:
            print(f'    [WARN] Could not delete subject {subject}: {str(e).strip()}')

    print(f'  [OK] Schema Registry flushed ({deleted_count} subjects)')
    sys.exit(0)

except Exception as e:
    print(f'  [ERROR] Schema Registry connection failed: {e}')
    sys.exit(1)
'@

        # Replace placeholders
        $pythonScript = $pythonScript.Replace('SCHEMA_REGISTRY_URL_PLACEHOLDER', $schemaRegistryUrl)

        # Save the script to a temporary file
        $tempScript = "development/flush_schema_registry.py"
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8 -Force

        # Run the Python script
        $output = & python $tempScript 2>&1
        $exitCode = $LASTEXITCODE

        # Display output
        $output | ForEach-Object { Write-Host $_ }

        # Clean up
        Remove-Item -Path $tempScript -Force -ErrorAction SilentlyContinue

        if ($exitCode -eq 0) {
            return $true
        } else {
            return $false
        }
    }
    catch {
        Write-Host "  [ERROR] Schema Registry flush failed: $_" -ForegroundColor Red
        return $false
    }
}

function Inspect-AllDataStores {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "INSPECTING ALL DATA STORES" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Run the inspection script
    $inspectScript = "development/inspect_all_datastores.py"
    if (Test-Path $inspectScript) {
        & python $inspectScript
    } else {
        Write-Host "[ERROR] Inspection script not found: $inspectScript" -ForegroundColor Red
    }
}

function Start-AllServices {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "STARTING ALL MICROSERVICES" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Create logs directory in development folder
    $logDir = "development/logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null

    # Clean up old log files
    Write-Host ""
    Write-Host "Cleaning up old log files..." -ForegroundColor Yellow
    if (Test-Path $logDir) {
        Get-ChildItem -Path $logDir -Filter "*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Old log files removed" -ForegroundColor Green
    }

    # Flush external services
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "FLUSHING EXTERNAL SERVICES" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    $redisOk = Flush-Redis
    Write-Host ""

    $qdrantOk = Flush-Qdrant
    Write-Host ""

    $kafkaOk = Flush-Kafka
    Write-Host ""

    $dbOk = Flush-Database
    Write-Host ""

    $neo4jOk = Flush-Neo4j
    Write-Host ""

    $schemaRegistryOk = Flush-SchemaRegistry
    Write-Host ""

    if (-not ($redisOk -and $qdrantOk -and $kafkaOk -and $dbOk -and $neo4jOk -and $schemaRegistryOk)) {
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "WARNING: Some services failed to flush" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "Redis: $(if ($redisOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($redisOk) { 'Green' } else { 'Red' })
        Write-Host "Qdrant: $(if ($qdrantOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($qdrantOk) { 'Green' } else { 'Red' })
        Write-Host "Kafka: $(if ($kafkaOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($kafkaOk) { 'Green' } else { 'Red' })
        Write-Host "Database: $(if ($dbOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($dbOk) { 'Green' } else { 'Red' })
        Write-Host "Neo4j: $(if ($neo4jOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($neo4jOk) { 'Green' } else { 'Red' })
        Write-Host "Schema Registry: $(if ($schemaRegistryOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($schemaRegistryOk) { 'Green' } else { 'Red' })
        Write-Host ""
        Write-Host "Continuing with service startup..." -ForegroundColor Yellow
        Write-Host ""
    }

    Write-Host ""

    $pids = @()
    $cmdPids = @()

    foreach ($service in $services) {
        Write-Host ""
        Write-Host "Starting $($service.name)..." -ForegroundColor Yellow

        $cwd = $service.name
        $cmd = $service.cmd
        $logFile = Join-Path $logDir "$($service.name)_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

        try {
            # Build the full command
            if ($service.venv) {
                # Activate venv and run command
                $fullCmd = "cd /d `"$cwd`" && venv311\Scripts\activate.bat && $cmd"
            } else {
                $fullCmd = "cd /d `"$cwd`" && $cmd"
            }

            # Create log file path
            $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $logFile = Join-Path $logDir "$($service.name)_$timestamp.log"

            # Start process with output redirection to single log file
            # Use cmd.exe with 2>&1 to redirect both stdout and stderr
            $proc = Start-Process -FilePath "cmd.exe" `
                                  -ArgumentList "/c $fullCmd 2>&1" `
                                  -RedirectStandardOutput $logFile `
                                  -PassThru -WindowStyle Normal

            $pids += [PSCustomObject]@{
                Name = $service.name
                PID = $proc.Id
                Port = $service.port
                Venv = $service.venv
                LogFile = $logFile
            }

            $cmdPids += $proc.Id

            Write-Host "[OK] $($service.name) started (PID: $($proc.Id))" -ForegroundColor Green
            Write-Host "     Log: $logFile" -ForegroundColor Gray
            Start-Sleep -Seconds 1
        }
        catch {
            Write-Host "[ERROR] Failed to start $($service.name): $_" -ForegroundColor Red
        }
    }

    # Save PIDs to files
    $pids | ConvertTo-Json | Out-File -FilePath $pidFile -Force
    $cmdPids | Out-File -FilePath $cmdPidFile -Force

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "ALL SERVICES STARTED" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Services running:" -ForegroundColor Yellow
    $pids | ForEach-Object {
        $venvLabel = if ($_.Venv) { " (venv311)" } else { "" }
        Write-Host "  - $($_.Name)$venvLabel (PID: $($_.PID), Port: $($_.Port))" -ForegroundColor Green
        Write-Host "    Log: $($_.LogFile)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "Waiting for services to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    Write-Host ""
    Write-Host "Checking service health..." -ForegroundColor Yellow
    foreach ($p in $pids) {
        try {
            $proc = Get-Process -Id $p.PID -ErrorAction Stop
            if ($proc.HasExited) {
                Write-Host "[ALERT] $($p.Name) has exited!" -ForegroundColor Red
            } else {
                Write-Host "[OK] $($p.Name) is running" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "[ALERT] $($p.Name) not found (PID: $($p.PID))" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "All services started. Check individual terminal windows for logs." -ForegroundColor Cyan
    Write-Host "To stop all services, run: .\manage_services.ps1 -Action stop" -ForegroundColor Yellow
}

function Stop-AllServices {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "STOPPING ALL MICROSERVICES" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow

    # Kill only the services we started using taskkill for reliable termination
    if (Test-Path $pidFile) {
        $pids = Get-Content -Path $pidFile | ConvertFrom-Json
        foreach ($p in $pids) {
            try {
                $proc = Get-Process -Id $p.PID -ErrorAction Stop
                Write-Host "  Stopping $($p.Name) (PID: $($p.PID))..." -ForegroundColor Yellow
                # Use taskkill with /T to kill process tree (cmd.exe and all children)
                taskkill /PID $p.PID /T /F 2>&1 | Out-Null
                Write-Host "    [OK] Stopped" -ForegroundColor Green
            }
            catch {
                Write-Host "  [WARN] Process $($p.Name) (PID: $($p.PID)) not found" -ForegroundColor Yellow
            }
        }
    }

    Start-Sleep -Seconds 2

    # Remove PID files
    Write-Host ""
    Write-Host "Cleaning up PID files..." -ForegroundColor Yellow
    Remove-Item -Path $pidFile -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $cmdPidFile -Force -ErrorAction SilentlyContinue
    Write-Host "  [OK] PID files removed" -ForegroundColor Green

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "ALL SERVICES STOPPED" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Get-ServiceStatus {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "SERVICE STATUS" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    if (-not (Test-Path $pidFile)) {
        Write-Host "[INFO] No services running" -ForegroundColor Yellow
        return
    }

    $pids = Get-Content -Path $pidFile | ConvertFrom-Json

    Write-Host ""
    Write-Host "Service Status:" -ForegroundColor Yellow
    foreach ($p in $pids) {
        try {
            $proc = Get-Process -Id $p.PID -ErrorAction Stop
            $status = if ($proc.HasExited) { "STOPPED" } else { "RUNNING" }
            $color = if ($proc.HasExited) { "Red" } else { "Green" }
            $venvLabel = if ($p.Venv) { " (venv311)" } else { "" }
            Write-Host "  [$status] $($p.Name)$venvLabel (PID: $($p.PID), Port: $($p.Port))" -ForegroundColor $color
        }
        catch {
            Write-Host "  [STOPPED] $($p.Name) (PID: $($p.PID)) - Process not found" -ForegroundColor Red
        }
    }
    Write-Host ""
}

function Restart-AllServices {
    Write-Host "Restarting all services..." -ForegroundColor Cyan
    Stop-AllServices
    Start-Sleep -Seconds 3
    Start-AllServices
}

function Restart-SingleService {
    param(
        [string]$ServiceName
    )

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "RESTARTING SERVICE: $ServiceName" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    # Find the service definition
    $service = $services | Where-Object { $_.name -eq $ServiceName }
    if (-not $service) {
        Write-Host "[ERROR] Service '$ServiceName' not found" -ForegroundColor Red
        Write-Host "Available services:" -ForegroundColor Yellow
        $services | ForEach-Object { Write-Host "  - $($_.name)" }
        return
    }

    # Stop the service
    Write-Host ""
    Write-Host "Stopping $ServiceName..." -ForegroundColor Yellow

    if (Test-Path $pidFile) {
        $pids = Get-Content -Path $pidFile | ConvertFrom-Json
        $servicePid = $pids | Where-Object { $_.Name -eq $ServiceName }

        if ($servicePid) {
            try {
                Write-Host "  Stopping $($servicePid.Name) (PID: $($servicePid.PID))..." -ForegroundColor Yellow
                taskkill /PID $servicePid.PID /T /F 2>&1 | Out-Null
                Write-Host "    [OK] Stopped" -ForegroundColor Green

                # Delete old log files for this service
                Write-Host "  Deleting old log files for $ServiceName..." -ForegroundColor Yellow
                $logDir = "development/logs"
                Get-ChildItem -Path $logDir -Filter "$($service.name)_*.log" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
                Write-Host "    [OK] Old logs deleted" -ForegroundColor Green

                # Remove from PID file
                $pids = $pids | Where-Object { $_.Name -ne $ServiceName }
                $pids | ConvertTo-Json | Out-File -FilePath $pidFile -Force
            }
            catch {
                Write-Host "  [WARN] Failed to stop service: $_" -ForegroundColor Yellow
            }
        }
    }

    Start-Sleep -Seconds 2

    # Start the service
    Write-Host ""
    Write-Host "Starting $ServiceName..." -ForegroundColor Yellow

    $cwd = $service.name
    $cmd = $service.cmd
    $logDir = "development/logs"

    try {
        # Build the full command
        if ($service.venv) {
            $fullCmd = "cd /d `"$cwd`" && venv311\Scripts\activate.bat && $cmd"
        } else {
            $fullCmd = "cd /d `"$cwd`" && $cmd"
        }

        # Create log file path
        $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        $logFile = Join-Path $logDir "$($service.name)_$timestamp.log"

        # Start process
        $proc = Start-Process -FilePath "cmd.exe" `
                              -ArgumentList "/c $fullCmd 2>&1" `
                              -RedirectStandardOutput $logFile `
                              -PassThru -WindowStyle Normal

        Write-Host "[OK] $($service.name) started (PID: $($proc.Id))" -ForegroundColor Green
        Write-Host "     Log: $logFile" -ForegroundColor Gray

        # Add to PID file
        if (Test-Path $pidFile) {
            $pids = Get-Content -Path $pidFile | ConvertFrom-Json
        } else {
            $pids = @()
        }

        $pids += [PSCustomObject]@{
            Name = $service.name
            PID = $proc.Id
            Port = $service.port
            Venv = $service.venv
            LogFile = $logFile
        }

        $pids | ConvertTo-Json | Out-File -FilePath $pidFile -Force

        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "SERVICE RESTARTED" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
    }
    catch {
        Write-Host "[ERROR] Failed to start $($service.name): $_" -ForegroundColor Red
    }
}

function Initiate-Crawl {
    param(
        [string]$FeedId = "reuters"
    )

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "INITIATING CRAWL" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Feed ID: $FeedId" -ForegroundColor Yellow
    Write-Host ""

    try {
        Write-Host "Sending crawl request to http://localhost:8000/crawl..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Method Post `
                                      -Uri "http://localhost:8000/crawl" `
                                      -ContentType "application/json" `
                                      -Body "{`"feed_id`": `"$FeedId`"}" `
                                      -ErrorAction Stop

        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "CRAWL INITIATED SUCCESSFULLY" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Response:" -ForegroundColor Yellow
        $response | ConvertTo-Json | Write-Host
        Write-Host ""
    }
    catch {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "CRAWL INITIATION FAILED" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host ""
    }
}

function Initiate-Clustering {
    param(
        [int]$TimeWindowHours = 24
    )

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "INITIATING CLUSTERING" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Time Window: $TimeWindowHours hours" -ForegroundColor Yellow
    Write-Host ""

    try {
        $body = @{
            time_window_hours = $TimeWindowHours
        } | ConvertTo-Json

        Write-Host "Sending clustering request to http://localhost:8082/jobs/clustering/run..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Method Post `
                                      -Uri "http://localhost:8082/jobs/clustering/run" `
                                      -ContentType "application/json" `
                                      -Body $body `
                                      -ErrorAction Stop

        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "CLUSTERING INITIATED SUCCESSFULLY" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Response:" -ForegroundColor Yellow
        $response | ConvertTo-Json | Write-Host
        Write-Host ""
    }
    catch {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "CLUSTERING INITIATION FAILED" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host ""
    }
}

# Execute action
switch ($Action) {
    "start" {
        Start-AllServices
    }
    "stop" {
        Stop-AllServices
    }
    "status" {
        Get-ServiceStatus
    }
    "restart" {
        if ($Service) {
            Restart-SingleService -ServiceName $Service
        } else {
            Restart-AllServices
        }
    }
    "crawl" {
        Initiate-Crawl -FeedId $Service
    }
    "clustering" {
        Initiate-Clustering
    }
    "flush-kafka" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING KAFKA TOPICS" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Kafka
        Write-Host ""
    }
    "flush-redis" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING REDIS" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Redis
        Write-Host ""
    }
    "flush-qdrant" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING QDRANT" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Qdrant
        Write-Host ""
    }
    "flush-database" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING DATABASE" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Database
        Write-Host ""
    }
    "flush-neo4j" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING NEO4J" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Neo4j
        Write-Host ""
    }
    "flush-s3" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING S3/MINIO" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-S3
        Write-Host ""
    }
    "flush-mlflow" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING MLFLOW" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-MLflow
        Write-Host ""
    }
    "flush-feast" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING FEAST" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-Feast
        Write-Host ""
    }
    "flush-schema-registry" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING SCHEMA REGISTRY" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Flush-SchemaRegistry
        Write-Host ""
    }
    "inspect-all" {
        Inspect-AllDataStores
    }
    "flush-all" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSHING ALL EXTERNAL SERVICES" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""

        $redisOk = Flush-Redis
        Write-Host ""

        $qdrantOk = Flush-Qdrant
        Write-Host ""

        $kafkaOk = Flush-Kafka
        Write-Host ""

        $dbOk = Flush-Database
        Write-Host ""

        $neo4jOk = Flush-Neo4j
        Write-Host ""

        $schemaRegistryOk = Flush-SchemaRegistry
        Write-Host ""

        $s3Ok = Flush-S3
        Write-Host ""

        $mlflowOk = Flush-MLflow
        Write-Host ""

        $feastOk = Flush-Feast
        Write-Host ""

        $deltaLakeOk = Flush-DeltaLake
        Write-Host ""

        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "FLUSH SUMMARY" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Redis: $(if ($redisOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($redisOk) { 'Green' } else { 'Red' })
        Write-Host "Qdrant: $(if ($qdrantOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($qdrantOk) { 'Green' } else { 'Red' })
        Write-Host "Kafka: $(if ($kafkaOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($kafkaOk) { 'Green' } else { 'Red' })
        Write-Host "Database: $(if ($dbOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($dbOk) { 'Green' } else { 'Red' })
        Write-Host "Neo4j: $(if ($neo4jOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($neo4jOk) { 'Green' } else { 'Red' })
        Write-Host "Schema Registry: $(if ($schemaRegistryOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($schemaRegistryOk) { 'Green' } else { 'Red' })
        Write-Host "S3/MinIO: $(if ($s3Ok) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($s3Ok) { 'Green' } else { 'Red' })
        Write-Host "MLflow: $(if ($mlflowOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($mlflowOk) { 'Green' } else { 'Red' })
        Write-Host "Feast: $(if ($feastOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($feastOk) { 'Green' } else { 'Red' })
        Write-Host "Delta Lake: $(if ($deltaLakeOk) { 'OK' } else { 'FAILED' })" -ForegroundColor $(if ($deltaLakeOk) { 'Green' } else { 'Red' })
        Write-Host ""
    }
    "flush-deltalake" {
        Flush-DeltaLake
    }
    default {
        Write-Host "Unknown action: $Action" -ForegroundColor Red
        Write-Host "Usage:" -ForegroundColor Yellow
        Write-Host "  .\manage_services.ps1 -Action start|stop|status|restart [-Service service-name]" -ForegroundColor Yellow
        Write-Host "  .\manage_services.ps1 -Action crawl [-Service feed-id]" -ForegroundColor Yellow
        Write-Host "  .\manage_services.ps1 -Action clustering" -ForegroundColor Yellow
        Write-Host "  .\manage_services.ps1 -Action inspect-all" -ForegroundColor Yellow
        Write-Host "  .\manage_services.ps1 -Action flush-kafka|flush-redis|flush-qdrant|flush-database|flush-neo4j|flush-s3|flush-mlflow|flush-feast|flush-deltalake|flush-schema-registry|flush-all" -ForegroundColor Yellow
    }
}


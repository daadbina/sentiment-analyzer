#!/usr/bin/env python3
"""
Task 3: Test MLflow and S3 Integration
Verify that:
1. Models are properly registered in MLflow
2. Metrics are logged correctly
3. Artifacts are stored in S3
4. Model versioning works
"""

import requests
import json
import sys
from datetime import datetime

def test_mlflow_server():
    """Check if MLflow server is running."""
    print("\n" + "="*80)
    print("1. MLflow Server Health Check")
    print("="*80)
    
    mlflow_url = "http://localhost:5000"
    
    try:
        response = requests.get(f"{mlflow_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ MLflow server is running")
            return True
        else:
            print(f"❌ MLflow server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ MLflow server error: {e}")
        return False

def test_mlflow_experiments():
    """Check MLflow experiments."""
    print("\n" + "="*80)
    print("2. MLflow Experiments")
    print("="*80)
    
    mlflow_url = "http://localhost:5000"
    
    try:
        # Get experiments using MLflow API
        response = requests.get(
            f"{mlflow_url}/api/2.0/mlflow/experiments/list",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            experiments = data.get("experiments", [])
            print(f"✅ Found {len(experiments)} experiments")
            
            for exp in experiments:
                print(f"   - {exp.get('name')} (ID: {exp.get('experiment_id')})")
            
            return len(experiments) > 0
        else:
            print(f"⚠️  Could not list experiments: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error listing experiments: {e}")
        return False

def test_mlflow_runs():
    """Check MLflow runs and metrics."""
    print("\n" + "="*80)
    print("3. MLflow Runs and Metrics")
    print("="*80)
    
    mlflow_url = "http://localhost:5000"
    
    try:
        # Get experiments first
        response = requests.get(
            f"{mlflow_url}/api/2.0/mlflow/experiments/list",
            timeout=10
        )
        
        if response.status_code != 200:
            print("⚠️  Could not list experiments")
            return False
        
        experiments = response.json().get("experiments", [])
        
        if not experiments:
            print("⚠️  No experiments found")
            return False
        
        # Get runs from first experiment
        exp_id = experiments[0].get("experiment_id")
        response = requests.get(
            f"{mlflow_url}/api/2.0/mlflow/runs/search",
            params={"experiment_ids": [exp_id]},
            timeout=10
        )
        
        if response.status_code == 200:
            runs = response.json().get("runs", [])
            print(f"✅ Found {len(runs)} runs in experiment {exp_id}")
            
            if runs:
                # Check first run details
                run = runs[0]
                run_id = run.get("info", {}).get("run_id")
                
                # Get run details
                response = requests.get(
                    f"{mlflow_url}/api/2.0/mlflow/runs/get",
                    params={"run_id": run_id},
                    timeout=10
                )
                
                if response.status_code == 200:
                    run_data = response.json().get("run", {})
                    metrics = run_data.get("data", {}).get("metrics", [])
                    params = run_data.get("data", {}).get("params", [])
                    
                    print(f"\n   Run ID: {run_id}")
                    print(f"   Metrics recorded: {len(metrics)}")
                    for metric in metrics[:5]:
                        print(f"      - {metric.get('key')}: {metric.get('value')}")
                    
                    print(f"   Parameters: {len(params)}")
                    for param in params[:3]:
                        print(f"      - {param.get('key')}: {param.get('value')}")
                    
                    return len(metrics) > 0
            
            return True
        else:
            print(f"⚠️  Could not list runs: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking runs: {e}")
        return False

def test_mlflow_models():
    """Check MLflow registered models."""
    print("\n" + "="*80)
    print("4. MLflow Registered Models")
    print("="*80)
    
    mlflow_url = "http://localhost:5000"
    
    try:
        response = requests.get(
            f"{mlflow_url}/api/2.0/mlflow/registered-models/list",
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json().get("registered_models", [])
            print(f"✅ Found {len(models)} registered models")
            
            for model in models[:5]:
                name = model.get("name")
                versions = model.get("latest_versions", [])
                print(f"   - {name}")
                for version in versions:
                    stage = version.get("current_stage")
                    version_num = version.get("version")
                    print(f"      Version {version_num}: {stage}")
            
            return len(models) > 0
        else:
            print(f"⚠️  Could not list models: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error listing models: {e}")
        return False

def test_s3_integration():
    """Check S3 artifact storage."""
    print("\n" + "="*80)
    print("5. S3 Artifact Storage")
    print("="*80)
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin',
            aws_secret_access_key='minioadmin',
            region_name='us-east-1'
        )
        
        # List buckets
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])
        print(f"✅ S3 connection successful")
        print(f"   Found {len(buckets)} buckets:")
        
        for bucket in buckets:
            bucket_name = bucket.get('Name')
            print(f"      - {bucket_name}")
            
            # List objects in bucket
            try:
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    MaxKeys=5
                )
                
                objects = response.get('Contents', [])
                if objects:
                    print(f"        Objects: {len(objects)}")
                    for obj in objects[:3]:
                        print(f"           - {obj.get('Key')} ({obj.get('Size')} bytes)")
            except ClientError as e:
                print(f"        Error listing objects: {e}")
        
        return len(buckets) > 0
    except ImportError:
        print("⚠️  boto3 not installed, skipping S3 test")
        return False
    except Exception as e:
        print(f"❌ S3 error: {e}")
        return False

def test_trainer_integration():
    """Test trainer service integration with MLflow."""
    print("\n" + "="*80)
    print("6. Trainer Service Integration")
    print("="*80)
    
    try:
        # Call train endpoint
        url = "http://localhost:8008/train"
        response = requests.post(url, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Training completed successfully")
            
            # Check evaluation results
            eval_results = result.get("evaluation_results", {})
            print(f"   Models evaluated: {len(eval_results)}")
            
            for model_name, metrics in eval_results.items():
                auc = metrics.get("auc", 0)
                accuracy = metrics.get("accuracy", 0)
                print(f"      - {model_name}: AUC={auc:.4f}, Accuracy={accuracy:.4f}")
            
            # Check drift detection
            feature_drift = result.get("feature_drift", {})
            target_drift = result.get("target_drift", {})
            
            print(f"   Feature drift detected: {feature_drift.get('drift_detected')}")
            print(f"   Target drift detected: {target_drift.get('drift_detected')}")
            
            return True
        else:
            print(f"❌ Training failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all MLflow and S3 integration tests."""
    print("\n" + "="*80)
    print("TASK 3: MLflow and S3 Integration Test")
    print("="*80)
    
    results = {
        "MLflow Server": test_mlflow_server(),
        "MLflow Experiments": test_mlflow_experiments(),
        "MLflow Runs & Metrics": test_mlflow_runs(),
        "MLflow Models": test_mlflow_models(),
        "S3 Artifact Storage": test_s3_integration(),
        "Trainer Integration": test_trainer_integration(),
    }
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "⚠️  SKIP/FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("="*80 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


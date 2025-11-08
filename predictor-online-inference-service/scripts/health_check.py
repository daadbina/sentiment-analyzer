#!/usr/bin/env python3
"""
Health check script for predictor-online-inference-service.

Used by Docker HEALTHCHECK and Kubernetes liveness/readiness probes.
"""

import sys
import requests
from typing import Dict, Any


def check_health(host: str = "localhost", port: int = 8000) -> Dict[str, Any]:
    """
    Check service health.
    
    Args:
        host: Service host
        port: Service port
    
    Returns:
        Health check response
    
    Raises:
        Exception: If health check fails
    """
    url = f"http://{host}:{port}/api/v1/health"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        health_data = response.json()
        
        # Check overall status
        if health_data.get("status") != "healthy":
            raise Exception(f"Service unhealthy: {health_data}")
        
        # Check dependencies
        dependencies = health_data.get("dependencies", {})
        unhealthy_deps = [
            dep for dep, status in dependencies.items()
            if status != "healthy"
        ]
        
        if unhealthy_deps:
            raise Exception(f"Unhealthy dependencies: {unhealthy_deps}")
        
        return health_data
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Health check request failed: {e}")


def main():
    """Main entry point."""
    try:
        health_data = check_health()
        print(f"✓ Service healthy: {health_data['status']}")
        print(f"  Version: {health_data.get('version', 'unknown')}")
        print(f"  Dependencies: {health_data.get('dependencies', {})}")
        sys.exit(0)
    except Exception as e:
        print(f"✗ Health check failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


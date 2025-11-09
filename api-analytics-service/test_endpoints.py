"""Test all API endpoints to identify errors."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8011"

def test_endpoint(method, endpoint, data=None, params=None):
    """Test an endpoint and return results."""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            return {"error": f"Unknown method: {method}"}
        
        return {
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
        return {
            "status_code": None,
            "success": False,
            "error": str(e)
        }

def main():
    """Test all endpoints."""
    print("=" * 80)
    print("API ANALYTICS SERVICE - ENDPOINT TESTING")
    print("=" * 80)
    print()
    
    results = []
    
    # Health endpoints
    print("Testing Health Endpoints...")
    print("-" * 80)
    
    tests = [
        ("GET", "/health", None, None),
        ("GET", "/ready", None, None),
        ("GET", "/live", None, None),
    ]
    
    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
    
    print()
    
    # Groups endpoints
    print("Testing Groups Endpoints...")
    print("-" * 80)
    
    tests = [
        ("GET", "/api/v1/groups", None, {"page": 1, "page_size": 10}),
        ("GET", "/api/v1/groups", None, {"page": 1, "page_size": 10, "search": "test"}),
    ]
    
    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
    
    print()
    
    # Predictions endpoints
    print("Testing Predictions Endpoints...")
    print("-" * 80)
    
    tests = [
        ("GET", "/api/v1/predictions", None, {"page": 1, "page_size": 10}),
        ("GET", "/api/v1/predictions", None, {"page": 1, "page_size": 10, "domain": "btc"}),
    ]
    
    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
    
    # Test create prediction
    prediction_data = {
        "group_id": "test-group-123",
        "domain": "btc",
        "prediction_probability": 0.75,
        "prediction_confidence": 0.85,
        "model_version": "v1.0.0",
        "features": {"test": "data"},
        "trace_id": "test-trace-123"
    }
    result = test_endpoint("POST", "/api/v1/predictions", prediction_data)
    results.append(("POST", "/api/v1/predictions", result))
    status = "✓" if result["success"] else "✗"
    print(f"{status} POST /api/v1/predictions - Status: {result.get('status_code', 'ERROR')}")
    if not result["success"]:
        print(f"  Error: {result.get('error', result.get('response'))}")
    
    print()
    
    # Entities endpoints
    print("Testing Entities Endpoints...")
    print("-" * 80)
    
    tests = [
        ("GET", "/api/v1/entities", None, {"page": 1, "page_size": 10}),
        ("GET", "/api/v1/entities", None, {"page": 1, "page_size": 10, "entity_type": "PERSON"}),
        ("GET", "/api/v1/entities", None, {"page": 1, "page_size": 10, "search": "test"}),
    ]
    
    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
    
    print()
    
    # Analytics endpoints
    print("Testing Analytics Endpoints...")
    print("-" * 80)

    tests = [
        ("GET", "/api/v1/analytics/trends", None, {"metric": "groups", "days": 7}),
        ("GET", "/api/v1/analytics/trends", None, {"metric": "predictions", "days": 7}),
        ("GET", "/api/v1/analytics/trends", None, {"metric": "entities", "days": 7}),
        ("GET", "/api/v1/analytics/distributions", None, {"metric": "domain"}),
        ("GET", "/api/v1/analytics/distributions", None, {"metric": "entity_type"}),
        ("GET", "/api/v1/analytics/top-entities", None, {"limit": 10}),
        ("GET", "/api/v1/analytics/top-actors", None, {"limit": 10}),
    ]
    
    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
    
    print()
    
    # Export endpoints
    print("Testing Export Endpoints...")
    print("-" * 80)

    tests = [
        ("GET", "/api/v1/export/groups", None, None),
        ("GET", "/api/v1/export/predictions", None, None),
    ]

    for method, endpoint, data, params in tests:
        result = test_endpoint(method, endpoint, data, params)
        results.append((method, endpoint, result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")

    print()

    # Test specific group endpoints (if we have groups)
    print("Testing Specific Group Endpoints...")
    print("-" * 80)

    # First get a group to test with
    groups_result = test_endpoint("GET", "/api/v1/groups", None, {"page": 1, "page_size": 1})
    if groups_result["success"] and groups_result["response"].get("items"):
        group_id = groups_result["response"]["items"][0]["group_id"]

        tests = [
            ("GET", f"/api/v1/groups/{group_id}", None, None),
        ]

        for method, endpoint, data, params in tests:
            result = test_endpoint(method, endpoint, data, params)
            results.append((method, endpoint, result))
            status = "✓" if result["success"] else "✗"
            print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
            if not result["success"]:
                print(f"  Error: {result.get('error', result.get('response'))}")
    else:
        print("  Skipped - No groups available")

    print()

    # Test specific prediction endpoints (if we have predictions)
    print("Testing Specific Prediction Endpoints...")
    print("-" * 80)

    predictions_result = test_endpoint("GET", "/api/v1/predictions", None, {"page": 1, "page_size": 1})
    if predictions_result["success"] and predictions_result["response"].get("items"):
        prediction_id = predictions_result["response"]["items"][0]["id"]
        group_id = predictions_result["response"]["items"][0]["group_id"]

        tests = [
            ("GET", f"/api/v1/predictions/{prediction_id}", None, None),
            ("GET", f"/api/v1/predictions/group/{group_id}", None, {"page": 1, "page_size": 10}),
        ]

        for method, endpoint, data, params in tests:
            result = test_endpoint(method, endpoint, data, params)
            results.append((method, endpoint, result))
            status = "✓" if result["success"] else "✗"
            print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
            if not result["success"]:
                print(f"  Error: {result.get('error', result.get('response'))}")
    else:
        print("  Skipped - No predictions available")

    print()

    # Test specific entity endpoints (if we have entities)
    print("Testing Specific Entity Endpoints...")
    print("-" * 80)

    entities_result = test_endpoint("GET", "/api/v1/entities", None, {"page": 1, "page_size": 1})
    if entities_result["success"] and entities_result["response"].get("items"):
        entity_id = entities_result["response"]["items"][0]["actor_id"]

        tests = [
            ("GET", f"/api/v1/entities/{entity_id}", None, None),
        ]

        for method, endpoint, data, params in tests:
            result = test_endpoint(method, endpoint, data, params)
            results.append((method, endpoint, result))
            status = "✓" if result["success"] else "✗"
            print(f"{status} {method} {endpoint} - Status: {result.get('status_code', 'ERROR')}")
            if not result["success"]:
                print(f"  Error: {result.get('error', result.get('response'))}")
    else:
        print("  Skipped - No entities available")

    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for _, _, r in results if r["success"])
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    if failed > 0:
        print()
        print("Failed Tests:")
        print("-" * 80)
        for method, endpoint, result in results:
            if not result["success"]:
                print(f"  {method} {endpoint}")
                print(f"    Status: {result.get('status_code', 'ERROR')}")
                print(f"    Error: {result.get('error', result.get('response'))}")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()


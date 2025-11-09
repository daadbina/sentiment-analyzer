"""Test remaining API endpoints not covered by automated tests."""

import requests
import json

BASE_URL = "http://localhost:8011"


def test_endpoint(method, endpoint, data=None, params=None):
    """Test a single endpoint."""
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
            return {"success": False, "error": f"Unknown method: {method}"}
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.json() if response.content else None,
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "response": response.json() if response.content else None,
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """Run all tests."""
    print("=" * 80)
    print("API ANALYTICS SERVICE - REMAINING ENDPOINT TESTING")
    print("=" * 80)
    print()
    
    results = []
    
    # First get some IDs to test with
    print("Getting test data...")
    print("-" * 80)
    
    # Get a group ID
    groups_result = test_endpoint("GET", "/api/v1/groups", None, {"page": 1, "page_size": 1})
    group_id = None
    if groups_result["success"] and groups_result["response"].get("items"):
        group_id = groups_result["response"]["items"][0]["group_id"]
        print(f"✓ Found group ID: {group_id}")
    else:
        print("✗ No groups available")
    
    # Get an entity ID
    entities_result = test_endpoint("GET", "/api/v1/entities", None, {"page": 1, "page_size": 1})
    entity_id = None
    if entities_result["success"] and entities_result["response"].get("items"):
        entity_id = entities_result["response"]["items"][0]["actor_id"]
        print(f"✓ Found entity ID: {entity_id}")
    else:
        print("✗ No entities available")
    
    print()
    
    # Test entity mentions endpoint
    if entity_id:
        print("Testing Entity Mentions Endpoint...")
        print("-" * 80)
        
        result = test_endpoint("GET", f"/api/v1/entities/{entity_id}/mentions", None, {"page": 1, "page_size": 10})
        results.append(("GET", f"/api/v1/entities/{entity_id}/mentions", result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} GET /api/v1/entities/{entity_id}/mentions - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
        print()
    
    # Test group update endpoint
    if group_id:
        print("Testing Group Update Endpoint...")
        print("-" * 80)
        
        update_data = {"topic_label": "Updated Test Topic"}
        result = test_endpoint("PUT", f"/api/v1/groups/{group_id}", update_data, None)
        results.append(("PUT", f"/api/v1/groups/{group_id}", result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} PUT /api/v1/groups/{group_id} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Error: {result.get('error', result.get('response'))}")
        print()
    
    # Test graph endpoints (these may fail if Neo4j is not set up)
    print("Testing Graph Endpoints (may fail if Neo4j not configured)...")
    print("-" * 80)
    
    if entity_id:
        # Test neighbors endpoint
        result = test_endpoint("GET", f"/api/v1/graph/neighbors/{entity_id}", None, {"depth": 1})
        results.append(("GET", f"/api/v1/graph/neighbors/{entity_id}", result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} GET /api/v1/graph/neighbors/{entity_id} - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Note: {result.get('error', result.get('response'))}")
        
        # Test centrality endpoint
        result = test_endpoint("GET", "/api/v1/graph/centrality", None, {"limit": 10})
        results.append(("GET", "/api/v1/graph/centrality", result))
        status = "✓" if result["success"] else "✗"
        print(f"{status} GET /api/v1/graph/centrality - Status: {result.get('status_code', 'ERROR')}")
        if not result["success"]:
            print(f"  Note: {result.get('error', result.get('response'))}")
    
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
    if total > 0:
        print(f"Success Rate: {passed / total * 100:.1f}%")
    else:
        print("Success Rate: N/A (no tests run)")
    
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


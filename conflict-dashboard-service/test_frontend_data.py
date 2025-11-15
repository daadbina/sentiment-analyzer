#!/usr/bin/env python3
"""
Test if system can extract BTC and conflict predictions for frontend display
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.database import PostgresClient


async def test_frontend_data():
    """Test data extraction for frontend."""
    
    print("="*80)
    print("TESTING FRONTEND DATA EXTRACTION")
    print("="*80)
    
    client = PostgresClient()
    await client.connect()
    
    issues = []
    
    try:
        # Test 1: Conflict Predictions
        print("\n1️⃣  CONFLICT PREDICTIONS (for main dashboard)")
        print("-" * 80)
        
        conflict_preds = await client.get_latest_predictions(limit=10, min_confidence=0.0, hours=24)
        
        if not conflict_preds:
            issues.append("❌ No conflict predictions found")
            print("  ❌ FAIL: No conflict predictions returned")
        else:
            print(f"  ✓ Found {len(conflict_preds)} conflict predictions")
            
            # Check data quality
            with_countries = sum(1 for p in conflict_preds if p.get('countries'))
            without_countries = len(conflict_preds) - with_countries
            
            print(f"  ✓ Predictions with countries: {with_countries}/{len(conflict_preds)} ({with_countries/len(conflict_preds)*100:.1f}%)")
            
            if without_countries > 0:
                issues.append(f"⚠️  {without_countries} conflict predictions missing countries")
                print(f"  ⚠️  WARNING: {without_countries} predictions have no countries")
            
            # Show sample
            print(f"\n  Sample conflict prediction:")
            sample = conflict_preds[0]
            print(f"    ID: {sample['id']}")
            print(f"    Domain: {sample['domain']}")
            print(f"    Probability: {sample['prediction_probability']:.4f}")
            print(f"    Confidence: {sample['prediction_confidence']:.4f}")
            print(f"    Countries: {sample['countries']}")
            print(f"    Predicted at: {sample['predicted_at']}")
            
            # Check required fields for frontend
            required_fields = ['id', 'domain', 'prediction_probability', 'prediction_confidence', 'countries', 'predicted_at']
            missing_fields = [f for f in required_fields if f not in sample]
            if missing_fields:
                issues.append(f"❌ Conflict predictions missing fields: {missing_fields}")
                print(f"  ❌ FAIL: Missing required fields: {missing_fields}")
            else:
                print(f"  ✓ All required fields present")
        
        # Test 2: BTC Predictions
        print("\n2️⃣  BTC PREDICTIONS (for BTC dashboard)")
        print("-" * 80)
        
        btc_preds = await client.get_btc_predictions(limit=10, hours=24)
        
        if not btc_preds:
            issues.append("❌ No BTC predictions found")
            print("  ❌ FAIL: No BTC predictions returned")
        else:
            print(f"  ✓ Found {len(btc_preds)} BTC predictions")
            
            # Show sample
            print(f"\n  Sample BTC prediction:")
            sample = btc_preds[0]
            print(f"    ID: {sample['id']}")
            print(f"    Domain: {sample['domain']}")
            print(f"    Probability: {sample['prediction_probability']:.4f}")
            print(f"    Confidence: {sample['prediction_confidence']:.4f}")
            print(f"    Direction: {sample.get('prediction_direction', 'N/A')}")
            print(f"    Magnitude: {sample.get('prediction_magnitude', 'N/A')}")
            print(f"    Strength: {sample.get('prediction_strength', 'N/A')}")
            print(f"    Description: {sample.get('prediction_description', 'N/A')}")
            print(f"    Predicted at: {sample['predicted_at']}")
            
            # Check BTC-specific fields
            btc_fields = ['prediction_direction', 'prediction_magnitude', 'prediction_strength', 'prediction_description']
            missing_btc = [f for f in btc_fields if not sample.get(f) or sample.get(f) in ['unknown', 0.0, None]]
            
            if missing_btc:
                issues.append(f"⚠️  BTC predictions missing/empty fields: {missing_btc}")
                print(f"  ⚠️  WARNING: BTC-specific fields are missing or empty: {missing_btc}")
                print(f"  ℹ️  This means BTC predictions exist but lack detailed metadata")
            else:
                print(f"  ✓ All BTC-specific fields populated")
        
        # Test 3: Country Risk Scores
        print("\n3️⃣  COUNTRY RISK SCORES (for risk map)")
        print("-" * 80)
        
        risk_scores = await client.get_country_risk_scores()
        
        if not risk_scores:
            issues.append("❌ No country risk scores found")
            print("  ❌ FAIL: No country risk scores returned")
        else:
            print(f"  ✓ Found {len(risk_scores)} countries with risk scores")
            print(f"\n  Top 5 countries by risk:")
            for i, score in enumerate(risk_scores[:5], 1):
                print(f"    {i}. {score['country']:3s}: {score['risk_score']:.4f} (based on {score['prediction_count']} predictions)")
        
        # Test 4: Network Graph Data
        print("\n4️⃣  NETWORK GRAPH DATA (for visualization)")
        print("-" * 80)
        
        graph = await client.get_network_graph_data(min_confidence=0.0, hours=168)
        
        if not graph or not graph.get('nodes') or not graph.get('links'):
            issues.append("❌ Network graph data incomplete")
            print("  ❌ FAIL: Network graph data is incomplete")
        else:
            print(f"  ✓ Network graph ready:")
            print(f"    Nodes (countries): {len(graph['nodes'])}")
            print(f"    Links (predictions): {len(graph['links'])}")
            
            if len(graph['nodes']) < 2:
                issues.append("⚠️  Network graph has too few nodes")
                print(f"  ⚠️  WARNING: Only {len(graph['nodes'])} nodes - need at least 2 for visualization")
        
        # Test 5: Dashboard Stats
        print("\n5️⃣  DASHBOARD STATISTICS (for overview)")
        print("-" * 80)
        
        stats = await client.get_dashboard_stats()
        
        print(f"  ✓ Dashboard stats:")
        print(f"    Total predictions: {stats['total_predictions']}")
        print(f"    Total countries: {stats['total_countries']}")
        print(f"    Avg probability: {stats['avg_probability']:.4f}")
        print(f"    High risk count: {stats['high_risk_count']}")
        
        # Final Summary
        print("\n" + "="*80)
        if not issues:
            print("✅ ALL TESTS PASSED - System ready for frontend!")
            print("="*80)
            return 0
        else:
            print("⚠️  ISSUES FOUND:")
            print("="*80)
            for issue in issues:
                print(f"  {issue}")
            print("\n" + "="*80)
            
            # Determine if critical or just warnings
            critical = [i for i in issues if i.startswith("❌")]
            if critical:
                print("❌ CRITICAL ISSUES - Frontend will not work properly")
                return 1
            else:
                print("⚠️  WARNINGS ONLY - Frontend will work but with limited data")
                return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await client.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(test_frontend_data())
    sys.exit(exit_code)


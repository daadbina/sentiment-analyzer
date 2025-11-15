#!/usr/bin/env python3
"""
Script to clean up Prediction nodes in Neo4j:
1. Delete all predictions with model_version = "1"
2. Delete duplicate BTC predictions (keep only the most recent one per group)

Usage:
    python scripts/cleanup_predictions.py [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from src.config import Config


def delete_model_version_1(driver, database: str = "neo4j", dry_run: bool = False):
    """
    Delete all predictions with model_version = "1".
    
    Args:
        driver: Neo4j driver instance
        database: Database name
        dry_run: If True, only count without deleting
        
    Returns:
        Number of predictions deleted/counted
    """
    if dry_run:
        query = """
        MATCH (p:Prediction {model_version: "1"})
        RETURN count(p) as count
        """
    else:
        query = """
        MATCH (p:Prediction {model_version: "1"})
        DETACH DELETE p
        RETURN count(p) as count
        """
    
    with driver.session(database=database) as session:
        result = session.run(query)
        record = result.single()
        return record["count"] if record else 0


def delete_duplicate_btc_predictions(driver, database: str = "neo4j", dry_run: bool = False):
    """
    Delete duplicate BTC predictions, keeping only the most recent one per group.
    
    Args:
        driver: Neo4j driver instance
        database: Database name
        dry_run: If True, only count without deleting
        
    Returns:
        Number of predictions deleted/counted
    """
    # First, find groups with multiple BTC predictions
    find_duplicates_query = """
    MATCH (p:Prediction {domain: "btc"})
    WITH p.group_id as group_id, collect(p) as predictions
    WHERE size(predictions) > 1
    RETURN group_id, predictions
    """
    
    total_deleted = 0
    
    with driver.session(database=database) as session:
        result = session.run(find_duplicates_query)
        
        for record in result:
            group_id = record["group_id"]
            predictions = record["predictions"]
            
            # Sort by predicted_at (most recent first)
            sorted_predictions = sorted(
                predictions,
                key=lambda p: p.get("predicted_at", ""),
                reverse=True
            )
            
            # Keep the first (most recent), delete the rest
            predictions_to_delete = sorted_predictions[1:]
            
            print(f"Group {group_id}: Found {len(predictions)} BTC predictions, keeping most recent, deleting {len(predictions_to_delete)}")
            
            if dry_run:
                for pred in predictions_to_delete:
                    print(f"  [DRY RUN] Would delete: {pred.get('id')} (predicted_at: {pred.get('predicted_at')})")
                total_deleted += len(predictions_to_delete)
            else:
                # Delete the duplicates
                for pred in predictions_to_delete:
                    delete_query = """
                    MATCH (p:Prediction {id: $pred_id})
                    DETACH DELETE p
                    """
                    session.run(delete_query, pred_id=pred.get("id"))
                    print(f"  Deleted: {pred.get('id')} (predicted_at: {pred.get('predicted_at')})")
                    total_deleted += 1
    
    return total_deleted


def get_prediction_stats(driver, database: str = "neo4j"):
    """
    Get statistics about predictions in the database.
    
    Args:
        driver: Neo4j driver instance
        database: Database name
        
    Returns:
        Dictionary with statistics
    """
    query = """
    MATCH (p:Prediction)
    RETURN 
        count(p) as total_predictions,
        count(DISTINCT p.group_id) as unique_groups,
        collect(DISTINCT p.model_version) as model_versions,
        collect(DISTINCT p.domain) as domains
    """
    
    with driver.session(database=database) as session:
        result = session.run(query)
        record = result.single()
        
        if record:
            return {
                "total_predictions": record["total_predictions"],
                "unique_groups": record["unique_groups"],
                "model_versions": sorted(record["model_versions"]),
                "domains": sorted(record["domains"])
            }
        return {}


def main():
    """Main function to clean up predictions."""
    parser = argparse.ArgumentParser(
        description="Clean up Prediction nodes in Neo4j database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = Config()
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("Make sure .env file exists with NEO4J_PASSWORD set")
        sys.exit(1)
    
    # Connect to Neo4j
    print(f"🔌 Connecting to Neo4j at {config.neo4j_uri}...")
    
    try:
        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            encrypted=config.neo4j_encrypted,
        )
        
        # Verify connection
        driver.verify_connectivity()
        print("✅ Connected to Neo4j successfully\n")
        
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        sys.exit(1)
    
    try:
        # Get initial statistics
        print("📊 BEFORE CLEANUP:")
        print("=" * 60)
        stats_before = get_prediction_stats(driver, config.neo4j_database)
        print(f"Total Predictions:    {stats_before.get('total_predictions', 0)}")
        print(f"Unique Groups:        {stats_before.get('unique_groups', 0)}")
        print(f"Model Versions:       {', '.join(stats_before.get('model_versions', []))}")
        print(f"Domains:              {', '.join(stats_before.get('domains', []))}")
        print()
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print("=" * 60)
        else:
            print("⚠️  LIVE MODE - Changes will be permanent!")
            print("=" * 60)
            response = input("Continue? (yes/no): ")
            if response.lower() != "yes":
                print("Aborted.")
                driver.close()
                sys.exit(0)
        
        print()
        
        # Step 1: Delete model version 1 predictions
        print("🗑️  Step 1: Deleting predictions with model_version = '1'...")
        deleted_v1 = delete_model_version_1(driver, config.neo4j_database, args.dry_run)
        if args.dry_run:
            print(f"   [DRY RUN] Would delete {deleted_v1} predictions with model_version = '1'")
        else:
            print(f"   ✅ Deleted {deleted_v1} predictions with model_version = '1'")
        print()
        
        # Step 2: Delete duplicate BTC predictions
        print("🗑️  Step 2: Deleting duplicate BTC predictions (keeping most recent)...")
        deleted_duplicates = delete_duplicate_btc_predictions(driver, config.neo4j_database, args.dry_run)
        if args.dry_run:
            print(f"   [DRY RUN] Would delete {deleted_duplicates} duplicate BTC predictions")
        else:
            print(f"   ✅ Deleted {deleted_duplicates} duplicate BTC predictions")
        print()
        
        # Get final statistics
        print("📊 AFTER CLEANUP:")
        print("=" * 60)
        stats_after = get_prediction_stats(driver, config.neo4j_database)
        print(f"Total Predictions:    {stats_after.get('total_predictions', 0)}")
        print(f"Unique Groups:        {stats_after.get('unique_groups', 0)}")
        print(f"Model Versions:       {', '.join(stats_after.get('model_versions', []))}")
        print(f"Domains:              {', '.join(stats_after.get('domains', []))}")
        print()
        
        # Summary
        total_deleted = deleted_v1 + deleted_duplicates
        print("=" * 60)
        if args.dry_run:
            print(f"📋 SUMMARY (DRY RUN): Would delete {total_deleted} predictions total")
        else:
            print(f"✅ SUMMARY: Deleted {total_deleted} predictions total")
            print(f"   - Model version 1: {deleted_v1}")
            print(f"   - Duplicate BTC:   {deleted_duplicates}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        driver.close()
        print("\n🔌 Connection closed")


if __name__ == "__main__":
    main()


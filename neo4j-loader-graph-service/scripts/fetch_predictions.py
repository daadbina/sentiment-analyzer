#!/usr/bin/env python3
"""
Script to fetch all Prediction nodes from Neo4j and save to a text file.

Usage:
    python scripts/fetch_predictions.py [--output predictions.txt]
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from src.config import Config


def fetch_all_predictions(driver, database: str = "neo4j"):
    """
    Fetch all Prediction nodes from Neo4j.
    
    Args:
        driver: Neo4j driver instance
        database: Database name
        
    Returns:
        List of prediction dictionaries
    """
    query = """
    MATCH (p:Prediction)
    OPTIONAL MATCH (p)-[:PREDICTS]->(g:Group)
    RETURN p, g.id as group_id
    ORDER BY p.predicted_at DESC
    """
    
    predictions = []
    
    with driver.session(database=database) as session:
        result = session.run(query)
        
        for record in result:
            prediction_node = record["p"]
            group_id = record["group_id"]
            
            # Convert Neo4j node to dictionary
            prediction_dict = dict(prediction_node)
            
            # Add relationship info
            if group_id:
                prediction_dict["linked_group_id"] = group_id
            
            predictions.append(prediction_dict)
    
    return predictions


def format_prediction_for_text(prediction: dict, index: int) -> str:
    """
    Format a prediction dictionary as human-readable text.
    
    Args:
        prediction: Prediction dictionary
        index: Prediction number
        
    Returns:
        Formatted string
    """
    lines = []
    lines.append(f"\n{'='*80}")
    lines.append(f"PREDICTION #{index}")
    lines.append(f"{'='*80}")
    
    # Core fields
    lines.append(f"ID:              {prediction.get('id', 'N/A')}")
    lines.append(f"Group ID:        {prediction.get('group_id', 'N/A')}")
    lines.append(f"Linked Group:    {prediction.get('linked_group_id', 'N/A')}")
    lines.append(f"Domain:          {prediction.get('domain', 'N/A')}")
    lines.append(f"Probability:     {prediction.get('probability', 'N/A')}")
    lines.append(f"Confidence:      {prediction.get('confidence', 'N/A')}")
    lines.append(f"Model Version:   {prediction.get('model_version', 'N/A')}")
    lines.append(f"Predicted At:    {prediction.get('predicted_at', 'N/A')}")
    
    # Features (if present)
    features = prediction.get('features')
    if features:
        lines.append(f"\nFeatures:")
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except:
                pass
        
        if isinstance(features, dict):
            for key, value in features.items():
                lines.append(f"  - {key}: {value}")
        else:
            lines.append(f"  {features}")
    
    # Additional fields
    other_fields = {k: v for k, v in prediction.items() 
                   if k not in ['id', 'group_id', 'linked_group_id', 'domain', 
                               'probability', 'confidence', 'model_version', 
                               'predicted_at', 'features']}
    
    if other_fields:
        lines.append(f"\nAdditional Properties:")
        for key, value in other_fields.items():
            lines.append(f"  - {key}: {value}")
    
    return "\n".join(lines)


def main():
    """Main function to fetch and save predictions."""
    parser = argparse.ArgumentParser(
        description="Fetch all Prediction nodes from Neo4j and save to text file"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="predictions.txt",
        help="Output file path (default: predictions.txt)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text"
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
        print("✅ Connected to Neo4j successfully")
        
    except Exception as e:
        print(f"❌ Failed to connect to Neo4j: {e}")
        sys.exit(1)
    
    # Fetch predictions
    print(f"📊 Fetching all Prediction nodes...")
    
    try:
        predictions = fetch_all_predictions(driver, config.neo4j_database)
        print(f"✅ Found {len(predictions)} predictions")
        
    except Exception as e:
        print(f"❌ Failed to fetch predictions: {e}")
        driver.close()
        sys.exit(1)
    
    finally:
        driver.close()
    
    # Save to file
    output_path = Path(args.output)
    print(f"💾 Saving to {output_path}...")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            if args.json:
                # JSON output
                json.dump(predictions, f, indent=2, default=str)
            else:
                # Formatted text output
                f.write(f"PREDICTION NODES EXPORT\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Total Predictions: {len(predictions)}\n")
                
                for idx, prediction in enumerate(predictions, 1):
                    f.write(format_prediction_for_text(prediction, idx))
                
                f.write(f"\n\n{'='*80}\n")
                f.write(f"END OF EXPORT - Total: {len(predictions)} predictions\n")
                f.write(f"{'='*80}\n")
        
        print(f"✅ Successfully saved {len(predictions)} predictions to {output_path}")
        
    except Exception as e:
        print(f"❌ Failed to save file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


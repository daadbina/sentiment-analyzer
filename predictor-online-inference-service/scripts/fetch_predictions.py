#!/usr/bin/env python3
"""
Script to fetch all prediction table data with complete metadata.
Saves the results to a text file.
"""

import asyncio
import asyncpg
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✓ Loaded environment variables from {env_path}")
else:
    print(f"⚠ Warning: .env file not found at {env_path}")
    sys.exit(1)


async def fetch_all_predictions() -> list[dict[str, Any]]:
    """
    Fetch all predictions from the database.
    
    Returns:
        List of prediction dictionaries with all metadata
    """
    # Get database configuration from environment
    host = os.environ.get("POSTGRES_HOST")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    database = os.environ.get("POSTGRES_DATABASE")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    
    if not all([host, database, user, password]):
        raise ValueError("Missing required PostgreSQL configuration in .env file")
    
    print(f"Connecting to PostgreSQL at {host}:{port}/{database}...")
    
    # Connect to database
    conn = await asyncpg.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
    
    print("✓ Connected to PostgreSQL")
    
    try:
        # Query all predictions with all columns
        query = """
            SELECT 
                id,
                group_id,
                domain,
                prediction_probability,
                prediction_confidence,
                model_version,
                features,
                predicted_at,
                created_at,
                trace_id
            FROM predictions
            ORDER BY created_at DESC
        """
        
        print("Fetching all predictions...")
        rows = await conn.fetch(query)
        print(f"✓ Fetched {len(rows)} predictions")
        
        # Convert rows to dictionaries
        predictions = []
        for row in rows:
            prediction = {
                "id": row["id"],
                "group_id": row["group_id"],
                "domain": row["domain"],
                "prediction_probability": float(row["prediction_probability"]),
                "prediction_confidence": float(row["prediction_confidence"]),
                "model_version": row["model_version"],
                "features": row["features"],  # Already parsed as dict from JSONB
                "predicted_at": row["predicted_at"].isoformat() if row["predicted_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "trace_id": row["trace_id"],
            }
            predictions.append(prediction)
        
        return predictions
        
    finally:
        await conn.close()
        print("✓ Database connection closed")


def save_predictions_to_file(predictions: list[dict[str, Any]], output_file: str) -> None:
    """
    Save predictions to a text file in a readable format.
    
    Args:
        predictions: List of prediction dictionaries
        output_file: Path to output file
    """
    with open(output_file, "w", encoding="utf-8") as f:
        # Write header
        f.write("=" * 100 + "\n")
        f.write(f"PREDICTION TABLE DATA EXPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Records: {len(predictions)}\n")
        f.write("=" * 100 + "\n\n")
        
        # Write each prediction
        for i, pred in enumerate(predictions, 1):
            f.write(f"\n{'=' * 100}\n")
            f.write(f"PREDICTION #{i}\n")
            f.write(f"{'=' * 100}\n")
            f.write(f"ID:                      {pred['id']}\n")
            f.write(f"Group ID:                {pred['group_id']}\n")
            f.write(f"Domain:                  {pred['domain']}\n")
            f.write(f"Prediction Probability:  {pred['prediction_probability']:.6f}\n")
            f.write(f"Prediction Confidence:   {pred['prediction_confidence']:.6f}\n")
            f.write(f"Model Version:           {pred['model_version']}\n")
            f.write(f"Predicted At:            {pred['predicted_at']}\n")
            f.write(f"Created At:              {pred['created_at']}\n")
            f.write(f"Trace ID:                {pred['trace_id']}\n")
            f.write(f"\nFeatures (Full Metadata):\n")
            f.write("-" * 100 + "\n")
            # Pretty print the features JSON
            f.write(json.dumps(pred['features'], indent=2, ensure_ascii=False))
            f.write("\n")
    
    print(f"✓ Saved {len(predictions)} predictions to {output_file}")


async def main():
    """Main function to fetch and save predictions."""
    try:
        # Fetch all predictions
        predictions = await fetch_all_predictions()
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"predictions_export_{timestamp}.txt"
        
        # Save to file
        save_predictions_to_file(predictions, output_file)
        
        print(f"\n{'=' * 100}")
        print(f"SUCCESS: Exported {len(predictions)} predictions to {output_file}")
        print(f"{'=' * 100}")
        
    except Exception as e:
        print(f"\n{'=' * 100}")
        print(f"ERROR: {e}")
        print(f"{'=' * 100}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


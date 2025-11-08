#!/usr/bin/env python3
"""Examine extracted features for quality and suitability for training."""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import directly from modules
from src.config import Config
from src.clients.feast_client import FeastClient
from src.clients.redis_client import RedisClient
from src.utils import StructuredLogger

logger = StructuredLogger(__name__)

def examine_feast_features():
    """Fetch and examine features from Feast offline store."""
    logger.info("=" * 80)
    logger.info("EXAMINING FEATURES FROM FEAST OFFLINE STORE")
    logger.info("=" * 80)
    
    config = Config()
    feast_client = FeastClient(config.feast)
    
    try:
        # Get the feature store
        fs = feast_client.fs
        
        # Get the feature view
        feature_view = fs.get_feature_view("semantic_group_features")
        logger.info(f"Feature view: {feature_view.name}")
        logger.info(f"Features: {[f.name for f in feature_view.schema]}")
        
        # Try to get historical features (this requires entity dataframe)
        # For now, just check the registry
        logger.info("Feature view retrieved successfully from registry")
        
    except Exception as e:
        logger.error(f"Error examining Feast features: {e}", exc_info=True)

def examine_delta_lake_features():
    """Fetch and examine features from Delta Lake."""
    logger.info("=" * 80)
    logger.info("EXAMINING FEATURES FROM DELTA LAKE")
    logger.info("=" * 80)
    
    try:
        from deltalake import DeltaTable
        
        delta_path = "data/feast/offline_store/semantic_group_features"
        
        if not os.path.exists(delta_path):
            logger.warning(f"Delta Lake table not found at {delta_path}")
            return
        
        # Read Delta Lake table
        dt = DeltaTable(delta_path)
        df = dt.to_pandas()
        
        logger.info(f"Delta Lake table shape: {df.shape}")
        logger.info(f"Columns: {list(df.columns)}")
        logger.info(f"Data types:\n{df.dtypes}")
        
        # Check for null values
        logger.info("\n" + "=" * 80)
        logger.info("NULL VALUE ANALYSIS")
        logger.info("=" * 80)
        null_counts = df.isnull().sum()
        if null_counts.sum() > 0:
            logger.warning(f"Found null values:\n{null_counts[null_counts > 0]}")
        else:
            logger.info("✓ No null values found")
        
        # Check for NaN and Inf values
        logger.info("\n" + "=" * 80)
        logger.info("NaN AND INF ANALYSIS")
        logger.info("=" * 80)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        nan_count = df[numeric_cols].isna().sum().sum()
        inf_count = np.isinf(df[numeric_cols]).sum().sum()
        
        logger.info(f"NaN values: {nan_count}")
        logger.info(f"Inf values: {inf_count}")
        
        if nan_count > 0 or inf_count > 0:
            logger.warning("Found NaN or Inf values!")
        else:
            logger.info("✓ No NaN or Inf values found")
        
        # Check value ranges
        logger.info("\n" + "=" * 80)
        logger.info("VALUE RANGE ANALYSIS")
        logger.info("=" * 80)
        
        for col in numeric_cols:
            min_val = df[col].min()
            max_val = df[col].max()
            mean_val = df[col].mean()
            std_val = df[col].std()
            
            logger.info(f"{col}:")
            logger.info(f"  Min: {min_val:.6f}, Max: {max_val:.6f}")
            logger.info(f"  Mean: {mean_val:.6f}, Std: {std_val:.6f}")
        
        # Show sample data
        logger.info("\n" + "=" * 80)
        logger.info("SAMPLE DATA (first 5 rows)")
        logger.info("=" * 80)
        logger.info(f"\n{df.head().to_string()}")
        
        # Check for duplicates
        logger.info("\n" + "=" * 80)
        logger.info("DUPLICATE ANALYSIS")
        logger.info("=" * 80)
        duplicates = df.duplicated(subset=['group_id']).sum()
        logger.info(f"Duplicate group_ids: {duplicates}")
        
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate group_ids")
        else:
            logger.info("✓ No duplicate group_ids found")
        
        # Summary statistics
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY STATISTICS")
        logger.info("=" * 80)
        logger.info(f"\n{df.describe().to_string()}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ FEATURE QUALITY CHECK COMPLETE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error examining Delta Lake features: {e}", exc_info=True)

def examine_redis_features():
    """Fetch and examine features from Redis."""
    logger.info("=" * 80)
    logger.info("EXAMINING FEATURES FROM REDIS ONLINE STORE")
    logger.info("=" * 80)
    
    try:
        config = Config()
        redis_client = RedisClient(config.redis)
        
        # Get all keys
        keys = redis_client.client.keys("*")
        logger.info(f"Total keys in Redis: {len(keys)}")
        
        if len(keys) > 0:
            # Sample a few keys
            sample_keys = keys[:5]
            logger.info(f"\nSample keys: {sample_keys}")
            
            for key in sample_keys:
                value = redis_client.client.get(key)
                logger.info(f"Key: {key}, Value length: {len(value) if value else 0}")
        
        logger.info("✓ Redis features accessible")
        
    except Exception as e:
        logger.error(f"Error examining Redis features: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting feature examination...")
    
    examine_feast_features()
    examine_delta_lake_features()
    examine_redis_features()
    
    logger.info("\n" + "=" * 80)
    logger.info("FEATURE EXAMINATION COMPLETE")
    logger.info("=" * 80)


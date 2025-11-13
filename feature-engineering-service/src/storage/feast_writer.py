"""Feast writer for online and offline features using Feast Python SDK."""

from typing import Dict, Any
import pandas as pd
from datetime import datetime
from feast import FeatureStore
from feast.errors import PushSourceNotFoundException
import subprocess
import sys
import os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import FeastConfig

logger = StructuredLogger(__name__)


class FeastWriter:
    """Write features to Feast online and offline stores using Python SDK."""

    def __init__(self):
        """Initialize writer with Feast SDK."""
        config = FeastConfig()
        self.repo_path = config.repo_path
        self.push_source_name = "semantic_group_push_source"
        self._initialized = False

        # Calculate path to centralized offline store parquet file
        if self.repo_path == ".":
            current_file = Path(__file__).resolve()
            repo_abs_path = current_file.parent.parent.parent
        else:
            repo_abs_path = Path(self.repo_path).resolve()

        # Path to centralized offline store
        self.offline_store_path = repo_abs_path.parent / "feast" / "offline_store" / "semantic_groups.parquet"

        # Initialize Feast FeatureStore
        # This will read feature_store.yaml from the repo_path
        self._initialize_feature_store()

        logger.info(
            "Feast SDK writer initialized",
            repo_path=self.repo_path,
            push_source=self.push_source_name,
            offline_store_path=str(self.offline_store_path)
        )

    def _initialize_feature_store(self):
        """Initialize or reinitialize the Feast FeatureStore."""
        try:
            self.feature_store = FeatureStore(repo_path=self.repo_path)
            self._initialized = True
            logger.debug("FeatureStore initialized", repo_path=self.repo_path)
        except Exception as e:
            logger.error("Failed to initialize FeatureStore", error=str(e))
            raise

    def _apply_feast_definitions(self) -> bool:
        """
        Run 'feast apply' to register feature definitions.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Running 'feast apply' to register feature definitions...")

            # Determine the absolute path to the repo
            # repo_path is "." which means current working directory
            # We need to get the absolute path
            if self.repo_path == ".":
                # Get the directory where this file is located
                current_file = Path(__file__).resolve()
                # Go up to feature-engineering-service directory
                # __file__ is in src/storage/feast_writer.py
                repo_abs_path = current_file.parent.parent.parent
            else:
                repo_abs_path = Path(self.repo_path).resolve()

            # Use the feast executable from venv
            feast_exe = repo_abs_path / "venv311" / "Scripts" / "feast.exe"

            if not feast_exe.exists():
                logger.error(f"Feast executable not found: {feast_exe}")
                return False

            logger.info(f"Using feast executable: {feast_exe}")
            logger.info(f"Working directory: {repo_abs_path}")

            # Run feast apply
            result = subprocess.run(
                [str(feast_exe), "apply"],
                cwd=str(repo_abs_path),
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("Feast definitions applied successfully", stdout=result.stdout[:500])
                return True
            else:
                logger.error(
                    f"Failed to apply Feast definitions - stdout: {result.stdout[:500]}, stderr: {result.stderr[:500]}, return_code: {result.returncode}"
                )
                return False

        except subprocess.TimeoutExpired:
            logger.error("Feast apply timed out after 60 seconds")
            return False
        except Exception as e:
            logger.error(f"Error running feast apply: {str(e)} ({type(e).__name__})")
            return False

    def _write_to_parquet(self, feature_data: pd.DataFrame) -> bool:
        """
        Write features directly to the centralized parquet file.

        Args:
            feature_data: DataFrame with features to write

        Returns:
            True if successful
        """
        try:
            # Check if file exists and get its schema
            if self.offline_store_path.exists():
                # Read existing schema
                existing_table = pq.read_table(str(self.offline_store_path))
                target_schema = existing_table.schema

                # Convert new data to match existing schema
                table = pa.Table.from_pandas(feature_data, preserve_index=False, schema=target_schema)

                # Concatenate with new data
                combined_table = pa.concat_tables([existing_table, table])

                # Write back
                pq.write_table(combined_table, str(self.offline_store_path))
                logger.debug(f"Appended features to existing parquet file: {self.offline_store_path}")
            else:
                # Create new file with inferred schema
                self.offline_store_path.parent.mkdir(parents=True, exist_ok=True)
                table = pa.Table.from_pandas(feature_data, preserve_index=False)
                pq.write_table(table, str(self.offline_store_path))
                logger.debug(f"Created new parquet file: {self.offline_store_path}")

            return True

        except Exception as e:
            logger.error(f"Error writing to parquet file: {str(e)} ({type(e).__name__})")
            return False

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
        to: str = "offline"
    ) -> bool:
        """Push features to Feast offline store using PushSource.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary (28 features)
            to: Target store - "offline" only (online store not used)

        Returns:
            True if successful

        Raises:
            FeastWriteError: If push fails
        """
        try:
            # Prepare feature data with required fields
            timestamp = datetime.utcnow()

            # Create DataFrame with all required fields
            # Note: Use "timestamp" field name to match feature definition in features.py
            feature_data = pd.DataFrame([{
                "group_id": str(group_id),
                "timestamp": timestamp,
                **features,
            }])

            # Debug: Log feature columns
            logger.debug(f"Writing features to Feast: group_id={group_id}, columns={list(feature_data.columns)}, has_countries={'countries' in feature_data.columns}, has_btc_timestamp={'btc_timestamp' in feature_data.columns}")

            # Ensure timestamp is datetime type
            feature_data['timestamp'] = pd.to_datetime(feature_data['timestamp'])

            # Write directly to centralized parquet file
            if self._write_to_parquet(feature_data):
                logger.info(
                    "Features written to centralized offline store parquet",
                    group_id=group_id,
                    feature_count=len(features),
                    parquet_path=str(self.offline_store_path)
                )
                return True
            else:
                raise FeastWriteError("Failed to write features to parquet file")

        except (PushSourceNotFoundException, FileNotFoundError) as e:
            # Auto-initialize Feast registry if needed (for future compatibility)
            error_type = type(e).__name__
            logger.warning(
                f"Feast registry error ({error_type}) - attempting auto-initialization",
                push_source=self.push_source_name,
                group_id=group_id,
                error=str(e)
            )

            # Try to apply Feast definitions
            if self._apply_feast_definitions():
                # Reinitialize FeatureStore to pick up new registry
                logger.info("Reinitializing FeatureStore after applying definitions")
                self._initialize_feature_store()

                # Retry writing to parquet
                logger.info("Retrying feature write after initialization")
                if self._write_to_parquet(feature_data):
                    logger.info(
                        "Features written successfully after auto-initialization",
                        group_id=group_id,
                        feature_count=len(features)
                    )
                    return True
                else:
                    raise FeastWriteError("Failed to write features to parquet after auto-initialization")
            else:
                logger.error("Auto-initialization failed - cannot write features")
                raise FeastWriteError(f"Feast registry error and auto-initialization failed: {str(e)}")

        except Exception as e:
            logger.error(
                "Error pushing features to Feast offline store",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise FeastWriteError(f"Error pushing features to Feast offline store: {str(e)}")

    def close(self):
        """Close connection (no-op for Feast SDK)."""
        logger.info("Feast SDK writer closed")


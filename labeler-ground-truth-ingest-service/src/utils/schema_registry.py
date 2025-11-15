"""Schema Registry utilities for registering schemas at startup."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from src.config import config
from src.utils.trace import get_logger

logger = get_logger(__name__)


class SchemaRegistrationError(Exception):
    """Exception raised when schema registration fails."""
    pass


def register_schema(
    registry_url: str,
    subject: str,
    schema: Dict[str, Any]
) -> Optional[int]:
    """
    Register a schema in Schema Registry.
    
    Args:
        registry_url: Schema Registry URL
        subject: Subject name for the schema
        schema: Schema definition as dict
        
    Returns:
        Schema ID if successful, None if already registered
        
    Raises:
        SchemaRegistrationError: If registration fails
    """
    url = f"{registry_url.rstrip('/')}/subjects/{subject}/versions"
    headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
    payload = {"schema": json.dumps(schema)}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        schema_id = result.get("id")
        
        logger.info(
            f"Registered schema '{subject}' with ID {schema_id}",
            operation="register_schema",
            subject=subject,
            schema_id=schema_id
        )
        
        return schema_id
        
    except requests.exceptions.HTTPError as e:
        # If schema already exists, that's OK
        if e.response.status_code == 409:
            logger.info(
                f"Schema '{subject}' already registered",
                operation="register_schema",
                subject=subject
            )
            return None
        else:
            logger.error(
                f"Failed to register schema '{subject}': {str(e)}",
                operation="register_schema",
                subject=subject,
                error_type=type(e).__name__
            )
            raise SchemaRegistrationError(f"Failed to register schema '{subject}': {str(e)}")
            
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to register schema '{subject}': {str(e)}",
            operation="register_schema",
            subject=subject,
            error_type=type(e).__name__
        )
        raise SchemaRegistrationError(f"Failed to register schema '{subject}': {str(e)}")


def load_schema(schema_file: str) -> Dict[str, Any]:
    """
    Load Avro schema from file.
    
    Args:
        schema_file: Schema filename (e.g., "reconciliation_completed.avsc")
        
    Returns:
        Schema definition as dict
        
    Raises:
        FileNotFoundError: If schema file not found
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = Path(__file__).parent.parent.parent / "schemas" / schema_file
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        return json.load(f)


async def register_all_schemas() -> Dict[str, Optional[int]]:
    """
    Register all schemas at service startup.
    
    Returns:
        Dict mapping subject names to schema IDs
        
    Raises:
        SchemaRegistrationError: If any registration fails
    """
    registry_url = config.kafka.schema_registry_url
    
    # Define schemas to register
    schemas_to_register = [
        ("ground_truth-value", "ground_truth_value.avsc"),
        ("acled_label-value", "acled_label.avsc"),
        ("gdelt_label-value", "gdelt_label.avsc"),
        ("coingecko_label-value", "coingecko_label.avsc"),
        ("reconciliation_completed-value", "reconciliation_completed.avsc"),
    ]
    
    logger.info(
        f"Registering {len(schemas_to_register)} schemas with Schema Registry",
        operation="register_all_schemas",
        registry_url=registry_url
    )
    
    registered_schemas = {}
    
    for subject, schema_file in schemas_to_register:
        try:
            schema = load_schema(schema_file)
            schema_id = register_schema(registry_url, subject, schema)
            registered_schemas[subject] = schema_id
        except Exception as e:
            logger.error(
                f"Failed to register schema '{subject}': {str(e)}",
                operation="register_all_schemas",
                subject=subject,
                error_type=type(e).__name__
            )
            # Continue with other schemas even if one fails
            continue
    
    logger.info(
        f"Schema registration complete: {len(registered_schemas)}/{len(schemas_to_register)} schemas registered",
        operation="register_all_schemas",
        registered_count=len(registered_schemas),
        total_count=len(schemas_to_register)
    )
    
    return registered_schemas


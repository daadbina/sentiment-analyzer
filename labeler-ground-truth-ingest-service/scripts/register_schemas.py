"""Register Avro schemas in Schema Registry."""

import json
import sys
from pathlib import Path
import requests
from typing import Dict, Any


class SchemaRegistryClient:
    """Client for Schema Registry operations."""

    def __init__(self, registry_url: str):
        """Initialize Schema Registry client."""
        self.registry_url = registry_url.rstrip('/')
        self.session = requests.Session()

    def register_schema(self, subject: str, schema: Dict[str, Any]) -> int:
        """
        Register schema in Schema Registry.

        Returns:
            Schema ID
        """
        url = f"{self.registry_url}/subjects/{subject}/versions"
        headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        payload = {"schema": json.dumps(schema)}

        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            schema_id = result.get("id")

            print(f"✓ Registered schema '{subject}' with ID {schema_id}")
            return schema_id

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to register schema '{subject}': {str(e)}")
            raise

    def get_schema(self, schema_id: int) -> Dict[str, Any]:
        """Get schema by ID."""
        url = f"{self.registry_url}/schemas/ids/{schema_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            result = response.json()
            return json.loads(result.get("schema", "{}"))

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to get schema {schema_id}: {str(e)}")
            raise

    def check_compatibility(self, subject: str, schema: Dict[str, Any]) -> bool:
        """Check schema compatibility."""
        url = f"{self.registry_url}/compatibility/subjects/{subject}/versions/latest"
        headers = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
        payload = {"schema": json.dumps(schema)}

        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()
            is_compatible = result.get("is_compatible", False)

            if is_compatible:
                print(f"✓ Schema '{subject}' is compatible")
            else:
                print(f"✗ Schema '{subject}' is NOT compatible")

            return is_compatible

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to check compatibility for '{subject}': {str(e)}")
            return False


def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load Avro schema from file."""
    with open(schema_path, 'r') as f:
        return json.load(f)


def main():
    """Main entry point."""
    registry_url = "http://154.53.166.231:8081"
    schemas_dir = Path(__file__).parent.parent / "schemas"

    print(f"Registering schemas from {schemas_dir}")
    print(f"Schema Registry: {registry_url}\n")

    client = SchemaRegistryClient(registry_url)

    # Define schemas to register
    schemas_to_register = [
        ("ground_truth-value", "ground_truth_value.avsc"),
        ("acled_label-value", "acled_label.avsc"),
        ("gdelt_label-value", "gdelt_label.avsc"),
        ("coingecko_label-value", "coingecko_label.avsc"),
        ("reconciliation_completed-value", "reconciliation_completed.avsc"),
    ]

    registered_schemas = {}

    try:
        print("=" * 60)
        print("REGISTERING SCHEMAS")
        print("=" * 60)

        for subject, schema_file in schemas_to_register:
            schema_path = schemas_dir / schema_file

            if not schema_path.exists():
                print(f"✗ Schema file not found: {schema_path}")
                continue

            schema = load_schema(schema_path)
            schema_id = client.register_schema(subject, schema)
            registered_schemas[subject] = schema_id

        print("\n" + "=" * 60)
        print("CHECKING COMPATIBILITY")
        print("=" * 60)

        for subject, schema_file in schemas_to_register:
            schema_path = schemas_dir / schema_file

            if not schema_path.exists():
                continue

            schema = load_schema(schema_path)
            client.check_compatibility(subject, schema)

        print("\n" + "=" * 60)
        print("REGISTRATION SUMMARY")
        print("=" * 60)

        for subject, schema_id in registered_schemas.items():
            print(f"✓ {subject}: Schema ID {schema_id}")

        print(f"\nTotal schemas registered: {len(registered_schemas)}")
        print("✓ All schemas registered successfully!")

        return 0

    except Exception as e:
        print(f"\n✗ Error during schema registration: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


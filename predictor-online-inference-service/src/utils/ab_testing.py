"""
A/B testing utilities for model version selection.

Provides deterministic model version selection based on group IDs.
Supports traffic splitting across multiple model versions for experimentation.
"""

import hashlib
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ModelVariant:
    """
    Model variant configuration for A/B testing.

    Attributes:
        version: Model version identifier
        traffic_percentage: Percentage of traffic to route to this variant (0-100)
        description: Human-readable description of the variant
    """

    version: str
    traffic_percentage: float
    description: str = ""

    def __post_init__(self):
        """Validate traffic percentage."""
        if not 0 <= self.traffic_percentage <= 100:
            raise ValueError(
                f"Traffic percentage must be between 0 and 100, got {self.traffic_percentage}"
            )


class ABTestingStrategy:
    """
    A/B testing strategy for model version selection.

    Uses consistent hashing to deterministically assign group IDs to model variants.
    Ensures the same group ID always gets the same model version.
    """

    def __init__(self, variants: list[ModelVariant], default_version: str):
        """
        Initialize A/B testing strategy.

        Args:
            variants: List of model variants with traffic percentages
            default_version: Default model version to use if no variants match

        Raises:
            ValueError: If traffic percentages don't sum to 100 or variants are invalid
        """
        self.variants = variants
        self.default_version = default_version

        # Validate variants
        self._validate_variants()

        # Build cumulative distribution for variant selection
        self._build_distribution()

        logger.info(
            f"A/B testing strategy initialized: variants={len(variants)}, "
            f"default={default_version}"
        )

    def _validate_variants(self) -> None:
        """
        Validate variant configuration.

        Raises:
            ValueError: If variants are invalid
        """
        if not self.variants:
            raise ValueError("At least one variant must be provided")

        # Check for duplicate versions
        versions = [v.version for v in self.variants]
        if len(versions) != len(set(versions)):
            raise ValueError("Duplicate model versions found in variants")

        # Check traffic percentages sum to 100
        total_traffic = sum(v.traffic_percentage for v in self.variants)
        if not 99.9 <= total_traffic <= 100.1:  # Allow small floating point errors
            raise ValueError(f"Traffic percentages must sum to 100, got {total_traffic}")

    def _build_distribution(self) -> None:
        """Build cumulative distribution for variant selection."""
        self.cumulative_distribution: list[tuple[float, str]] = []
        cumulative = 0.0

        for variant in self.variants:
            cumulative += variant.traffic_percentage
            self.cumulative_distribution.append((cumulative, variant.version))

    def select_variant(self, group_id: str) -> str:
        """
        Select model variant for a given group ID.

        Uses consistent hashing to ensure the same group ID always gets
        the same model version.

        Args:
            group_id: Semantic group ID

        Returns:
            Model version to use for this group

        Example:
            strategy = ABTestingStrategy([
                ModelVariant("v1.0", 80, "Production model"),
                ModelVariant("v2.0", 20, "Experimental model"),
            ], default_version="v1.0")

            version = strategy.select_variant("group_123")
            # Returns "v1.0" or "v2.0" based on hash of "group_123"
        """
        # Hash the group ID to get a deterministic value
        hash_value = self._hash_group_id(group_id)

        # Convert hash to percentage (0-100)
        percentage = (hash_value % 10000) / 100.0

        # Find matching variant in cumulative distribution
        for cumulative, version in self.cumulative_distribution:
            if percentage <= cumulative:
                logger.debug(
                    f"Selected variant: group_id={group_id}, version={version}, "
                    f"hash_percentage={percentage:.2f}"
                )
                return version

        # Fallback to default (should not happen with valid distribution)
        logger.warning(
            f"No variant matched for group_id={group_id}, using default={self.default_version}"
        )
        return self.default_version

    def _hash_group_id(self, group_id: str) -> int:
        """
        Hash group ID to deterministic integer.

        Args:
            group_id: Semantic group ID

        Returns:
            Integer hash value
        """
        # Use SHA256 for consistent hashing
        hash_bytes = hashlib.sha256(group_id.encode()).digest()
        # Convert first 8 bytes to integer
        return int.from_bytes(hash_bytes[:8], byteorder="big")

    def get_variant_info(self) -> dict[str, dict]:
        """
        Get information about all variants.

        Returns:
            Dictionary mapping version to variant information
        """
        return {
            variant.version: {
                "traffic_percentage": variant.traffic_percentage,
                "description": variant.description,
            }
            for variant in self.variants
        }


class SimpleABTestingStrategy(ABTestingStrategy):
    """
    Simplified A/B testing strategy with two variants.

    Convenience class for common case of testing one variant against production.
    """

    def __init__(
        self,
        production_version: str,
        experiment_version: str,
        experiment_traffic_percentage: float,
        experiment_description: str = "Experimental variant",
    ):
        """
        Initialize simple A/B testing strategy.

        Args:
            production_version: Production model version
            experiment_version: Experimental model version
            experiment_traffic_percentage: Percentage of traffic for experiment (0-100)
            experiment_description: Description of the experiment

        Example:
            strategy = SimpleABTestingStrategy(
                production_version="v1.0",
                experiment_version="v2.0",
                experiment_traffic_percentage=10,
                experiment_description="Testing new feature engineering",
            )
        """
        production_traffic = 100 - experiment_traffic_percentage

        variants = [
            ModelVariant(production_version, production_traffic, "Production variant"),
            ModelVariant(experiment_version, experiment_traffic_percentage, experiment_description),
        ]

        super().__init__(variants, default_version=production_version)


class NoABTestingStrategy(ABTestingStrategy):
    """
    No-op A/B testing strategy that always returns the same version.

    Used when A/B testing is disabled.
    """

    def __init__(self, version: str):
        """
        Initialize no-op A/B testing strategy.

        Args:
            version: Model version to always use
        """
        variants = [ModelVariant(version, 100, "Single variant")]
        super().__init__(variants, default_version=version)

    def select_variant(self, group_id: str) -> str:
        """Always return the single version."""
        return self.default_version


def create_ab_testing_strategy(
    enable_ab_testing: bool,
    default_version: str,
    variants: list[dict] | None = None,
) -> ABTestingStrategy:
    """
    Create A/B testing strategy from configuration.

    Args:
        enable_ab_testing: Whether to enable A/B testing
        default_version: Default model version
        variants: Optional list of variant configurations
            Each variant should have: version, traffic_percentage, description

    Returns:
        ABTestingStrategy instance

    Example:
        strategy = create_ab_testing_strategy(
            enable_ab_testing=True,
            default_version="v1.0",
            variants=[
                {"version": "v1.0", "traffic_percentage": 80, "description": "Production"},
                {"version": "v2.0", "traffic_percentage": 20, "description": "Experiment"},
            ]
        )
    """
    if not enable_ab_testing or not variants or len(variants) == 1:
        # No A/B testing, use single version
        return NoABTestingStrategy(default_version)

    # Parse variants
    model_variants = []
    for variant_config in variants:
        model_variants.append(
            ModelVariant(
                version=variant_config["version"],
                traffic_percentage=variant_config["traffic_percentage"],
                description=variant_config.get("description", ""),
            )
        )

    return ABTestingStrategy(model_variants, default_version)

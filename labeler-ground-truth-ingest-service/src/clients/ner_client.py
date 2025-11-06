"""NER Entity Linking Service client for country extraction."""

import logging
import sys
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NERClient:
    """Client for NER Entity Linking Service to extract countries from text."""

    def __init__(self):
        """Initialize NER client with orchestrator."""
        try:
            # Add NER service to path for imports
            ner_service_path = Path(__file__).parent.parent.parent.parent / "ner-entity-linking-service"
            if str(ner_service_path) not in sys.path:
                sys.path.insert(0, str(ner_service_path))

            # Import NER components
            from src.ner.orchestrator import NEROrchestrator
            from src.ner.model_registry import NERModelRegistry
            from src.models import EntityType

            self.NEROrchestrator = NEROrchestrator
            self.NERModelRegistry = NERModelRegistry
            self.EntityType = EntityType

            # Initialize model registry and orchestrator
            self.model_registry = NERModelRegistry(cache_size=100)
            self.orchestrator = NEROrchestrator(self.model_registry)

            logger.info(
                "NER client initialized successfully",
                operation="ner_client_init"
            )

        except ImportError as e:
            logger.error(
                f"Failed to import NER components: {str(e)}",
                operation="ner_client_init",
                error_type="ImportError"
            )
            raise
        except Exception as e:
            logger.error(
                f"Failed to initialize NER client: {str(e)}",
                operation="ner_client_init",
                error_type=type(e).__name__
            )
            raise

    async def extract_countries(
        self,
        text: str,
        language: str = "en",
        article_id: str = "unknown"
    ) -> List[str]:
        """
        Extract country names from text using NER.

        Args:
            text: Article text to extract countries from
            language: Language code (default: "en")
            article_id: Article identifier for tracing

        Returns:
            List of country names extracted from text

        Raises:
            Exception: If NER extraction fails
        """
        if not text or not text.strip():
            logger.warning(
                "Empty text provided for country extraction",
                operation="extract_countries",
                article_id=article_id
            )
            return []

        try:
            logger.info(
                f"Extracting countries from text (length={len(text)}, language={language})",
                operation="extract_countries",
                article_id=article_id,
                text_length=len(text),
                language=language
            )

            # Extract entities using NER orchestrator
            ner_result = self.orchestrator.extract_entities(
                text=text,
                language=language,
                article_id=article_id
            )

            # Filter for LOCATION and GPE entity types
            countries = []
            for entity in ner_result.entities:
                entity_type = entity.entity_type
                # Handle both string and enum types
                entity_type_str = (
                    entity_type.value
                    if hasattr(entity_type, 'value')
                    else str(entity_type)
                )

                if entity_type_str in ["LOCATION", "GPE"]:
                    countries.append(entity.text)
                    logger.debug(
                        f"Extracted country: {entity.text} (confidence={entity.confidence})",
                        operation="extract_countries",
                        article_id=article_id,
                        entity_text=entity.text,
                        entity_type=entity_type_str,
                        confidence=entity.confidence
                    )

            logger.info(
                f"Successfully extracted {len(countries)} countries from text",
                operation="extract_countries",
                article_id=article_id,
                country_count=len(countries),
                countries=countries,
                coverage_score=ner_result.coverage_score,
                extraction_duration_ms=ner_result.extraction_duration_ms
            )

            return countries

        except Exception as e:
            logger.error(
                f"Failed to extract countries from text: {str(e)}",
                operation="extract_countries",
                article_id=article_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            # Return empty list instead of raising - allow processing to continue
            return []

    async def extract_countries_from_title(
        self,
        title: str,
        language: str = "en",
        article_id: str = "unknown"
    ) -> List[str]:
        """
        Extract country names from article title.

        Args:
            title: Article title
            language: Language code (default: "en")
            article_id: Article identifier for tracing

        Returns:
            List of country names extracted from title
        """
        if not title or not title.strip():
            logger.debug(
                "Empty title provided for country extraction",
                operation="extract_countries_from_title",
                article_id=article_id
            )
            return []

        return await self.extract_countries(
            text=title,
            language=language,
            article_id=article_id
        )

    async def extract_countries_from_content(
        self,
        content: str,
        language: str = "en",
        article_id: str = "unknown"
    ) -> List[str]:
        """
        Extract country names from article content.

        Args:
            content: Article content/body
            language: Language code (default: "en")
            article_id: Article identifier for tracing

        Returns:
            List of country names extracted from content
        """
        if not content or not content.strip():
            logger.debug(
                "Empty content provided for country extraction",
                operation="extract_countries_from_content",
                article_id=article_id
            )
            return []

        return await self.extract_countries(
            text=content,
            language=language,
            article_id=article_id
        )

    async def extract_countries_combined(
        self,
        title: str,
        content: str,
        language: str = "en",
        article_id: str = "unknown"
    ) -> List[str]:
        """
        Extract country names from both title and content, deduplicate.

        Args:
            title: Article title
            content: Article content
            language: Language code (default: "en")
            article_id: Article identifier for tracing

        Returns:
            Deduplicated list of country names
        """
        try:
            # Extract from title
            title_countries = await self.extract_countries_from_title(
                title=title,
                language=language,
                article_id=article_id
            )

            # Extract from content
            content_countries = await self.extract_countries_from_content(
                content=content,
                language=language,
                article_id=article_id
            )

            # Combine and deduplicate (preserve order)
            seen = set()
            combined = []
            for country in title_countries + content_countries:
                if country.lower() not in seen:
                    seen.add(country.lower())
                    combined.append(country)

            logger.info(
                f"Extracted {len(combined)} unique countries from title and content",
                operation="extract_countries_combined",
                article_id=article_id,
                title_countries=len(title_countries),
                content_countries=len(content_countries),
                unique_countries=len(combined),
                countries=combined
            )

            return combined

        except Exception as e:
            logger.error(
                f"Failed to extract countries from combined text: {str(e)}",
                operation="extract_countries_combined",
                article_id=article_id,
                error_type=type(e).__name__
            )
            return []


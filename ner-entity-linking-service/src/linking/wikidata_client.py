"""Wikidata entity linking client."""

import logging
import redis
import json
import requests
from typing import Optional, Dict, List
from src.resilience.retry_policy import get_retry_policy, BackoffStrategy
from src.resilience.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)


class WikidataClient:
    """Client for Wikidata entity linking with caching, retry, and circuit breaker."""

    def __init__(self, api_url: str, timeout: int = 30, redis_client: Optional[redis.Redis] = None, cache_ttl: int = 2592000):
        """
        Initialize Wikidata client.

        Args:
            api_url: Wikidata SPARQL endpoint URL
            timeout: Request timeout in seconds (default 30s per architecture)
            redis_client: Redis client for caching
            cache_ttl: Cache TTL in seconds (default 30 days)
        """
        self.api_url = api_url
        self.timeout = timeout
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl

        # Initialize retry policy with exponential backoff
        # Per architecture: 3 attempts with exponential backoff for resilience
        self.retry_policy = get_retry_policy(
            name="wikidata_search",
            max_attempts=3,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            retryable_exceptions=[Exception]
        )

        # Initialize circuit breaker
        self.circuit_breaker = get_circuit_breaker(
            name="wikidata_api",
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )

    def search_entity(
        self, entity_text: str, entity_type: str, language: str = "en"
    ) -> Optional[Dict]:
        """
        Search for entity in Wikidata using exact label matching with caching and retry.

        Args:
            entity_text: Entity text to search
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)
            language: Language code

        Returns:
            Entity data with wikidata_id if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"wikidata:{entity_text}:{entity_type}:{language}"
            if self.redis_client:
                try:
                    cached_result = self.redis_client.get(cache_key)
                    if cached_result:
                        logger.debug(f"Cache hit for entity: {entity_text}")
                        return json.loads(cached_result)
                except Exception as e:
                    logger.warning(f"Cache lookup failed: {e}")

            logger.debug(f"Searching Wikidata for entity: {entity_text} (type: {entity_type}, language: {language}, timeout: {self.timeout}s)")

            # Execute with retry policy and circuit breaker
            logger.debug(f"Circuit breaker state: {self.circuit_breaker.get_state()}")
            result = self.circuit_breaker.call(
                self.retry_policy.execute,
                self._search_wikidata,
                entity_text,
                entity_type,
                language
            )

            # Cache the result
            if result and self.redis_client:
                try:
                    self.redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(result)
                    )
                    logger.debug(f"Cached Wikidata result for: {entity_text}")
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")

            return result

        except Exception as e:
            logger.error(f"Error searching Wikidata for {entity_text}: {type(e).__name__}: {e}")
            logger.debug(f"Circuit breaker state after error: {self.circuit_breaker.get_state()}")
            return None

    def _search_wikidata(
        self, entity_text: str, entity_type: str, language: str = "en"
    ) -> Optional[Dict]:
        """
        Internal method to search Wikidata using MediaWiki Action API (used with retry policy).

        Uses the wbsearchentities endpoint which is:
        - More reliable than SPARQL (no timeout issues)
        - Designed specifically for entity search
        - Returns results with confidence scores
        - Supports fuzzy matching

        Args:
            entity_text: Entity text to search
            entity_type: Entity type
            language: Language code

        Returns:
            Entity data or None
        """
        # Use MediaWiki Action API endpoint for entity search
        # This is much more reliable than SPARQL for simple entity lookups
        api_url = "https://www.wikidata.org/w/api.php"

        logger.debug(f"Searching Wikidata using MediaWiki API for: {entity_text} (type: {entity_type}, language: {language})")

        try:
            # Call wbsearchentities endpoint
            params = {
                "action": "wbsearchentities",
                "search": entity_text,
                "language": language,
                "format": "json",
                "limit": 5,  # Get top 5 results
                "type": "item"  # Search for items, not properties
            }

            logger.debug(f"MediaWiki API params: {params}")

            # Make request with timeout
            response = requests.get(
                api_url,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "sentiment-analyzer-ner-service/1.0"}
            )

            logger.debug(f"MediaWiki API response status: {response.status_code}")

            # Raise exception for HTTP errors
            response.raise_for_status()

            results = response.json()
            search_results = results.get("search", [])

            logger.debug(f"Wikidata returned {len(search_results)} results for: {entity_text}")

            if not search_results:
                logger.debug(f"No Wikidata results for: {entity_text}")
                return None

            # Return first result (highest ranked by Wikidata)
            result = search_results[0]
            wikidata_id = result.get("id", "")
            label = result.get("label", entity_text)
            description = result.get("description", "")

            logger.debug(f"Found Wikidata match: {label} ({wikidata_id}) - confidence: {result.get('match', {}).get('type', 'unknown')}")

            return {
                "wikidata_id": wikidata_id,
                "label": label,
                "description": description,
                "country": "",  # Not available from search API, would need separate call
            }

        except requests.exceptions.Timeout:
            logger.error(f"Timeout searching Wikidata for {entity_text} after {self.timeout}s")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error searching Wikidata for {entity_text}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing Wikidata response for {entity_text}: {e}")
            raise



    def get_entity_info(self, wikidata_id: str) -> Optional[Dict]:
        """
        Get detailed entity information from Wikidata using MediaWiki API.

        Args:
            wikidata_id: Wikidata identifier (e.g., "Q42")

        Returns:
            Entity information
        """
        try:
            api_url = "https://www.wikidata.org/w/api.php"

            logger.debug(f"Getting entity info for: {wikidata_id}")

            # Use wbgetentities endpoint to get entity data
            params = {
                "action": "wbgetentities",
                "ids": wikidata_id,
                "format": "json",
                "languages": "en",
                "props": "labels|descriptions"
            }

            response = requests.get(
                api_url,
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "sentiment-analyzer-ner-service/1.0"}
            )

            response.raise_for_status()
            results = response.json()

            entities = results.get("entities", {})
            entity_data = entities.get(wikidata_id, {})

            if not entity_data or "missing" in entity_data:
                logger.debug(f"Entity not found: {wikidata_id}")
                return None

            labels = entity_data.get("labels", {})
            descriptions = entity_data.get("descriptions", {})

            label = labels.get("en", {}).get("value", "")
            description = descriptions.get("en", {}).get("value", "")

            logger.debug(f"Retrieved entity info: {label} ({wikidata_id})")

            return {
                "wikidata_id": wikidata_id,
                "label": label,
                "description": description,
                "country": "",  # Would need additional query to get country
            }

        except Exception as e:
            logger.error(f"Error getting Wikidata info for {wikidata_id}: {e}")
            return None


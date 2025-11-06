"""Wikidata entity linking client."""

import logging
import aiohttp
import redis
import json
from typing import Optional, Dict, List
from SPARQLWrapper import SPARQLWrapper, JSON
from src.resilience.retry_policy import get_retry_policy, BackoffStrategy
from src.resilience.circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)


class WikidataClient:
    """Client for Wikidata entity linking with caching, retry, and circuit breaker."""

    def __init__(self, api_url: str, timeout: int = 10, redis_client: Optional[redis.Redis] = None, cache_ttl: int = 2592000):
        """
        Initialize Wikidata client.

        Args:
            api_url: Wikidata SPARQL endpoint URL
            timeout: Request timeout in seconds
            redis_client: Redis client for caching
            cache_ttl: Cache TTL in seconds (default 30 days)
        """
        self.api_url = api_url
        self.timeout = timeout
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl

        # Initialize retry policy with exponential backoff
        # Reduced to 1 attempt to fail fast on Wikidata timeouts
        self.retry_policy = get_retry_policy(
            name="wikidata_search",
            max_attempts=1,
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

            logger.debug(f"Searching Wikidata for entity: {entity_text} (type: {entity_type}, language: {language})")

            # Execute with retry policy and circuit breaker
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
            logger.error(f"Error searching Wikidata for {entity_text}: {e}")
            return None

    def _search_wikidata(
        self, entity_text: str, entity_type: str, language: str = "en"
    ) -> Optional[Dict]:
        """
        Internal method to search Wikidata (used with retry policy).

        Args:
            entity_text: Entity text to search
            entity_type: Entity type
            language: Language code

        Returns:
            Entity data or None
        """
        sparql = SPARQLWrapper(self.api_url)

        # Build SPARQL query based on entity type
        query = self._build_search_query(entity_text, entity_type, language)
        logger.debug(f"SPARQL query: {query}")

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        sparql.setTimeout(self.timeout)  # CRITICAL FIX: Set timeout to prevent hanging

        results = sparql.query().convert()
        bindings = results.get("results", {}).get("bindings", [])

        logger.debug(f"Wikidata returned {len(bindings)} results for: {entity_text}")

        if not bindings:
            logger.debug(f"No Wikidata results for: {entity_text}")
            return None

        # Return first result (highest ranked)
        result = bindings[0]
        wikidata_id = result.get("item", {}).get("value", "").split("/")[-1]
        label = result.get("itemLabel", {}).get("value", entity_text)
        logger.debug(f"Found Wikidata match: {label} ({wikidata_id})")

        return {
            "wikidata_id": wikidata_id,
            "label": label,
            "description": result.get("itemDescription", {}).get("value", ""),
            "country": result.get("country", {}).get("value", ""),
        }

    def _build_search_query(self, entity_text: str, entity_type: str, language: str) -> str:
        """
        Build SPARQL query for entity search using flexible label matching.

        Uses a two-tier approach:
        1. First try exact label matching in specified language
        2. Fall back to case-insensitive prefix matching in English

        Args:
            entity_text: Entity text
            entity_type: Entity type
            language: Language code

        Returns:
            SPARQL query string
        """
        # Type mapping to Wikidata classes
        type_mapping = {
            "PERSON": "wd:Q5",  # human
            "ORGANIZATION": "wd:Q43229",  # organization
            "LOCATION": "wd:Q618123",  # geographic location
            "GPE": "wd:Q6256",  # country
            "CURRENCY": "wd:Q8142",  # currency
        }

        wikidata_type = type_mapping.get(entity_type, "")

        # Escape quotes in entity text for SPARQL
        escaped_text = entity_text.replace('"', '\\"')

        if wikidata_type:
            # Use flexible label matching: try exact first, then prefix matching
            query = f"""
            SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
              {{
                # Try exact label match in specified language
                ?item rdfs:label "{escaped_text}"@{language} .
              }} UNION {{
                # Try exact label match in English
                ?item rdfs:label "{escaped_text}"@en .
              }} UNION {{
                # Try case-insensitive prefix match using FILTER
                ?item rdfs:label ?label .
                FILTER(REGEX(?label, "^{escaped_text}$", "i"))
              }}
              ?item wdt:P31 {wikidata_type} .
              OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
            }}
            LIMIT 5
            """
        else:
            query = f"""
            SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
              {{
                # Try exact label match in specified language
                ?item rdfs:label "{escaped_text}"@{language} .
              }} UNION {{
                # Try exact label match in English
                ?item rdfs:label "{escaped_text}"@en .
              }} UNION {{
                # Try case-insensitive prefix match using FILTER
                ?item rdfs:label ?label .
                FILTER(REGEX(?label, "^{escaped_text}$", "i"))
              }}
              OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
            }}
            LIMIT 5
            """

        return query

    def get_entity_info(self, wikidata_id: str) -> Optional[Dict]:
        """
        Get detailed entity information from Wikidata.

        Args:
            wikidata_id: Wikidata identifier

        Returns:
            Entity information
        """
        try:
            sparql = SPARQLWrapper(self.api_url)

            query = f"""
            SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
              BIND(wd:{wikidata_id} AS ?item)
              OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            """

            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)

            results = sparql.query().convert()
            bindings = results.get("results", {}).get("bindings", [])

            if not bindings:
                return None

            result = bindings[0]
            return {
                "wikidata_id": wikidata_id,
                "label": result.get("itemLabel", {}).get("value", ""),
                "description": result.get("itemDescription", {}).get("value", ""),
                "country": result.get("country", {}).get("value", ""),
            }

        except Exception as e:
            logger.error(f"Error getting Wikidata info for {wikidata_id}: {e}")
            return None


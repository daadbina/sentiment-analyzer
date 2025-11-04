"""Wikidata entity linking client."""

import logging
import aiohttp
import time
from typing import Optional, Dict, List
from SPARQLWrapper import SPARQLWrapper, JSON

logger = logging.getLogger(__name__)


class WikidataClient:
    """Client for Wikidata entity linking."""

    def __init__(self, api_url: str, timeout: int = 10):
        """
        Initialize Wikidata client.

        Args:
            api_url: Wikidata SPARQL endpoint URL
            timeout: Request timeout in seconds
        """
        self.api_url = api_url
        self.timeout = timeout

    def search_entity(
        self, entity_text: str, entity_type: str, language: str = "en"
    ) -> Optional[Dict]:
        """
        Search for entity in Wikidata with retry logic.

        Args:
            entity_text: Entity text to search
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)
            language: Language code

        Returns:
            Entity data with wikidata_id if found, None otherwise
        """
        max_retries = 2
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.debug(f"Searching Wikidata for entity: {entity_text} (type: {entity_type}, language: {language}, attempt: {attempt + 1})")

                sparql = SPARQLWrapper(self.api_url)

                # Build SPARQL query based on entity type
                query = self._build_search_query(entity_text, entity_type, language)
                logger.debug(f"SPARQL query: {query}")

                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)

                results = sparql.query().convert()
                bindings = results.get("results", {}).get("bindings", [])

                logger.debug(f"Wikidata returned {len(bindings)} results for: {entity_text}")

                if not bindings:
                    logger.debug(f"No Wikidata results for: {entity_text}, trying fallback search")
                    # Try fallback with prefix matching
                    return self._fallback_search(entity_text, entity_type, language)

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

            except Exception as e:
                logger.warning(f"Error searching Wikidata for {entity_text} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Failed to search Wikidata for {entity_text} after {max_retries} attempts")
                    return None

    def _build_search_query(self, entity_text: str, entity_type: str, language: str) -> str:
        """
        Build SPARQL query for entity search using exact label matching.

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
            # Use exact label matching with rdfs:label
            query = f"""
            SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
              ?item rdfs:label "{escaped_text}"@{language} .
              ?item wdt:P31 {wikidata_type} .
              OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
            }}
            LIMIT 5
            """
        else:
            query = f"""
            SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
              ?item rdfs:label "{escaped_text}"@{language} .
              OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
            }}
            LIMIT 5
            """

        return query

    def _fallback_search(self, entity_text: str, entity_type: str, language: str) -> Optional[Dict]:
        """
        Fallback search using case-insensitive prefix matching with retry logic.

        Args:
            entity_text: Entity text
            entity_type: Entity type
            language: Language code

        Returns:
            Entity data if found, None otherwise
        """
        max_retries = 2
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempting fallback prefix search for: {entity_text} (attempt {attempt + 1}/{max_retries})")

                sparql = SPARQLWrapper(self.api_url)

                # Type mapping to Wikidata classes
                type_mapping = {
                    "PERSON": "wd:Q5",
                    "ORGANIZATION": "wd:Q43229",
                    "LOCATION": "wd:Q618123",
                    "GPE": "wd:Q6256",
                    "CURRENCY": "wd:Q8142",
                }

                wikidata_type = type_mapping.get(entity_type, "")
                escaped_text = entity_text.replace('"', '\\"')

                if wikidata_type:
                    query = f"""
                    SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
                      ?item rdfs:label ?label .
                      FILTER(STRSTARTS(LCASE(?label), LCASE("{escaped_text}")))
                      ?item wdt:P31 {wikidata_type} .
                      OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
                      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
                    }}
                    ORDER BY ?itemLabel
                    LIMIT 5
                    """
                else:
                    query = f"""
                    SELECT ?item ?itemLabel ?itemDescription ?country WHERE {{
                      ?item rdfs:label ?label .
                      FILTER(STRSTARTS(LCASE(?label), LCASE("{escaped_text}")))
                      OPTIONAL {{ ?item wdt:P17 ?countryEntity . ?countryEntity rdfs:label ?country . }}
                      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{language},en" . }}
                    }}
                    ORDER BY ?itemLabel
                    LIMIT 5
                    """

                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)

                results = sparql.query().convert()
                bindings = results.get("results", {}).get("bindings", [])

                logger.debug(f"Fallback search returned {len(bindings)} results for: {entity_text}")

                if not bindings:
                    return None

                # Return first result
                result = bindings[0]
                wikidata_id = result.get("item", {}).get("value", "").split("/")[-1]
                label = result.get("itemLabel", {}).get("value", entity_text)
                logger.debug(f"Fallback found: {label} ({wikidata_id})")

                return {
                    "wikidata_id": wikidata_id,
                    "label": label,
                    "description": result.get("itemDescription", {}).get("value", ""),
                    "country": result.get("country", {}).get("value", ""),
                }

            except Exception as e:
                logger.warning(f"Error in fallback search for {entity_text} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Failed fallback search for {entity_text} after {max_retries} attempts")
                    return None

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


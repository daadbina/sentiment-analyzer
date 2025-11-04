"""
DBpedia Spotlight client for entity linking.
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from prometheus_client import Counter, Histogram, REGISTRY
import time

logger = logging.getLogger(__name__)

# Global metrics (registered once)
try:
    _dbpedia_requests = REGISTRY._names_to_collectors.get("ner_dbpedia_requests_total")
    if _dbpedia_requests is None:
        _dbpedia_requests = Counter(
            "ner_dbpedia_requests_total",
            "Total DBpedia Spotlight requests",
            ["language", "status"],
        )
except:
    _dbpedia_requests = Counter(
        "ner_dbpedia_requests_total",
        "Total DBpedia Spotlight requests",
        ["language", "status"],
    )

try:
    _dbpedia_latency = REGISTRY._names_to_collectors.get("ner_dbpedia_latency_seconds")
    if _dbpedia_latency is None:
        _dbpedia_latency = Histogram(
            "ner_dbpedia_latency_seconds",
            "DBpedia Spotlight request latency",
            ["language"],
        )
except:
    _dbpedia_latency = Histogram(
        "ner_dbpedia_latency_seconds",
        "DBpedia Spotlight request latency",
        ["language"],
    )

try:
    _dbpedia_errors = REGISTRY._names_to_collectors.get("ner_dbpedia_errors_total")
    if _dbpedia_errors is None:
        _dbpedia_errors = Counter(
            "ner_dbpedia_errors_total",
            "Total DBpedia Spotlight errors",
            ["error_type"],
        )
except:
    _dbpedia_errors = Counter(
        "ner_dbpedia_errors_total",
        "Total DBpedia Spotlight errors",
        ["error_type"],
    )


class DBpediaSpotlightClient:
    """Client for DBpedia Spotlight entity linking service."""

    def __init__(self, base_url: str = "https://api.dbpedia-spotlight.org"):
        """
        Initialize DBpedia Spotlight client.

        Args:
            base_url: Base URL for DBpedia Spotlight API
        """
        self.base_url = base_url
        self.timeout = 10

        # Use global metrics
        self.dbpedia_requests = _dbpedia_requests
        self.dbpedia_latency = _dbpedia_latency
        self.dbpedia_errors = _dbpedia_errors

    def annotate(
        self,
        text: str,
        language: str = "en",
        confidence: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Annotate text with DBpedia entities.
        
        Args:
            text: Text to annotate
            language: Language code (default: en)
            confidence: Confidence threshold (default: 0.5)
            
        Returns:
            Annotation result or None if error
        """
        try:
            url = f"{self.base_url}/{language}/annotate"
            
            params = {
                "text": text,
                "confidence": confidence,
                "support": 20,
            }
            
            headers = {
                "Accept": "application/json",
            }
            
            start_time = time.time()
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            latency = time.time() - start_time
            
            self.dbpedia_latency.labels(language=language).observe(latency)
            
            if response.status_code == 200:
                self.dbpedia_requests.labels(language=language, status="success").inc()
                logger.debug(f"DBpedia annotation successful for {language}")
                return response.json()
            else:
                self.dbpedia_requests.labels(language=language, status="error").inc()
                self.dbpedia_errors.labels(error_type="http_error").inc()
                logger.warning(f"DBpedia error: {response.status_code}")
                return None
                
        except requests.Timeout:
            self.dbpedia_errors.labels(error_type="timeout").inc()
            logger.error(f"DBpedia timeout for language {language}")
            return None
        except requests.RequestException as e:
            self.dbpedia_errors.labels(error_type="request_error").inc()
            logger.error(f"DBpedia request error: {e}")
            return None
        except Exception as e:
            self.dbpedia_errors.labels(error_type="unknown").inc()
            logger.error(f"DBpedia error: {e}")
            return None

    def extract_entities(
        self,
        text: str,
        language: str = "en",
        confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from text using DBpedia Spotlight.
        
        Args:
            text: Text to extract entities from
            language: Language code
            confidence: Confidence threshold
            
        Returns:
            List of extracted entities
        """
        result = self.annotate(text, language, confidence)
        
        if result is None:
            return []
        
        entities = []
        if "Resources" in result:
            for resource in result["Resources"]:
                entity = {
                    "text": resource.get("surfaceForm", ""),
                    "dbpedia_uri": resource.get("@URI", ""),
                    "dbpedia_type": resource.get("@types", ""),
                    "confidence": float(resource.get("@similarityScore", 0)),
                    "offset": int(resource.get("@offset", 0)),
                }
                entities.append(entity)
        
        logger.debug(f"Extracted {len(entities)} entities from DBpedia")
        return entities

    def get_entity_info(self, dbpedia_uri: str) -> Optional[Dict[str, Any]]:
        """
        Get entity information from DBpedia URI.
        
        Args:
            dbpedia_uri: DBpedia entity URI
            
        Returns:
            Entity information or None
        """
        try:
            # Extract resource name from URI
            resource_name = dbpedia_uri.split("/resource/")[-1]
            
            url = f"https://dbpedia.org/data/{resource_name}.json"
            
            start_time = time.time()
            response = requests.get(url, timeout=self.timeout)
            latency = time.time() - start_time
            
            self.dbpedia_latency.labels(language="en").observe(latency)
            
            if response.status_code == 200:
                self.dbpedia_requests.labels(language="en", status="success").inc()
                return response.json()
            else:
                self.dbpedia_requests.labels(language="en", status="error").inc()
                return None
                
        except Exception as e:
            self.dbpedia_errors.labels(error_type="info_error").inc()
            logger.error(f"Error getting entity info: {e}")
            return None

    def link_entity(
        self,
        entity_text: str,
        language: str = "en",
        confidence: float = 0.5,
    ) -> Optional[Dict[str, Any]]:
        """
        Link a single entity to DBpedia.
        
        Args:
            entity_text: Entity text to link
            language: Language code
            confidence: Confidence threshold
            
        Returns:
            Linked entity or None
        """
        entities = self.extract_entities(entity_text, language, confidence)
        
        if entities:
            return entities[0]
        
        return None


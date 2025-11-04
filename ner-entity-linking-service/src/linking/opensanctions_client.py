"""
OpenSanctions client for entity verification and sanctions checking.
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from prometheus_client import Counter, Histogram, REGISTRY
import time

logger = logging.getLogger(__name__)

# Global metrics (registered once)
try:
    _opensanctions_requests = REGISTRY._names_to_collectors.get("ner_opensanctions_requests_total")
    if _opensanctions_requests is None:
        _opensanctions_requests = Counter(
            "ner_opensanctions_requests_total",
            "Total OpenSanctions requests",
            ["status"],
        )
except:
    _opensanctions_requests = Counter(
        "ner_opensanctions_requests_total",
        "Total OpenSanctions requests",
        ["status"],
    )

try:
    _opensanctions_latency = REGISTRY._names_to_collectors.get("ner_opensanctions_latency_seconds")
    if _opensanctions_latency is None:
        _opensanctions_latency = Histogram(
            "ner_opensanctions_latency_seconds",
            "OpenSanctions request latency",
        )
except:
    _opensanctions_latency = Histogram(
        "ner_opensanctions_latency_seconds",
        "OpenSanctions request latency",
    )

try:
    _opensanctions_errors = REGISTRY._names_to_collectors.get("ner_opensanctions_errors_total")
    if _opensanctions_errors is None:
        _opensanctions_errors = Counter(
            "ner_opensanctions_errors_total",
            "Total OpenSanctions errors",
            ["error_type"],
        )
except:
    _opensanctions_errors = Counter(
        "ner_opensanctions_errors_total",
        "Total OpenSanctions errors",
        ["error_type"],
    )

try:
    _sanctions_found = REGISTRY._names_to_collectors.get("ner_sanctions_found_total")
    if _sanctions_found is None:
        _sanctions_found = Counter(
            "ner_sanctions_found_total",
            "Total sanctioned entities found",
        )
except:
    _sanctions_found = Counter(
        "ner_sanctions_found_total",
        "Total sanctioned entities found",
    )


class OpenSanctionsClient:
    """Client for OpenSanctions entity verification."""

    def __init__(self, base_url: str = "https://api.opensanctions.org"):
        """
        Initialize OpenSanctions client.

        Args:
            base_url: Base URL for OpenSanctions API
        """
        self.base_url = base_url
        self.timeout = 10

        # Use global metrics
        self.opensanctions_requests = _opensanctions_requests
        self.opensanctions_latency = _opensanctions_latency
        self.opensanctions_errors = _opensanctions_errors
        self.sanctions_found = _sanctions_found

    def search(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Search for entity in OpenSanctions database.
        
        Args:
            entity_name: Entity name to search
            entity_type: Entity type (person, company, etc.)
            
        Returns:
            Search result or None
        """
        try:
            url = f"{self.base_url}/search"
            
            params = {
                "q": entity_name,
            }
            
            if entity_type:
                params["schema"] = entity_type
            
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
            
            self.opensanctions_latency.observe(latency)
            
            if response.status_code == 200:
                self.opensanctions_requests.labels(status="success").inc()
                logger.debug(f"OpenSanctions search successful for {entity_name}")
                return response.json()
            else:
                self.opensanctions_requests.labels(status="error").inc()
                self.opensanctions_errors.labels(error_type="http_error").inc()
                logger.warning(f"OpenSanctions error: {response.status_code}")
                return None
                
        except requests.Timeout:
            self.opensanctions_errors.labels(error_type="timeout").inc()
            logger.error(f"OpenSanctions timeout for {entity_name}")
            return None
        except requests.RequestException as e:
            self.opensanctions_errors.labels(error_type="request_error").inc()
            logger.error(f"OpenSanctions request error: {e}")
            return None
        except Exception as e:
            self.opensanctions_errors.labels(error_type="unknown").inc()
            logger.error(f"OpenSanctions error: {e}")
            return None

    def check_sanctions(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if entity is sanctioned.
        
        Args:
            entity_name: Entity name to check
            entity_type: Entity type
            
        Returns:
            Sanctions check result
        """
        result = self.search(entity_name, entity_type)
        
        if result is None:
            return {
                "is_sanctioned": False,
                "matches": [],
                "confidence": 0.0,
            }
        
        matches = result.get("results", [])
        
        if matches:
            self.sanctions_found.inc()
            
            return {
                "is_sanctioned": True,
                "matches": matches,
                "confidence": float(matches[0].get("score", 0)),
            }
        
        return {
            "is_sanctioned": False,
            "matches": [],
            "confidence": 0.0,
        }

    def get_entity_details(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about entity.
        
        Args:
            entity_id: OpenSanctions entity ID
            
        Returns:
            Entity details or None
        """
        try:
            url = f"{self.base_url}/entities/{entity_id}"
            
            headers = {
                "Accept": "application/json",
            }
            
            start_time = time.time()
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
            latency = time.time() - start_time
            
            self.opensanctions_latency.observe(latency)
            
            if response.status_code == 200:
                self.opensanctions_requests.labels(status="success").inc()
                return response.json()
            else:
                self.opensanctions_requests.labels(status="error").inc()
                return None
                
        except Exception as e:
            self.opensanctions_errors.labels(error_type="details_error").inc()
            logger.error(f"Error getting entity details: {e}")
            return None

    def verify_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify entity against OpenSanctions database.
        
        Args:
            entity_name: Entity name to verify
            entity_type: Entity type
            
        Returns:
            Verification result
        """
        sanctions_result = self.check_sanctions(entity_name, entity_type)
        
        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "is_sanctioned": sanctions_result["is_sanctioned"],
            "sanctions_matches": sanctions_result["matches"],
            "sanctions_confidence": sanctions_result["confidence"],
            "verified": True,
        }


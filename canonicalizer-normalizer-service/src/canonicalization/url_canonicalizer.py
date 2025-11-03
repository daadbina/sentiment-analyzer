"""URL canonicalization module."""

import logging
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, unquote
from typing import Optional, Tuple
import tldextract

from src.exceptions import URLCanonicalizationError
from src.models import URLNormalizationResult

logger = logging.getLogger(__name__)

# Tracking parameters to remove
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid",
    "sessionid", "session_id", "sid", "jsessionid",
    "phpsessid", "aspsessionid",
}


class URLCanonicalizer:
    """URL canonicalization engine."""

    def __init__(self, redirect_max_hops: int = 3, redirect_timeout_seconds: int = 5):
        """Initialize URL canonicalizer.

        Args:
            redirect_max_hops: Maximum number of redirects to follow
            redirect_timeout_seconds: Timeout for redirect resolution
        """
        self.redirect_max_hops = redirect_max_hops
        self.redirect_timeout_seconds = redirect_timeout_seconds

    def canonicalize(self, url: str) -> URLNormalizationResult:
        """Canonicalize URL.

        Args:
            url: URL to canonicalize

        Returns:
            URLNormalizationResult with normalized URL and metadata
        """
        try:
            # Step 1: Protocol standardization
            normalized_url = self._standardize_protocol(url)

            # Step 2: Parse URL
            parsed = urlparse(normalized_url)

            # Step 3: Parameter normalization
            normalized_url = self._normalize_parameters(parsed)

            # Step 4: Path normalization
            normalized_url = self._normalize_path(normalized_url)

            # Step 5: Extract domain
            domain = self._extract_domain(normalized_url)

            # Step 6: Compute URL hash
            url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()

            return URLNormalizationResult(
                original_url=url,
                normalized_url=normalized_url,
                url_hash=url_hash,
                canonicalized=True,
                domain=domain,
            )

        except Exception as e:
            logger.error(f"URL canonicalization failed for {url}: {e}")
            return URLNormalizationResult(
                original_url=url,
                normalized_url=url,
                url_hash=hashlib.sha256(url.encode()).hexdigest(),
                canonicalized=False,
                domain="",
                error=str(e),
            )

    def _standardize_protocol(self, url: str) -> str:
        """Standardize protocol to HTTPS.

        Args:
            url: URL to standardize

        Returns:
            URL with standardized protocol
        """
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Convert http to https
        if url.startswith("http://"):
            url = "https://" + url[7:]

        return url

    def _normalize_parameters(self, parsed) -> str:
        """Normalize query parameters.

        Args:
            parsed: Parsed URL

        Returns:
            URL with normalized parameters
        """
        if not parsed.query:
            return urlunparse(parsed)

        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove tracking parameters
        filtered_params = {
            k: v for k, v in params.items()
            if k.lower() not in TRACKING_PARAMS
        }

        # Sort parameters alphabetically
        sorted_params = sorted(filtered_params.items())

        # Reconstruct query string
        new_query = urlencode(sorted_params, doseq=True)

        # Reconstruct URL
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            ""  # Remove fragment
        ))

    def _normalize_path(self, url: str) -> str:
        """Normalize URL path.

        Args:
            url: URL to normalize

        Returns:
            URL with normalized path
        """
        parsed = urlparse(url)

        # Convert to lowercase for case-insensitive domains
        netloc = parsed.netloc.lower()

        # Remove www prefix
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Remove default ports
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        # Decode percent-encoded characters
        path = unquote(parsed.path)

        # Remove trailing slash
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]

        # Reconstruct URL without fragment
        return urlunparse((
            parsed.scheme,
            netloc,
            path,
            parsed.params,
            parsed.query,
            ""  # Remove fragment
        ))

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: URL to extract domain from

        Returns:
            Domain name
        """
        try:
            parsed = urlparse(url)
            extracted = tldextract.extract(parsed.netloc)
            return extracted.domain
        except Exception as e:
            logger.error(f"Failed to extract domain from {url}: {e}")
            return ""


"""Geographic location extraction from article content."""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Country patterns for extraction (ISO 3166-1 alpha-2 codes)
COUNTRY_PATTERNS = {
    "US": r"\b(United States|USA|America|U\.S\.|US|American)\b",
    "GB": r"\b(United Kingdom|UK|Britain|England|British)\b",
    "CN": r"\b(China|Chinese|PRC|People's Republic)\b",
    "RU": r"\b(Russia|Russian|USSR|Soviet)\b",
    "IN": r"\b(India|Indian)\b",
    "BR": r"\b(Brazil|Brazilian)\b",
    "DE": r"\b(Germany|German)\b",
    "FR": r"\b(France|French)\b",
    "JP": r"\b(Japan|Japanese)\b",
    "KR": r"\b(Korea|Korean|South Korea)\b",
    "IR": r"\b(Iran|Iranian|Persia|Persian)\b",
    "SA": r"\b(Saudi Arabia|Saudi|Saudi Arabian)\b",
    "AE": r"\b(UAE|United Arab Emirates|Emirates)\b",
    "IL": r"\b(Israel|Israeli)\b",
    "PS": r"\b(Palestine|Palestinian)\b",
    "SY": r"\b(Syria|Syrian)\b",
    "IQ": r"\b(Iraq|Iraqi)\b",
    "EG": r"\b(Egypt|Egyptian)\b",
    "TR": r"\b(Turkey|Turkish)\b",
    "AU": r"\b(Australia|Australian)\b",
    "CA": r"\b(Canada|Canadian)\b",
    "MX": r"\b(Mexico|Mexican)\b",
    "ES": r"\b(Spain|Spanish)\b",
    "IT": r"\b(Italy|Italian)\b",
    "NL": r"\b(Netherlands|Dutch)\b",
    "BE": r"\b(Belgium|Belgian)\b",
    "SE": r"\b(Sweden|Swedish)\b",
    "NO": r"\b(Norway|Norwegian)\b",
    "DK": r"\b(Denmark|Danish)\b",
    "PL": r"\b(Poland|Polish)\b",
    "UA": r"\b(Ukraine|Ukrainian)\b",
    "ZA": r"\b(South Africa|South African)\b",
    "NG": r"\b(Nigeria|Nigerian)\b",
    "KE": r"\b(Kenya|Kenyan)\b",
    "TH": r"\b(Thailand|Thai)\b",
    "VN": r"\b(Vietnam|Vietnamese)\b",
    "ID": r"\b(Indonesia|Indonesian)\b",
    "MY": r"\b(Malaysia|Malaysian)\b",
    "SG": r"\b(Singapore|Singaporean)\b",
    "PH": r"\b(Philippines|Philippine)\b",
    "NZ": r"\b(New Zealand|New Zealander)\b",
}

# URL TLD to country mapping
TLD_TO_COUNTRY = {
    ".uk": "GB",
    ".co.uk": "GB",
    ".de": "DE",
    ".fr": "FR",
    ".it": "IT",
    ".es": "ES",
    ".nl": "NL",
    ".be": "BE",
    ".se": "SE",
    ".no": "NO",
    ".dk": "DK",
    ".pl": "PL",
    ".ua": "UA",
    ".ru": "RU",
    ".cn": "CN",
    ".hk": "HK",
    ".jp": "JP",
    ".kr": "KR",
    ".in": "IN",
    ".br": "BR",
    ".mx": "MX",
    ".au": "AU",
    ".nz": "NZ",
    ".ca": "CA",
    ".za": "ZA",
    ".ng": "NG",
    ".ke": "KE",
    ".th": "TH",
    ".vn": "VN",
    ".id": "ID",
    ".my": "MY",
    ".sg": "SG",
    ".ph": "PH",
    ".ir": "IR",
    ".sa": "SA",
    ".ae": "AE",
    ".il": "IL",
    ".ps": "PS",
    ".sy": "SY",
    ".iq": "IQ",
    ".eg": "EG",
    ".tr": "TR",
}


class GeographicExtractor:
    """Extracts geographic location from article content."""

    @staticmethod
    def extract_country(
        title: str, body: str, url: str = "", existing_country: Optional[str] = None
    ) -> Optional[str]:
        """Extract country code from article content.

        Args:
            title: Article title
            body: Article body
            url: Article URL (optional)
            existing_country: Pre-extracted country code (takes precedence)

        Returns:
            Country code (ISO 3166-1 alpha-2) or None
        """
        try:
            # If country already extracted, use it
            if existing_country and len(existing_country) == 2:
                return existing_country.upper()

            # Try to extract from content
            combined_text = f"{title} {body}".lower()

            # Search for country mentions in content (prioritize title)
            title_lower = title.lower()
            for country_code, pattern in COUNTRY_PATTERNS.items():
                if re.search(pattern, title_lower, re.IGNORECASE):
                    return country_code

            # Then search in body
            for country_code, pattern in COUNTRY_PATTERNS.items():
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return country_code

            # Try to extract from URL TLD
            if url:
                country_from_url = GeographicExtractor._extract_from_url(url)
                if country_from_url:
                    return country_from_url

            return None

        except Exception as e:
            logger.error(f"Country extraction error: {e}")
            return None

    @staticmethod
    def _extract_from_url(url: str) -> Optional[str]:
        """Extract country from URL TLD.

        Args:
            url: Article URL

        Returns:
            Country code or None
        """
        try:
            url_lower = url.lower()

            # Check for specific TLDs
            for tld, country_code in TLD_TO_COUNTRY.items():
                if tld in url_lower:
                    return country_code

            return None

        except Exception as e:
            logger.error(f"URL country extraction error: {e}")
            return None

    @staticmethod
    def extract_region(country_code: Optional[str] = None) -> Optional[str]:
        """Extract region from country code.

        Args:
            country_code: ISO 3166-1 alpha-2 country code

        Returns:
            Region code (e.g., "EU", "APAC", "LATAM", "EMEA", "MENA") or None
        """
        if not country_code:
            return None

        # Region mapping
        region_map = {
            # Europe
            "GB": "EU",
            "DE": "EU",
            "FR": "EU",
            "IT": "EU",
            "ES": "EU",
            "NL": "EU",
            "BE": "EU",
            "SE": "EU",
            "NO": "EU",
            "DK": "EU",
            "PL": "EU",
            "UA": "EMEA",
            "RU": "EMEA",
            # Asia-Pacific
            "CN": "APAC",
            "JP": "APAC",
            "KR": "APAC",
            "IN": "APAC",
            "TH": "APAC",
            "VN": "APAC",
            "ID": "APAC",
            "MY": "APAC",
            "SG": "APAC",
            "PH": "APAC",
            "AU": "APAC",
            "NZ": "APAC",
            "HK": "APAC",
            # Americas
            "US": "AMERICAS",
            "CA": "AMERICAS",
            "MX": "LATAM",
            "BR": "LATAM",
            # Middle East & North Africa
            "IR": "MENA",
            "SA": "MENA",
            "AE": "MENA",
            "IL": "MENA",
            "PS": "MENA",
            "SY": "MENA",
            "IQ": "MENA",
            "EG": "MENA",
            "TR": "MENA",
            # Africa
            "ZA": "AFRICA",
            "NG": "AFRICA",
            "KE": "AFRICA",
        }

        return region_map.get(country_code)


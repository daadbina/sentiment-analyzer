"""Extract countries from NER entities."""

import logging
from typing import List, Dict, Set, Optional
from collections import Counter

logger = logging.getLogger(__name__)


# Comprehensive country name to ISO code mapping
COUNTRY_MAPPINGS = {
    # Major countries
    "United States": "US", "USA": "US", "America": "US", "U.S.": "US", "United States of America": "US",
    "China": "CN", "Chinese": "CN", "PRC": "CN", "People's Republic of China": "CN",
    "Russia": "RU", "Russian": "RU", "Russian Federation": "RU",
    "United Kingdom": "GB", "UK": "GB", "Britain": "GB", "England": "GB", "Great Britain": "GB",
    "India": "IN", "Indian": "IN",
    "Germany": "DE", "German": "DE", "Deutschland": "DE",
    "France": "FR", "French": "FR",
    "Japan": "JP", "Japanese": "JP",
    "Brazil": "BR", "Brazilian": "BR", "Brasil": "BR",
    "Canada": "CA", "Canadian": "CA",
    "Australia": "AU", "Australian": "AU",
    "South Korea": "KR", "Korea": "KR", "Korean": "KR", "Republic of Korea": "KR",
    "Italy": "IT", "Italian": "IT", "Italia": "IT",
    "Spain": "ES", "Spanish": "ES", "España": "ES",
    "Mexico": "MX", "Mexican": "MX", "México": "MX",
    
    # Middle East
    "Iran": "IR", "Iranian": "IR", "Persia": "IR",
    "Iraq": "IQ", "Iraqi": "IQ",
    "Israel": "IL", "Israeli": "IL",
    "Saudi Arabia": "SA", "Saudi": "SA",
    "Turkey": "TR", "Turkish": "TR", "Türkiye": "TR",
    "Syria": "SY", "Syrian": "SY",
    "Lebanon": "LB", "Lebanese": "LB",
    "Jordan": "JO", "Jordanian": "JO",
    "Egypt": "EG", "Egyptian": "EG",
    "UAE": "AE", "United Arab Emirates": "AE",
    "Qatar": "QA", "Qatari": "QA",
    "Kuwait": "KW", "Kuwaiti": "KW",
    
    # Europe
    "Poland": "PL", "Polish": "PL", "Polska": "PL",
    "Ukraine": "UA", "Ukrainian": "UA",
    "Netherlands": "NL", "Dutch": "NL", "Holland": "NL",
    "Belgium": "BE", "Belgian": "BE",
    "Sweden": "SE", "Swedish": "SE", "Sverige": "SE",
    "Norway": "NO", "Norwegian": "NO", "Norge": "NO",
    "Denmark": "DK", "Danish": "DK", "Danmark": "DK",
    "Finland": "FI", "Finnish": "FI", "Suomi": "FI",
    "Switzerland": "CH", "Swiss": "CH", "Schweiz": "CH",
    "Austria": "AT", "Austrian": "AT", "Österreich": "AT",
    "Greece": "GR", "Greek": "GR", "Hellas": "GR",
    "Portugal": "PT", "Portuguese": "PT",
    "Czech Republic": "CZ", "Czech": "CZ", "Czechia": "CZ",
    "Romania": "RO", "Romanian": "RO", "România": "RO",
    "Hungary": "HU", "Hungarian": "HU", "Magyarország": "HU",
    
    # Asia-Pacific
    "Indonesia": "ID", "Indonesian": "ID",
    "Thailand": "TH", "Thai": "TH",
    "Vietnam": "VN", "Vietnamese": "VN",
    "Philippines": "PH", "Philippine": "PH", "Filipino": "PH",
    "Malaysia": "MY", "Malaysian": "MY",
    "Singapore": "SG", "Singaporean": "SG",
    "Pakistan": "PK", "Pakistani": "PK",
    "Bangladesh": "BD", "Bangladeshi": "BD",
    "Afghanistan": "AF", "Afghan": "AF",
    "Myanmar": "MM", "Burmese": "MM", "Burma": "MM",
    "Taiwan": "TW", "Taiwanese": "TW",
    "Hong Kong": "HK",
    "New Zealand": "NZ", "Kiwi": "NZ",
    
    # Africa
    "South Africa": "ZA", "South African": "ZA",
    "Nigeria": "NG", "Nigerian": "NG",
    "Kenya": "KE", "Kenyan": "KE",
    "Ethiopia": "ET", "Ethiopian": "ET",
    "Ghana": "GH", "Ghanaian": "GH",
    "Tanzania": "TZ", "Tanzanian": "TZ",
    "Uganda": "UG", "Ugandan": "UG",
    "Algeria": "DZ", "Algerian": "DZ",
    "Morocco": "MA", "Moroccan": "MA",
    "Libya": "LY", "Libyan": "LY",
    "Tunisia": "TN", "Tunisian": "TN",
    "Sudan": "SD", "Sudanese": "SD",
    "Somalia": "SO", "Somali": "SO",
    
    # Latin America
    "Argentina": "AR", "Argentine": "AR", "Argentinian": "AR",
    "Chile": "CL", "Chilean": "CL",
    "Colombia": "CO", "Colombian": "CO",
    "Venezuela": "VE", "Venezuelan": "VE",
    "Peru": "PE", "Peruvian": "PE",
    "Ecuador": "EC", "Ecuadorian": "EC",
    "Bolivia": "BO", "Bolivian": "BO",
    "Cuba": "CU", "Cuban": "CU",
    "Dominican Republic": "DO", "Dominican": "DO",
    "Puerto Rico": "PR", "Puerto Rican": "PR",
    
    # Other
    "North Korea": "KP", "DPRK": "KP", "Democratic People's Republic of Korea": "KP",
    "Yemen": "YE", "Yemeni": "YE",
    "Palestine": "PS", "Palestinian": "PS",
    "Kosovo": "XK", "Kosovar": "XK",
    "Serbia": "RS", "Serbian": "RS",
    "Croatia": "HR", "Croatian": "HR",
    "Bosnia": "BA", "Bosnian": "BA", "Bosnia and Herzegovina": "BA",
}


class CountryExtractor:
    """Extract countries from NER entities."""

    @staticmethod
    def extract_countries_from_entities(entities: List[Dict]) -> List[str]:
        """
        Extract unique country codes from entity list.

        Args:
            entities: List of entity dictionaries from NER service
                     Each entity has: text, entity_type, country (optional), etc.

        Returns:
            List of unique ISO country codes (e.g., ["US", "CN", "RU"])
        """
        if not entities:
            return []

        countries = set()

        for entity in entities:
            entity_type = entity.get("entity_type", "")
            entity_text = entity.get("text", "").strip()
            entity_country = entity.get("country")  # Some entities have country field

            # Method 1: Use entity's country field if available
            if entity_country:
                countries.add(entity_country)
                logger.debug(f"Extracted country from entity field: {entity_country}")
                continue

            # Method 2: Extract from LOCATION or GPE entity types
            if entity_type in ["LOCATION", "GPE"] and entity_text:
                # Try exact match first
                country_code = COUNTRY_MAPPINGS.get(entity_text)
                
                if country_code:
                    countries.add(country_code)
                    logger.debug(f"Extracted country from entity text: {entity_text} -> {country_code}")
                else:
                    # Try case-insensitive partial match
                    entity_text_lower = entity_text.lower()
                    for country_name, code in COUNTRY_MAPPINGS.items():
                        if country_name.lower() in entity_text_lower or entity_text_lower in country_name.lower():
                            countries.add(code)
                            logger.debug(f"Extracted country from partial match: {entity_text} -> {code}")
                            break

        result = sorted(list(countries))
        logger.info(f"Extracted {len(result)} countries from {len(entities)} entities: {result}")
        return result


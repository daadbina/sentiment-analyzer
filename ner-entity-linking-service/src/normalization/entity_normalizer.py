"""Entity text normalization."""

import logging
import re
import unicodedata
from typing import List, Tuple
from unidecode import unidecode

logger = logging.getLogger(__name__)


class EntityNormalizer:
    """Normalizes entity text for linking and deduplication."""

    # Common abbreviations to expand
    ABBREVIATIONS = {
        "dr.": "doctor",
        "mr.": "mister",
        "mrs.": "misses",
        "ms.": "miss",
        "prof.": "professor",
        "inc.": "incorporated",
        "ltd.": "limited",
        "corp.": "corporation",
        "co.": "company",
        "u.s.": "united states",
        "u.k.": "united kingdom",
        "u.n.": "united nations",
    }

    @staticmethod
    def normalize(text: str, language: str = "en") -> str:
        """
        Normalize entity text.

        Args:
            text: Entity text to normalize
            language: Language code

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Convert to NFC form for consistent character representation
        text = unicodedata.normalize("NFC", text)

        # Convert to lowercase
        text = text.lower()

        # Remove diacritics and accents
        text = unidecode(text)

        # Expand common abbreviations
        for abbr, expansion in EntityNormalizer.ABBREVIATIONS.items():
            text = re.sub(r"\b" + re.escape(abbr) + r"\b", expansion, text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Remove control characters
        text = "".join(char for char in text if unicodedata.category(char)[0] != "C")

        return text

    @staticmethod
    def extract_aliases(text: str) -> List[str]:
        """
        Extract aliases from entity text.

        Args:
            text: Entity text (e.g., "United States (USA)")

        Returns:
            List of aliases
        """
        aliases = []

        # Extract parenthetical aliases
        matches = re.findall(r"\(([^)]+)\)", text)
        for match in matches:
            alias = match.strip()
            if alias and len(alias) > 1:
                aliases.append(alias)

        # Extract acronyms (consecutive capital letters)
        acronyms = re.findall(r"\b([A-Z]{2,})\b", text)
        for acronym in acronyms:
            if acronym not in aliases:
                aliases.append(acronym)

        return aliases

    @staticmethod
    def normalize_type(entity_type: str) -> str:
        """
        Normalize entity type to canonical form.

        Args:
            entity_type: Entity type from NER model

        Returns:
            Canonical entity type
        """
        type_mapping = {
            "PER": "PERSON",
            "PERSON": "PERSON",
            "ORG": "ORGANIZATION",
            "ORGANIZATION": "ORGANIZATION",
            "LOC": "LOCATION",
            "LOCATION": "LOCATION",
            "GPE": "GPE",
            "MONEY": "CURRENCY",
            "CURRENCY": "CURRENCY",
            "DATE": "DATE",
            "EVENT": "EVENT",
        }

        normalized = type_mapping.get(entity_type.upper(), entity_type)
        return normalized

    @staticmethod
    def is_valid_entity(text: str, min_length: int = 2) -> bool:
        """
        Check if text is valid entity.

        Args:
            text: Entity text
            min_length: Minimum entity length

        Returns:
            True if valid entity
        """
        if not text or len(text) < min_length:
            return False

        # Reject pure numbers
        if text.isdigit():
            return False

        # Reject pure punctuation
        if all(not c.isalnum() for c in text):
            return False

        return True


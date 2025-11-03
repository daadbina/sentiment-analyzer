"""
Base parser class for article extraction.

Defines the abstract interface for all parser implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ParsedArticle:
    """
    Represents a parsed article with extracted content.

    Attributes:
        title: Article headline.
        body: Article main content.
        url: Original article URL.
        canonical_url: Canonical/normalized URL.
        published_at: Publication timestamp (ISO-8601, UTC).
        author: Article author name.
        source: Source/publication name.
        language: Detected language code (ISO 639-1).
        raw_html: Original HTML content.
        extraction_method: Parser type used (rss, html, etc.).
    """

    title: str
    body: str
    url: str
    canonical_url: str
    published_at: datetime
    author: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    raw_html: Optional[str] = None
    extraction_method: str = "unknown"
    article_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate parsed article data."""
        if not self.title or not self.title.strip():
            raise ValueError("Article title cannot be empty")
        if not self.body or not self.body.strip():
            raise ValueError("Article body cannot be empty")
        if not self.url or not self.url.strip():
            raise ValueError("Article URL cannot be empty")
        if not self.canonical_url or not self.canonical_url.strip():
            raise ValueError("Article canonical_url cannot be empty")


class BaseParser(ABC):
    """
    Abstract base class for article parsers.

    Defines the interface that all parser implementations must follow.
    Supports both RSS feed parsing and HTML content extraction.
    """

    def __init__(self, source_name: str) -> None:
        """
        Initialize parser.

        Args:
            source_name: Name of the news source being parsed.
        """
        self.source_name = source_name

    @abstractmethod
    async def parse(self, content: str, url: str) -> ParsedArticle:
        """
        Parse article content and extract structured data.

        Args:
            content: Raw content to parse (HTML or XML).
            url: Source URL for context and canonical URL resolution.

        Returns:
            ParsedArticle: Extracted article data.

        Raises:
            ParseError: If parsing fails or required fields are missing.
        """
        pass

    @abstractmethod
    def supports_format(self, content_type: str) -> bool:
        """
        Check if parser supports the given content type.

        Args:
            content_type: MIME type or format identifier.

        Returns:
            bool: True if parser can handle this format.
        """
        pass

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for canonical form.

        Removes fragments, query parameters, and trailing slashes.

        Args:
            url: URL to normalize.

        Returns:
            str: Normalized URL.
        """
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        # Remove fragment and query parameters
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        # Remove trailing slash
        if normalized.endswith("/"):
            normalized = normalized[:-1]
        return normalized

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.

        Removes extra whitespace, control characters, and normalizes line breaks.

        Args:
            text: Text to clean.

        Returns:
            str: Cleaned text.
        """
        if not text:
            return ""

        # Remove control characters except newlines and tabs
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")

        # Normalize whitespace
        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]  # Remove empty lines
        return "\n".join(lines)

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: URL to extract domain from.

        Returns:
            str: Domain name.
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain

"""
HTML article parser implementation.

Extracts articles from HTML pages using newspaper3k and readability-lxml.
"""

from datetime import datetime
from typing import Optional
import newspaper
from readability import Document

from .base import BaseParser, ParsedArticle
from ..exceptions import ParseError


class HTMLParser(BaseParser):
    """
    Parser for HTML article pages.

    Uses newspaper3k for article extraction with fallback to readability-lxml.
    """

    def __init__(self, source_name: str) -> None:
        """
        Initialize HTML parser.

        Args:
            source_name: Name of the news source.
        """
        super().__init__(source_name)
        self.extraction_method = "html"

    async def parse(self, content: str, url: str) -> list:
        """
        Parse HTML page and extract article data.

        Args:
            content: HTML page content.
            url: Article URL for context.

        Returns:
            list[ParsedArticle]: List of extracted articles (usually 1 for HTML).

        Raises:
            ParseError: If parsing fails or required fields are missing.
        """
        try:
            # Try newspaper3k first
            article = self._parse_with_newspaper(content, url)

            if article:
                return [article]

            # Fallback to readability
            article = self._parse_with_readability(content, url)

            if article:
                return [article]

            raise ParseError(
                "Failed to extract article from HTML",
                parser_type="html",
                error_code="HTML_EXTRACTION_FAILED",
            )

        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                f"Failed to parse HTML: {str(e)}",
                parser_type="html",
                error_code="HTML_PARSE_FAILED",
            )

    def supports_format(self, content_type: str) -> bool:
        """
        Check if parser supports HTML formats.

        Args:
            content_type: MIME type or format identifier.

        Returns:
            bool: True if content type is HTML.
        """
        html_types = {"text/html", "application/xhtml+xml"}
        return content_type.lower() in html_types

    def _parse_with_newspaper(self, content: str, url: str) -> Optional[ParsedArticle]:
        """
        Parse HTML using newspaper3k library.

        Args:
            content: HTML content.
            url: Article URL.

        Returns:
            ParsedArticle or None if extraction fails.
        """
        try:
            article = newspaper.Article(url)
            article.set_html(content)
            article.parse()

            title = article.title or ""
            body = article.text or ""

            if not title or not body:
                return None

            published_at = article.publish_date or datetime.utcnow()

            canonical_url = self._normalize_url(url)

            return ParsedArticle(
                title=title,
                body=self._clean_text(body),
                url=url,
                canonical_url=canonical_url,
                published_at=published_at,
                author=article.authors[0] if article.authors else None,
                source=self.source_name,
                raw_html=content,
                extraction_method=self.extraction_method,
            )

        except Exception:
            return None

    def _parse_with_readability(
        self, content: str, url: str
    ) -> Optional[ParsedArticle]:
        """
        Parse HTML using readability-lxml library.

        Args:
            content: HTML content.
            url: Article URL.

        Returns:
            ParsedArticle or None if extraction fails.
        """
        try:
            doc = Document(content)

            title = doc.short_title() or ""
            body = doc.summary() or ""

            if not title or not body:
                return None

            # Extract text from HTML
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(body, "html.parser")
            text = soup.get_text()

            if not text.strip():
                return None

            canonical_url = self._normalize_url(url)

            return ParsedArticle(
                title=title,
                body=self._clean_text(text),
                url=url,
                canonical_url=canonical_url,
                published_at=datetime.utcnow(),
                source=self.source_name,
                raw_html=content,
                extraction_method=self.extraction_method,
            )

        except Exception:
            return None

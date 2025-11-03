"""
RSS feed parser implementation.

Extracts articles from RSS/Atom feeds using feedparser library.
"""

import logging
from datetime import datetime
import feedparser
from dateutil import parser as date_parser

from .base import BaseParser, ParsedArticle
from ..exceptions import ParseError

logger = logging.getLogger(__name__)


class RSSParser(BaseParser):
    """
    Parser for RSS and Atom feeds.

    Handles RSS 2.0, Atom 1.0, and other common feed formats.
    """

    def __init__(self, source_name: str) -> None:
        """
        Initialize RSS parser.

        Args:
            source_name: Name of the news source.
        """
        super().__init__(source_name)
        self.extraction_method = "rss"

    async def parse(self, content: str, url: str) -> list:
        """
        Parse RSS feed and extract all articles.

        Args:
            content: RSS/Atom feed XML content.
            url: Feed URL for context.

        Returns:
            list[ParsedArticle]: List of extracted articles.

        Raises:
            ParseError: If parsing fails or no entries found.
        """
        try:
            feed = feedparser.parse(content)

            if not feed.entries:
                raise ParseError(
                    "No entries found in feed",
                    parser_type="rss",
                    error_code="RSS_NO_ENTRIES",
                )

            articles = []
            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry, content)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse entry: {str(e)}")
                    continue

            if not articles:
                raise ParseError(
                    "No valid articles found in feed",
                    parser_type="rss",
                    error_code="RSS_NO_VALID_ARTICLES",
                )

            return articles

        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                f"Failed to parse RSS feed: {str(e)}",
                parser_type="rss",
                error_code="RSS_PARSE_FAILED",
            )

    def _parse_entry(self, entry: dict, content: str) -> ParsedArticle:
        """
        Parse a single RSS entry.

        Args:
            entry: RSS entry dictionary.
            content: Original feed content.

        Returns:
            ParsedArticle: Extracted article data or None if invalid.
        """
        try:
            # Extract title
            title = entry.get("title", "")
            if isinstance(title, str):
                title = title.strip()
            else:
                title = str(title).strip()
            if not title:
                return None

            # Extract content/description
            body = self._extract_body(entry)
            if not body:
                return None

            # Extract URL
            article_url = entry.get("link", "")
            if isinstance(article_url, str):
                article_url = article_url.strip()
            else:
                article_url = str(article_url).strip()
            if not article_url:
                return None

            # Extract publication date
            published_at = self._extract_published_date(entry)

            # Extract author
            author = entry.get("author", "")
            if isinstance(author, str):
                author = author.strip() or None
            else:
                author = str(author).strip() or None

            # Normalize URLs
            canonical_url = self._normalize_url(article_url)

            return ParsedArticle(
                title=title,
                body=body,
                url=article_url,
                canonical_url=canonical_url,
                published_at=published_at,
                author=author,
                source=self.source_name,
                raw_html=content,
                extraction_method=self.extraction_method,
            )
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            raise

    def supports_format(self, content_type: str) -> bool:
        """
        Check if parser supports RSS/Atom formats.

        Args:
            content_type: MIME type or format identifier.

        Returns:
            bool: True if content type is RSS/Atom.
        """
        rss_types = {
            "application/rss+xml",
            "application/atom+xml",
            "text/xml",
            "application/xml",
        }
        return content_type.lower() in rss_types

    def _extract_body(self, entry: dict) -> str:
        """
        Extract article body from RSS entry.

        Tries multiple fields in order of preference.

        Args:
            entry: RSS entry dictionary.

        Returns:
            str: Article body content.
        """
        # Try content field first (Atom)
        if "content" in entry and entry["content"]:
            try:
                content_list = entry["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    content_item = content_list[0]
                    if isinstance(content_item, dict):
                        content = content_item.get("value", "")
                        if isinstance(content, str) and content:
                            return self._clean_text(content)
            except Exception as e:
                logger.debug(f"Failed to extract content field: {e}")

        # Try summary field
        if "summary" in entry:
            try:
                summary = entry["summary"]
                if isinstance(summary, str):
                    summary = summary.strip()
                    if summary:
                        return self._clean_text(summary)
            except Exception as e:
                logger.debug(f"Failed to extract summary field: {e}")

        # Try description field (RSS)
        if "description" in entry:
            try:
                description = entry["description"]
                if isinstance(description, str):
                    description = description.strip()
                    if description:
                        return self._clean_text(description)
            except Exception as e:
                logger.debug(f"Failed to extract description field: {e}")

        return ""

    def _extract_published_date(self, entry: dict) -> datetime:
        """
        Extract publication date from RSS entry.

        Tries multiple date fields and formats.

        Args:
            entry: RSS entry dictionary.

        Returns:
            datetime: Publication timestamp in UTC.

        Raises:
            ParseError: If no valid date found.
        """
        date_fields = [
            "published_parsed",
            "updated_parsed",
            "created_parsed",
            "published",
            "updated",
            "created",
        ]

        for field in date_fields:
            if field in entry and entry[field]:
                try:
                    value = entry[field]

                    # Handle time.struct_time from feedparser
                    if hasattr(value, "tm_year"):
                        return datetime(
                            value.tm_year,
                            value.tm_mon,
                            value.tm_mday,
                            value.tm_hour,
                            value.tm_min,
                            value.tm_sec,
                        )

                    # Handle string dates
                    if isinstance(value, str):
                        return date_parser.isoparse(value)

                    # Handle datetime objects
                    if isinstance(value, datetime):
                        return value

                except Exception as e:  # nosec B112
                    logger.debug(f"Failed to parse date from field {field}: {e}")
                    continue

        # Fallback to current time if no date found
        return datetime.utcnow()

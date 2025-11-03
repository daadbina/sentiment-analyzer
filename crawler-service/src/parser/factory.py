"""
Parser factory for creating appropriate parser instances.

Implements Factory pattern to select parser based on content type.
"""

from typing import Optional

from .base import BaseParser
from .rss_parser import RSSParser
from .html_parser import HTMLParser
from ..exceptions import ParseError


class ParserFactory:
    """
    Factory for creating parser instances.

    Selects appropriate parser based on content type and source format.
    """

    _parsers = {
        "rss": RSSParser,
        "html": HTMLParser,
    }

    @classmethod
    def create(cls, content_type: str, source_name: str) -> BaseParser:
        """
        Create parser instance for given content type.

        Args:
            content_type: Content type (rss, html, etc.).
            source_name: Name of the news source.

        Returns:
            BaseParser: Appropriate parser instance.

        Raises:
            ParseError: If content type is not supported.
        """
        return cls.create_parser(source_name, content_type)

    @classmethod
    def create_parser(cls, source_name: str, content_type: str = "html") -> BaseParser:
        """
        Create parser instance for given content type.

        Args:
            source_name: Name of the news source.
            content_type: Content type (rss, html, etc.).

        Returns:
            BaseParser: Appropriate parser instance.

        Raises:
            ParseError: If content type is not supported.
        """
        parser_class = cls._parsers.get(content_type.lower())

        if not parser_class:
            raise ParseError(
                f"Unsupported content type: {content_type}",
                parser_type=content_type,
                error_code="UNSUPPORTED_CONTENT_TYPE",
            )

        return parser_class(source_name)

    @classmethod
    def detect_parser(cls, source_name: str, content_type: str) -> Optional[BaseParser]:
        """
        Detect and create appropriate parser based on content type.

        Tries to find a parser that supports the given content type.

        Args:
            source_name: Name of the news source.
            content_type: MIME type or format identifier.

        Returns:
            BaseParser: Parser instance if found, None otherwise.
        """
        for parser_class in cls._parsers.values():
            parser = parser_class(source_name)
            if parser.supports_format(content_type):
                return parser

        return None

    @classmethod
    def register_parser(cls, name: str, parser_class: type) -> None:
        """
        Register custom parser implementation.

        Allows extending parser factory with new parser types.

        Args:
            name: Parser identifier.
            parser_class: Parser class (must inherit from BaseParser).

        Raises:
            ValueError: If parser_class doesn't inherit from BaseParser.
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(
                f"Parser class must inherit from BaseParser, got {parser_class}"
            )

        cls._parsers[name.lower()] = parser_class

    @classmethod
    def get_available_parsers(cls) -> list[str]:
        """
        Get list of available parser types.

        Returns:
            list[str]: List of registered parser names.
        """
        return list(cls._parsers.keys())

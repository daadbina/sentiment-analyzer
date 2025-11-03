"""
Parser module for extracting article metadata from various feed formats.

Implements Factory pattern for dynamic parser selection based on source type.
"""

from .base import BaseParser, ParsedArticle
from .rss_parser import RSSParser
from .html_parser import HTMLParser
from .factory import ParserFactory

__all__ = [
    "BaseParser",
    "ParsedArticle",
    "RSSParser",
    "HTMLParser",
    "ParserFactory",
]

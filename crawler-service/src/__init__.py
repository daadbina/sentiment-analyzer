"""
Crawler Service - Multilingual news article crawler for sentiment-analyzer-v2.

This package implements a production-grade microservice for collecting news articles
from diverse RSS feeds and HTML sources, normalizing content, and publishing to Kafka.
"""

__version__ = "1.0.0"
__author__ = "Sentiment Analyzer Team"

from .config import CrawlerSettings, get_settings, get_config_dict
from .exceptions import (
    CrawlerException,
    FetchError,
    ParseError,
    ValidationError,
    PublishError,
    ConfigError,
    SchemaError,
    CircuitBreakerOpenError,
    LanguageDetectionError,
    DuplicateArticleError,
)
from .fetcher import HTTPFetcher, CircuitBreaker
from .parser import BaseParser, ParsedArticle, ParserFactory
from .utils import ChecksumEngine, LanguageDetector, TimestampUtils

__all__ = [
    "CrawlerSettings",
    "get_settings",
    "get_config_dict",
    "CrawlerException",
    "FetchError",
    "ParseError",
    "ValidationError",
    "PublishError",
    "ConfigError",
    "SchemaError",
    "CircuitBreakerOpenError",
    "LanguageDetectionError",
    "DuplicateArticleError",
    "HTTPFetcher",
    "CircuitBreaker",
    "BaseParser",
    "ParsedArticle",
    "ParserFactory",
    "ChecksumEngine",
    "LanguageDetector",
    "TimestampUtils",
]

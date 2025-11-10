"""
Training data fetcher for GitHub news datasets.

Downloads and parses training datasets from Webhose free-news-datasets repository.
"""

import asyncio
import logging
import json
import zipfile
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
import hashlib

from .models import NewsRawMessage
from .config import get_settings
from .utils import TimestampUtils
from .exceptions import FetchError

logger = logging.getLogger(__name__)


class TrainingDataFetcher:
    """
    Fetcher for training data from GitHub repository.
    
    Downloads ZIP files containing labeled news articles and converts them
    to NewsRawMessage format for training purposes.
    """
    
    # GitHub raw content base URL
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Webhose/free-news-datasets/master/News_Datasets"
    
    # Available categories and sentiments
    CATEGORIES = [
        "Arts, Culture, and Entertainment",
        "Crime, Law and Justice",
        "Disaster and Accident",
        "Economy, Business and Finance",
        "Education",
        "Environment",
        "Health",
        "Human Interest",
        "Labor",
        "Lifestyle and Leisure",
        "Politics",
        "Religion and Belief",
        "Science and Technology",
        "Social Issue",
        "Sport",
        "War, Conflict and Unrest",
        "Weather",
    ]
    
    SENTIMENTS = ["positive", "negative"]
    
    def __init__(self):
        """Initialize training data fetcher."""
        self.settings = get_settings()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self) -> None:
        """Start HTTP session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes for large files
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Training data fetcher session started")
    
    async def stop(self) -> None:
        """Stop HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Training data fetcher session stopped")
    
    async def fetch_available_datasets(self) -> List[Dict[str, str]]:
        """
        Fetch list of available datasets from GitHub.
        
        Returns:
            List of dataset metadata dicts with category, sentiment, filename.
        """
        # For now, we'll construct dataset names based on known patterns
        # In production, you might want to scrape the GitHub page or use GitHub API
        datasets = []
        
        # Note: GitHub repo has files with timestamps in names
        # We'll need to discover actual filenames or maintain a list
        # For this implementation, we'll use a sample approach
        
        logger.info("Discovering available training datasets")
        
        # Sample datasets (you can expand this list based on actual GitHub content)
        sample_datasets = [
            {"category": "War, Conflict and Unrest", "sentiment": "negative", 
             "filename": "War, Conflict and Unrest_negative_20240128093740.zip"},
            {"category": "War, Conflict and Unrest", "sentiment": "positive",
             "filename": "War, Conflict and Unrest_positive_20240128131846.zip"},
            {"category": "Politics", "sentiment": "negative",
             "filename": "Politics_negative_20240128132206.zip"},
            {"category": "Politics", "sentiment": "positive",
             "filename": "Politics_positive_20240811070033.zip"},
            {"category": "Health", "sentiment": "negative",
             "filename": "Health_negative_20240128131616.zip"},
            {"category": "Health", "sentiment": "positive",
             "filename": "Health_positive_20240505070030.zip"},
            {"category": "Environment", "sentiment": "positive",
             "filename": "Environment_positive_20240317070020.zip"},
            {"category": "Sport", "sentiment": "negative",
             "filename": "Sport_negative_20240128131809.zip"},
        ]
        
        return sample_datasets
    
    async def download_dataset(self, filename: str) -> bytes:
        """
        Download a dataset ZIP file from GitHub.
        
        Args:
            filename: Name of the ZIP file to download.
            
        Returns:
            bytes: ZIP file content.
            
        Raises:
            FetchError: If download fails.
        """
        url = f"{self.GITHUB_RAW_BASE}/{filename}"
        
        logger.info(f"Downloading training dataset: {filename}")
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    logger.info(f"Downloaded {len(content)} bytes from {filename}")
                    return content
                else:
                    raise FetchError(
                        f"Failed to download {filename}: HTTP {response.status}",
                        url=url,
                        status_code=response.status,
                    )
        except aiohttp.ClientError as e:
            raise FetchError(
                f"Network error downloading {filename}: {str(e)}",
                url=url,
            )
    
    def extract_articles_from_zip(self, zip_content: bytes) -> List[Dict[str, Any]]:
        """
        Extract articles from ZIP file.
        
        Args:
            zip_content: ZIP file content as bytes.
            
        Returns:
            List of article dictionaries.
        """
        articles = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                for filename in zf.namelist():
                    if filename.endswith('.json'):
                        with zf.open(filename) as f:
                            content = f.read()
                            article = json.loads(content)
                            articles.append(article)
            
            logger.info(f"Extracted {len(articles)} articles from ZIP")
            return articles
            
        except (zipfile.BadZipFile, json.JSONDecodeError) as e:
            logger.error(f"Error extracting articles from ZIP: {str(e)}")
            return []
    
    def convert_to_news_raw_message(
        self,
        article: Dict[str, Any],
        category: str,
        sentiment: str,
        job_id: str,
    ) -> Optional[NewsRawMessage]:
        """
        Convert training article to NewsRawMessage format.
        
        Args:
            article: Article dictionary from training dataset.
            category: Article category.
            sentiment: Article sentiment (positive/negative).
            job_id: Crawl job identifier.
            
        Returns:
            NewsRawMessage or None if conversion fails.
        """
        try:
            # Extract fields from training data format
            # Webhose format typically has: title, text, url, published, language, etc.
            title = article.get('title', '')
            body = article.get('text', '')
            url = article.get('url', '')
            # Use fixed source for all training data (not the original article source)
            source = 'webhose_free_datasets'
            # Store original source in metadata for reference
            original_source = article.get('thread', {}).get('site', 'unknown')
            language = article.get('language', 'en')
            published_at = article.get('published', '')
            author = article.get('author', None)
            
            # Validate required fields
            if not title or not body or not url:
                logger.warning(f"Skipping article with missing required fields: {url}")
                return None
            
            # Parse and normalize timestamp
            try:
                if published_at:
                    # Webhose format: "2024-01-15T10:30:00.000+00:00"
                    dt = datetime.fromisoformat(published_at.replace('+00:00', '+00:00'))
                    published_at_iso = TimestampUtils.to_iso8601(dt)
                else:
                    published_at_iso = TimestampUtils.to_iso8601(TimestampUtils.now_utc())
            except Exception as e:
                logger.warning(f"Error parsing timestamp: {e}, using current time")
                published_at_iso = TimestampUtils.to_iso8601(TimestampUtils.now_utc())
            
            # Generate checksum
            checksum = hashlib.sha256(body.encode('utf-8')).hexdigest()
            
            # Create message with training data metadata
            message = NewsRawMessage(
                canonical_url=url,
                title=title,
                body=body,
                url=url,
                source=source,
                language=language[:2].lower() if language else 'en',
                published_at=published_at_iso,
                crawled_at=TimestampUtils.to_iso8601(TimestampUtils.now_utc()),
                country=None,  # Training data may not have country
                checksum=checksum,
                validation_score=1.0,  # Training data is pre-validated
                schema_version=self.settings.schema_version,
                ingest_job_id=job_id,
                publisher_id="training_data",
                author=author,
                raw_html=None,
                extraction_method="training_data",
                metadata={
                    "is_training_data": "true",  # Flag to skip Neo4j processing
                    "category": category,
                    "sentiment": sentiment,
                    "source": "webhose_free_datasets",
                    "original_source": original_source,
                },
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error converting article to NewsRawMessage: {str(e)}")
            return None
    
    async def fetch_training_data(
        self,
        categories: Optional[List[str]] = None,
        sentiments: Optional[List[str]] = None,
        max_datasets: Optional[int] = None,
        job_id: str = None,
    ) -> List[NewsRawMessage]:
        """
        Fetch training data from GitHub repository.
        
        Args:
            categories: List of categories to fetch (None = all).
            sentiments: List of sentiments to fetch (None = all).
            max_datasets: Maximum number of datasets to fetch (None = all).
            job_id: Crawl job identifier.
            
        Returns:
            List of NewsRawMessage objects.
        """
        if not self.session:
            await self.start()
        
        # Get available datasets
        available_datasets = await self.fetch_available_datasets()
        
        # Filter by categories and sentiments
        if categories:
            available_datasets = [
                d for d in available_datasets if d['category'] in categories
            ]
        if sentiments:
            available_datasets = [
                d for d in available_datasets if d['sentiment'] in sentiments
            ]
        
        # Limit number of datasets
        if max_datasets:
            available_datasets = available_datasets[:max_datasets]
        
        logger.info(f"Fetching {len(available_datasets)} training datasets")
        
        all_messages = []
        
        for dataset in available_datasets:
            try:
                # Download ZIP file
                zip_content = await self.download_dataset(dataset['filename'])
                
                # Extract articles
                articles = self.extract_articles_from_zip(zip_content)
                
                # Convert to NewsRawMessage
                for article in articles:
                    message = self.convert_to_news_raw_message(
                        article=article,
                        category=dataset['category'],
                        sentiment=dataset['sentiment'],
                        job_id=job_id,
                    )
                    if message:
                        all_messages.append(message)
                
                logger.info(
                    f"Processed dataset {dataset['filename']}: "
                    f"{len(articles)} articles, {len(all_messages)} valid messages"
                )
                
            except Exception as e:
                logger.error(f"Error processing dataset {dataset['filename']}: {str(e)}")
                continue
        
        logger.info(f"Total training messages fetched: {len(all_messages)}")
        return all_messages


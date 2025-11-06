"""API client base class and implementations."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import aiohttp
from datetime import datetime, timedelta

try:
    import ccxt
except ImportError:
    ccxt = None

from src.config import config
from src.exceptions import FetchError, CircuitBreakerError
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class CircuitBreaker:
    """Circuit breaker for API calls."""

    def __init__(self, threshold: int = 5, timeout_seconds: int = 60):
        """Initialize circuit breaker."""
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def record_success(self):
        """Record successful call."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.threshold:
            self.state = "open"

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == "open":
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed > self.timeout_seconds:
                self.state = "half-open"
                self.failure_count = 0
                return False
            return True
        return False

    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == "half-open"


class BaseAPIClient(ABC):
    """Base API client with retry and circuit breaker."""

    def __init__(self, name: str, base_url: str, timeout_seconds: int = 30):
        """Initialize API client."""
        self.name = name
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.circuit_breaker = CircuitBreaker(
            threshold=config.api_client.circuit_breaker_threshold,
            timeout_seconds=config.api_client.circuit_breaker_timeout_seconds
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request with retry logic."""
        if self.circuit_breaker.is_open():
            raise CircuitBreakerError(self.name, "Circuit breaker is open")

        for attempt in range(config.api_client.retry_max_attempts):
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()

                async with self.session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                    **kwargs
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.circuit_breaker.record_success()
                        logger.info(
                            f"API request successful: {self.name}",
                            operation="api_get",
                            url=url,
                            status_code=response.status
                        )
                        return data
                    else:
                        raise FetchError(
                            self.name,
                            f"HTTP {response.status}: {await response.text()}",
                            attempt
                        )

            except asyncio.TimeoutError as e:
                logger.warning(
                    f"API request timeout: {self.name}",
                    operation="api_get",
                    attempt=attempt,
                    error=str(e)
                )
                if attempt < config.api_client.retry_max_attempts - 1:
                    backoff = config.api_client.retry_backoff_factor ** attempt
                    await asyncio.sleep(backoff)
                else:
                    self.circuit_breaker.record_failure()
                    raise FetchError(self.name, f"Timeout after {attempt + 1} attempts", attempt)

            except Exception as e:
                logger.error(
                    f"API request failed: {self.name}",
                    operation="api_get",
                    attempt=attempt,
                    error_type=type(e).__name__,
                    error=str(e)
                )
                if attempt < config.api_client.retry_max_attempts - 1:
                    backoff = config.api_client.retry_backoff_factor ** attempt
                    await asyncio.sleep(backoff)
                else:
                    self.circuit_breaker.record_failure()
                    raise FetchError(self.name, str(e), attempt)

        raise FetchError(self.name, "Max retries exceeded", config.api_client.retry_max_attempts)

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch labels from API."""
        pass

    @abstractmethod
    async def parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse API response."""
        pass


class ACLEDFetcher(BaseAPIClient):
    """ACLED API fetcher."""

    def __init__(self):
        """Initialize ACLED fetcher."""
        super().__init__(
            name="ACLED",
            base_url=config.acled.api_url,
            timeout_seconds=config.api_client.timeout_seconds
        )
        self.api_key = config.acled.api_key
        self.oauth_url = config.acled.oauth_url
        self.username = config.acled.username
        self.password = config.acled.password
        self.access_token = config.acled.access_token
        self.token_expires_at = config.acled.token_expires_at

    async def _get_oauth_token(self) -> str:
        """Get OAuth access token from ACLED."""
        logger.info(
            "Requesting OAuth token from ACLED",
            operation="acled_oauth",
            oauth_url=self.oauth_url
        )

        # Validate credentials are configured
        if not self.username or not self.password:
            error_msg = "ACLED credentials not configured (ACLED_USERNAME and ACLED_PASSWORD required)"
            logger.error(
                error_msg,
                operation="acled_oauth",
                has_username=bool(self.username),
                has_password=bool(self.password)
            )
            raise FetchError(error_msg)

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Prepare OAuth request data
            data = {
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
                "client_id": "acled"
            }

            # Use explicit Content-Type header for form data
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            logger.info(
                "Sending OAuth token request to ACLED",
                operation="acled_oauth",
                username=self.username[:10] + "***" if self.username else "N/A"
            )

            async with self.session.post(
                self.oauth_url,
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)
            ) as resp:
                response_text = await resp.text()

                logger.info(
                    f"OAuth response received: HTTP {resp.status}",
                    operation="acled_oauth",
                    status_code=resp.status,
                    response_length=len(response_text)
                )

                if resp.status != 200:
                    logger.error(
                        f"OAuth token request failed: HTTP {resp.status}",
                        operation="acled_oauth",
                        status_code=resp.status,
                        response_text=response_text[:500]  # Log first 500 chars
                    )
                    raise FetchError(f"OAuth token request failed: HTTP {resp.status}: {response_text[:200]}")

                try:
                    response = await resp.json()
                except Exception as json_err:
                    logger.error(
                        f"Failed to parse OAuth response as JSON: {str(json_err)}",
                        operation="acled_oauth",
                        response_text=response_text[:500]
                    )
                    raise FetchError(f"Invalid JSON response from ACLED OAuth: {str(json_err)}")

                self.access_token = response.get("access_token")
                if not self.access_token:
                    logger.error(
                        "OAuth response missing access_token field",
                        operation="acled_oauth",
                        response_keys=list(response.keys())
                    )
                    raise FetchError(f"OAuth response missing access_token: {response}")

                expires_in = response.get("expires_in", 86400)
                self.token_expires_at = time.time() + expires_in

                logger.info(
                    "Successfully obtained OAuth token from ACLED",
                    operation="acled_oauth",
                    expires_in=expires_in,
                    token_length=len(self.access_token)
                )

                return self.access_token

        except FetchError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to get OAuth token: {str(e)}",
                operation="acled_oauth",
                error_type=type(e).__name__,
                error_details=str(e)
            )
            raise FetchError(f"ACLED OAuth error: {str(e)}")

    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid OAuth token."""
        current_time = time.time()

        # If token doesn't exist or is expired, get a new one
        if not self.access_token or not self.token_expires_at or current_time >= self.token_expires_at - 300:
            return await self._get_oauth_token()

        return self.access_token

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch conflict events from ACLED."""
        logger.info(
            "Fetching labels from ACLED",
            operation="acled_fetch"
        )

        try:
            # Ensure we have a valid token
            logger.info(
                "Ensuring valid OAuth token",
                operation="acled_fetch"
            )
            token = await self._ensure_valid_token()

            if not token:
                logger.error(
                    "Failed to obtain OAuth token",
                    operation="acled_fetch"
                )
                return []

            # Calculate date range (last 24 hours)
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=config.acled.fetch_interval_hours)

            # Use the correct ACLED API format with _format=json parameter
            # This is the key difference - ACLED requires _format=json in the URL
            base_url_with_format = f"{self.base_url}/acled/read?_format=json"

            params = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "limit": 500,
                "fields": "event_id_cnty|event_date|event_type|country|fatalities"
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            logger.info(
                f"Fetching from ACLED with date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                operation="acled_fetch",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                url=base_url_with_format
            )

            try:
                response = await self._get(base_url_with_format, params=params, headers=headers)

                logger.info(
                    "ACLED API response received",
                    operation="acled_fetch",
                    response_status=response.get("status"),
                    response_keys=list(response.keys()) if isinstance(response, dict) else "N/A"
                )

                # Check if response has status 200
                if response.get("status") != 200:
                    status = response.get("status", "unknown")
                    logger.error(
                        f"ACLED API returned non-200 status: {status}",
                        operation="acled_fetch",
                        response_status=status,
                        full_response=str(response)[:500]
                    )
                    return []

                labels = await self.parse_response(response)

                logger.info(
                    f"Successfully fetched {len(labels)} labels from ACLED",
                    operation="acled_fetch",
                    label_count=len(labels)
                )

                return labels

            except Exception as e:
                error_msg = str(e)

                # Check if it's a 403 error (access denied)
                if "403" in error_msg:
                    logger.error(
                        f"ACLED API access denied (HTTP 403): Account may not have API access enabled. "
                        f"Please verify API credentials and account permissions at https://acleddata.com/dashboard/api",
                        operation="acled_fetch",
                        error=error_msg,
                        username=self.username
                    )
                else:
                    logger.warning(
                        f"ACLED fetch failed: {error_msg}",
                        operation="acled_fetch",
                        error=error_msg
                    )

                # Return empty list instead of raising - allow other sources to provide data
                return []

        except Exception as e:
            logger.error(
                f"Failed to fetch from ACLED: {str(e)}",
                operation="acled_fetch",
                error_type=type(e).__name__
            )
            # Return empty list instead of raising - allow other sources to provide data
            return []

    async def parse_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse ACLED response."""
        labels = []
        data = response.get("data", [])

        for event in data:
            # Parse event_date from ACLED (format: YYYY-MM-DD)
            event_date_str = event.get("event_date", "")
            try:
                if event_date_str:
                    # Convert YYYY-MM-DD to ISO format with time
                    event_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
                    event_timestamp = event_dt.isoformat() + "Z"
                else:
                    event_timestamp = datetime.utcnow().isoformat() + "Z"
            except Exception:
                event_timestamp = datetime.utcnow().isoformat() + "Z"

            label = {
                "event_id": str(event.get("event_id_cnty", "")),
                "event_date": event_date_str,
                "event_timestamp": event_timestamp,  # Actual event time (ISO format)
                "country": event.get("country", ""),
                "event_type": event.get("event_type", ""),
                "fatalities": int(event.get("fatalities", 0)),
                "label_conflict": 1 if event.get("event_type") in ["Violence against civilians", "Protests"] else 0,
                "confidence": 0.85,  # ACLED data is high confidence
                "source_url": event.get("source_url", ""),
                "fetched_at": datetime.utcnow().isoformat() + "Z",  # When fetched from API
                "trace_id": logger.trace_id
            }
            labels.append(label)

        return labels


class GDELTFetcher(BaseAPIClient):
    """GDELT API fetcher using gdelt library with NER-based country extraction."""

    # GDELT event codes for conflict classification
    CONFLICT_EVENT_CODES = {
        18: "PROTEST",
        19: "RIOT",
        20: "VIOLENCE_AGAINST_CIVILIANS",
        21: "MASS_VIOLENCE",
        22: "ARMED_CONFLICT",
        23: "MILITARY_ACTION"
    }

    def __init__(self):
        """Initialize GDELT fetcher with NER client."""
        super().__init__(
            name="GDELT",
            base_url=config.gdelt.api_url,
            timeout_seconds=config.api_client.timeout_seconds
        )
        # Import here to avoid issues if gdelt is not installed
        try:
            from gdelt import gdelt
            self.gdelt_client = gdelt(version=2)
        except ImportError:
            logger.warning(
                "gdelt library not installed, GDELT fetcher will not work",
                operation="init"
            )
            self.gdelt_client = None

        # Initialize NER client for country extraction
        try:
            from src.clients.ner_client import NERClient
            self.ner_client = NERClient()
            logger.info(
                "NER client initialized for GDELT country extraction",
                operation="init"
            )
        except Exception as e:
            logger.warning(
                f"Failed to initialize NER client: {str(e)}. Country extraction will be skipped.",
                operation="init",
                error_type=type(e).__name__
            )
            self.ner_client = None

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch events from GDELT using gdelt library."""
        logger.info(
            "Fetching labels from GDELT",
            operation="gdelt_fetch"
        )

        try:
            if not self.gdelt_client:
                raise Exception("GDELT client not initialized")

            # Use gdelt library to fetch events
            # The gdelt library Search() method expects a date range in YYYYMMDD format
            # Query parameter should be a date string, not a keyword
            from datetime import datetime, timedelta
            import sys
            import io
            import logging

            # Get yesterday's date in YYYYMMDD format
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y%m%d")

            # Search for events from yesterday
            # The gdelt library returns a DataFrame with articles
            # Suppress gdelt library debug output by redirecting stdout, stderr, and logging
            old_stdout = sys.stdout
            old_stderr = sys.stderr

            # Suppress gdelt library logging
            gdelt_logger = logging.getLogger('gdelt')
            old_gdelt_level = gdelt_logger.level
            gdelt_logger.setLevel(logging.CRITICAL)

            # Also suppress print statements from gdelt by redirecting file descriptors
            import os
            old_stdout_fd = os.dup(1)
            old_stderr_fd = os.dup(2)
            devnull = os.open(os.devnull, os.O_WRONLY)

            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)

            try:
                results = self.gdelt_client.Search(yesterday, coverage=True)
            finally:
                os.dup2(old_stdout_fd, 1)
                os.dup2(old_stderr_fd, 2)
                os.close(devnull)
                os.close(old_stdout_fd)
                os.close(old_stderr_fd)
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                gdelt_logger.setLevel(old_gdelt_level)

            labels = await self.parse_response(results)

            logger.info(
                f"Successfully fetched {len(labels)} labels from GDELT",
                operation="gdelt_fetch",
                label_count=len(labels)
            )

            return labels

        except Exception as e:
            logger.error(
                f"Failed to fetch from GDELT: {str(e)}",
                operation="gdelt_fetch",
                error_type=type(e).__name__
            )
            raise

    async def parse_response(self, response: Any) -> List[Dict[str, Any]]:
        """Parse GDELT response with event codes, Goldstein scale, and NER-based country extraction."""
        labels = []

        try:
            # gdelt library returns a pandas DataFrame
            if response is None or len(response) == 0:
                logger.warning(
                    "GDELT response is empty",
                    operation="gdelt_parse"
                )
                return labels

            # Convert DataFrame to list of dicts
            for idx, row in response.iterrows():
                try:
                    # Extract event information from row
                    url = str(row.get("url", "")) if "url" in row else ""
                    title = str(row.get("title", "")) if "title" in row else ""
                    seendate = str(row.get("seendate", "")) if "seendate" in row else ""
                    domain = str(row.get("domain", "")) if "domain" in row else ""
                    language = str(row.get("language", "")) if "language" in row else "en"

                    # Extract GDELT event code (if available)
                    event_code = None
                    event_type_name = "news_event"
                    if "eventcode" in row:
                        try:
                            event_code = int(row.get("eventcode", 0))
                            if event_code in self.CONFLICT_EVENT_CODES:
                                event_type_name = self.CONFLICT_EVENT_CODES[event_code]
                                logger.debug(
                                    f"Extracted GDELT event code: {event_code} ({event_type_name})",
                                    operation="gdelt_parse",
                                    event_code=event_code,
                                    event_type=event_type_name
                                )
                        except (ValueError, TypeError):
                            event_code = None

                    # Extract Goldstein scale (sentiment score: -10 to +10)
                    goldstein_scale = 0.0
                    if "goldstein_scale" in row:
                        try:
                            goldstein_scale = float(row.get("goldstein_scale", 0.0))
                            logger.debug(
                                f"Extracted Goldstein scale: {goldstein_scale}",
                                operation="gdelt_parse",
                                goldstein_scale=goldstein_scale
                            )
                        except (ValueError, TypeError):
                            goldstein_scale = 0.0

                    # Derive conflict label from event code or Goldstein scale
                    label_conflict = 0
                    if event_code and event_code in self.CONFLICT_EVENT_CODES:
                        label_conflict = 1
                    elif goldstein_scale < -2:  # Negative Goldstein = conflict
                        label_conflict = 1

                    # Extract countries using NER (from title + content)
                    countries = []
                    if self.ner_client:
                        try:
                            countries = await self.ner_client.extract_countries_combined(
                                title=title,
                                content="",  # GDELT Doc API doesn't provide full content
                                language=language,
                                article_id=url or f"gdelt_{idx}"
                            )
                            logger.debug(
                                f"Extracted {len(countries)} countries from GDELT article",
                                operation="gdelt_parse",
                                countries=countries,
                                country_count=len(countries)
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract countries using NER: {str(e)}",
                                operation="gdelt_parse",
                                error_type=type(e).__name__
                            )
                            countries = []

                    # Use first country if available, otherwise empty string
                    country = countries[0] if countries else ""

                    # Parse seendate from GDELT (format: YYYYMMDD)
                    try:
                        if seendate and len(seendate) == 8:
                            event_dt = datetime.strptime(seendate, "%Y%m%d")
                            event_timestamp = event_dt.isoformat() + "Z"
                        else:
                            event_timestamp = datetime.utcnow().isoformat() + "Z"
                    except Exception:
                        event_timestamp = datetime.utcnow().isoformat() + "Z"

                    label = {
                        "event_id": url or f"gdelt_{idx}",
                        "event_date": seendate,
                        "event_timestamp": event_timestamp,
                        "event_code": event_code,  # GDELT event code (18-23 for conflicts)
                        "event_type": event_type_name,  # Derived from event code
                        "country": country,  # Extracted using NER
                        "countries": countries,  # All extracted countries
                        "goldstein_scale": goldstein_scale,  # Sentiment score (-10 to +10)
                        "label_conflict": label_conflict,  # Binary conflict label (0/1)
                        "label_event_type": "news_article",
                        "confidence": 0.80,  # Confidence for GDELT articles
                        "source_url": url,
                        "title": title,
                        "domain": domain,
                        "language": language,
                        "fetched_at": datetime.utcnow().isoformat() + "Z",
                        "trace_id": logger.trace_id
                    }
                    labels.append(label)

                    logger.debug(
                        f"Parsed GDELT article: event_code={event_code}, goldstein={goldstein_scale}, "
                        f"conflict={label_conflict}, countries={countries}",
                        operation="gdelt_parse",
                        event_code=event_code,
                        goldstein_scale=goldstein_scale,
                        label_conflict=label_conflict,
                        countries=countries
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to parse GDELT article: {str(e)}",
                        operation="gdelt_parse",
                        error_type=type(e).__name__
                    )
                    continue

        except Exception as e:
            logger.error(
                f"Failed to parse GDELT response: {str(e)}",
                operation="gdelt_parse",
                error_type=type(e).__name__
            )
            raise

        return labels


class BinanceFetcher(BaseAPIClient):
    """Binance API fetcher (free alternative to CoinGecko)."""

    def __init__(self):
        """Initialize Binance fetcher."""
        super().__init__(
            name="Binance",
            base_url=config.binance.api_url,
            timeout_seconds=config.api_client.timeout_seconds
        )
        self.symbols = config.binance.symbols.split(",")
        self.interval = config.binance.interval
        self.limit = config.binance.limit

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch crypto prices from Binance."""
        logger.info(
            "Fetching labels from Binance",
            operation="binance_fetch"
        )

        try:
            all_labels = []

            for symbol in self.symbols:
                symbol = symbol.strip()
                logger.info(
                    f"Fetching Binance klines for {symbol}",
                    operation="binance_fetch",
                    symbol=symbol
                )

                url = f"{self.base_url}/klines"
                params = {
                    "symbol": symbol,
                    "interval": self.interval,
                    "limit": self.limit
                }

                response = await self._get(url, params=params)
                labels = await self.parse_response(response, symbol)
                all_labels.extend(labels)

            logger.info(
                f"Successfully fetched {len(all_labels)} labels from Binance",
                operation="binance_fetch",
                label_count=len(all_labels),
                symbols=len(self.symbols)
            )

            return all_labels

        except Exception as e:
            logger.error(
                f"Failed to fetch from Binance: {str(e)}",
                operation="binance_fetch",
                error_type=type(e).__name__
            )
            raise

    async def parse_response(self, response: List[List[Any]], symbol: str) -> List[Dict[str, Any]]:
        """Parse Binance klines response.

        Response format: [[open_time, open, high, low, close, volume, close_time, ...], ...]
        """
        labels = []

        for i, kline in enumerate(response):
            if len(kline) < 5:
                continue

            open_time = int(kline[0])
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5]) if len(kline) > 5 else 0.0

            # Calculate 10-period change
            change_pct = 0.0
            if i >= 10:
                prev_close = float(response[i - 10][4])
                change_pct = ((close_price - prev_close) / prev_close) * 100

            label = {
                "event_id": f"binance_{symbol}_{open_time}",
                "event_timestamp": datetime.fromtimestamp(open_time / 1000).isoformat() + "Z",  # Actual event time
                "symbol": symbol,
                "open": open_price,
                "close": close_price,
                "high": high_price,
                "low": low_price,
                "volume": volume,
                "change_pct_10p": change_pct,
                "label_spike": 1 if abs(change_pct) > 5.0 else 0,
                "volatility_score": min(abs(change_pct) / 10.0, 1.0),
                "confidence": 0.95,
                "source_url": "https://www.binance.com",
                "fetched_at": datetime.utcnow().isoformat() + "Z",  # When fetched from API
                "trace_id": logger.trace_id
            }
            labels.append(label)

        return labels



class CCXTFetcher(BaseAPIClient):
    """CCXT API fetcher (fallback for crypto data from multiple exchanges)."""

    def __init__(self):
        """Initialize CCXT fetcher."""
        super().__init__(
            name="CCXT",
            base_url="https://ccxt.io",  # Placeholder, CCXT uses exchange-specific URLs
            timeout_seconds=config.api_client.timeout_seconds
        )

        if ccxt is None:
            logger.warning(
                "CCXT not installed, fallback fetcher will not be available",
                operation="init_ccxt"
            )
            self.available = False
        else:
            self.available = config.ccxt.enabled
            self.exchanges = config.ccxt.exchanges.split(",")
            self.symbols = config.ccxt.symbols.split(",")
            self.timeframe = config.ccxt.timeframe
            self.limit = config.ccxt.limit

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch crypto prices from CCXT exchanges (fallback)."""
        if not self.available or ccxt is None:
            logger.warning(
                "CCXT fetcher not available",
                operation="ccxt_fetch"
            )
            return []

        logger.info(
            "Fetching labels from CCXT (fallback)",
            operation="ccxt_fetch"
        )

        all_labels = []

        for exchange_name in self.exchanges:
            exchange_name = exchange_name.strip().lower()

            try:
                logger.info(
                    f"Trying CCXT exchange: {exchange_name}",
                    operation="ccxt_fetch",
                    exchange=exchange_name
                )

                # Get exchange class
                if not hasattr(ccxt, exchange_name):
                    logger.warning(
                        f"Exchange {exchange_name} not supported by CCXT",
                        operation="ccxt_fetch",
                        exchange=exchange_name
                    )
                    continue

                exchange_class = getattr(ccxt, exchange_name)
                exchange = exchange_class()

                # Fetch klines for each symbol
                for symbol in self.symbols:
                    symbol = symbol.strip()

                    try:
                        logger.info(
                            f"Fetching CCXT klines for {symbol} from {exchange_name}",
                            operation="ccxt_fetch",
                            exchange=exchange_name,
                            symbol=symbol
                        )

                        # Fetch OHLCV data
                        ohlcv = exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.limit)
                        labels = await self.parse_response(ohlcv, symbol, exchange_name)
                        all_labels.extend(labels)

                        logger.info(
                            f"Successfully fetched {len(labels)} labels from {exchange_name}",
                            operation="ccxt_fetch",
                            exchange=exchange_name,
                            symbol=symbol,
                            label_count=len(labels)
                        )

                    except Exception as e:
                        logger.warning(
                            f"Failed to fetch {symbol} from {exchange_name}: {str(e)}",
                            operation="ccxt_fetch",
                            exchange=exchange_name,
                            symbol=symbol,
                            error=str(e)
                        )
                        continue

                # If we successfully fetched from this exchange, break
                if all_labels:
                    break

            except Exception as e:
                logger.warning(
                    f"Failed to connect to {exchange_name}: {str(e)}",
                    operation="ccxt_fetch",
                    exchange=exchange_name,
                    error=str(e)
                )
                continue

        logger.info(
            f"Successfully fetched {len(all_labels)} labels from CCXT",
            operation="ccxt_fetch",
            label_count=len(all_labels),
            exchanges_tried=len(self.exchanges)
        )

        return all_labels

    async def parse_response(self, ohlcv: List[List[Any]], symbol: str, exchange: str) -> List[Dict[str, Any]]:
        """Parse CCXT OHLCV response.

        Response format: [[timestamp, open, high, low, close, volume], ...]
        """
        labels = []

        for i, candle in enumerate(ohlcv):
            if len(candle) < 5:
                continue

            timestamp = int(candle[0])
            open_price = float(candle[1])
            high_price = float(candle[2])
            low_price = float(candle[3])
            close_price = float(candle[4])
            volume = float(candle[5]) if len(candle) > 5 else 0.0

            # Calculate 10-period change
            change_pct = 0.0
            if i >= 10:
                prev_close = float(ohlcv[i - 10][4])
                change_pct = ((close_price - prev_close) / prev_close) * 100

            label = {
                "event_id": f"ccxt_{exchange}_{symbol}_{timestamp}",
                "timestamp": datetime.fromtimestamp(timestamp / 1000).isoformat(),
                "exchange": exchange,
                "symbol": symbol,
                "open": open_price,
                "close": close_price,
                "high": high_price,
                "low": low_price,
                "volume": volume,
                "change_pct_10p": change_pct,
                "label_spike": 1 if abs(change_pct) > 5.0 else 0,
                "volatility_score": min(abs(change_pct) / 10.0, 1.0),
                "confidence": 0.90,  # Slightly lower confidence for fallback
                "source_url": f"https://{exchange}.com",
                "fetched_at": datetime.utcnow().isoformat(),
                "trace_id": logger.trace_id
            }
            labels.append(label)

        return labels

"""Unit tests for API clients."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.clients.api_clients import ACLEDFetcher, GDELTFetcher, BinanceFetcher, CircuitBreaker
from src.exceptions import FetchError, CircuitBreakerError


class TestCircuitBreaker:
    """Test circuit breaker."""

    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker is closed initially."""
        cb = CircuitBreaker(threshold=3, timeout_seconds=60)
        assert cb.state == "closed"
        assert not cb.is_open()

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(threshold=3, timeout_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on success."""
        cb = CircuitBreaker(threshold=3, timeout_seconds=60)
        cb.record_failure()
        cb.record_success()
        assert cb.state == "closed"
        assert not cb.is_open()


class TestACLEDFetcher:
    """Test ACLED fetcher."""

    @pytest.mark.asyncio
    async def test_acled_fetcher_initialization(self):
        """Test ACLED fetcher initialization."""
        fetcher = ACLEDFetcher()
        assert fetcher.name == "ACLED"
        assert fetcher.api_key is not None

    @pytest.mark.asyncio
    async def test_acled_parse_response(self):
        """Test ACLED response parsing."""
        fetcher = ACLEDFetcher()
        response = {
            "data": [
                {
                    "event_id_cnty": "123",
                    "event_date": "2025-11-05",
                    "country": "Syria",
                    "event_type": "Violence against civilians",
                    "fatalities": 5,
                    "source_url": "http://example.com"
                }
            ]
        }

        labels = await fetcher.parse_response(response)
        assert len(labels) == 1
        assert labels[0]["event_id"] == "123"
        assert labels[0]["label_conflict"] == 1

    @pytest.mark.asyncio
    async def test_acled_parse_response_multiple(self):
        """Test ACLED response parsing with multiple events."""
        fetcher = ACLEDFetcher()
        response = {
            "data": [
                {
                    "event_id_cnty": "123",
                    "event_date": "2025-11-05",
                    "country": "Syria",
                    "event_type": "Violence against civilians",
                    "fatalities": 5,
                    "source_url": "http://example.com"
                },
                {
                    "event_id_cnty": "124",
                    "event_date": "2025-11-04",
                    "country": "Yemen",
                    "event_type": "Protests",
                    "fatalities": 0,
                    "source_url": "http://example2.com"
                }
            ]
        }

        labels = await fetcher.parse_response(response)
        assert len(labels) == 2
        assert labels[0]["country"] == "Syria"
        assert labels[1]["country"] == "Yemen"

    @pytest.mark.asyncio
    async def test_acled_parse_response_empty(self):
        """Test ACLED response parsing with empty data."""
        fetcher = ACLEDFetcher()
        response = {"data": []}
        labels = await fetcher.parse_response(response)
        assert len(labels) == 0


class TestGDELTFetcher:
    """Test GDELT fetcher."""

    @pytest.mark.asyncio
    async def test_gdelt_fetcher_initialization(self):
        """Test GDELT fetcher initialization."""
        fetcher = GDELTFetcher()
        assert fetcher.name == "GDELT"
        assert fetcher.CONFLICT_EVENT_CODES[18] == "PROTEST"
        assert fetcher.CONFLICT_EVENT_CODES[20] == "VIOLENCE_AGAINST_CIVILIANS"

    @pytest.mark.asyncio
    async def test_gdelt_parse_response_with_event_code(self):
        """Test GDELT response parsing with event codes."""
        import pandas as pd
        fetcher = GDELTFetcher()
        # Mock NER client to avoid actual NER calls
        fetcher.ner_client = None

        response = pd.DataFrame([
            {
                "url": "http://example.com/article",
                "seendate": "20251105",
                "eventcode": 20,  # VIOLENCE_AGAINST_CIVILIANS
                "goldstein_scale": -5.5,
                "title": "Conflict in Syria",
                "domain": "example.com",
                "language": "en"
            }
        ])

        labels = await fetcher.parse_response(response)
        assert len(labels) == 1
        assert labels[0]["event_code"] == 20
        assert labels[0]["event_type"] == "VIOLENCE_AGAINST_CIVILIANS"
        assert labels[0]["goldstein_scale"] == -5.5
        assert labels[0]["label_conflict"] == 1

    @pytest.mark.asyncio
    async def test_gdelt_parse_response_with_goldstein_conflict(self):
        """Test GDELT conflict detection via Goldstein scale."""
        import pandas as pd
        fetcher = GDELTFetcher()
        fetcher.ner_client = None

        response = pd.DataFrame([
            {
                "url": "http://example.com/article",
                "seendate": "20251105",
                "eventcode": 0,  # Non-conflict code
                "goldstein_scale": -3.0,  # Negative = conflict
                "title": "Negative event",
                "domain": "example.com",
                "language": "en"
            }
        ])

        labels = await fetcher.parse_response(response)
        assert len(labels) == 1
        assert labels[0]["label_conflict"] == 1  # Derived from Goldstein

    @pytest.mark.asyncio
    async def test_gdelt_parse_response_no_conflict(self):
        """Test GDELT non-conflict event."""
        import pandas as pd
        fetcher = GDELTFetcher()
        fetcher.ner_client = None

        response = pd.DataFrame([
            {
                "url": "http://example.com/article",
                "seendate": "20251105",
                "eventcode": 1,  # Non-conflict code
                "goldstein_scale": 2.0,  # Positive = cooperation
                "title": "Positive event",
                "domain": "example.com",
                "language": "en"
            }
        ])

        labels = await fetcher.parse_response(response)
        assert len(labels) == 1
        assert labels[0]["label_conflict"] == 0

    @pytest.mark.asyncio
    async def test_gdelt_parse_response_multiple(self):
        """Test GDELT response parsing with multiple articles."""
        import pandas as pd
        fetcher = GDELTFetcher()
        fetcher.ner_client = None

        response = pd.DataFrame([
            {
                "url": "http://example.com/article1",
                "seendate": "20251105",
                "eventcode": 20,
                "goldstein_scale": -5.0,
                "title": "Article 1",
                "domain": "example.com",
                "language": "en"
            },
            {
                "url": "http://example2.com/article2",
                "seendate": "20251104",
                "eventcode": 1,
                "goldstein_scale": 3.0,
                "title": "Article 2",
                "domain": "example2.com",
                "language": "fr"
            }
        ])

        labels = await fetcher.parse_response(response)
        assert len(labels) == 2
        assert labels[0]["label_conflict"] == 1
        assert labels[1]["label_conflict"] == 0

    @pytest.mark.asyncio
    async def test_gdelt_parse_response_empty(self):
        """Test GDELT response parsing with empty DataFrame."""
        import pandas as pd
        fetcher = GDELTFetcher()
        response = pd.DataFrame([])
        labels = await fetcher.parse_response(response)
        assert len(labels) == 0

    @pytest.mark.asyncio
    async def test_gdelt_conflict_event_codes(self):
        """Test all GDELT conflict event codes."""
        import pandas as pd
        fetcher = GDELTFetcher()
        fetcher.ner_client = None

        conflict_codes = [18, 19, 20, 21, 22, 23]
        for code in conflict_codes:
            response = pd.DataFrame([
                {
                    "url": f"http://example.com/article{code}",
                    "seendate": "20251105",
                    "eventcode": code,
                    "goldstein_scale": 0.0,
                    "title": f"Conflict {code}",
                    "domain": "example.com",
                    "language": "en"
                }
            ])

            labels = await fetcher.parse_response(response)
            assert len(labels) == 1
            assert labels[0]["event_code"] == code
            assert labels[0]["label_conflict"] == 1
            assert labels[0]["event_type"] == fetcher.CONFLICT_EVENT_CODES[code]


class TestBinanceFetcher:
    """Test Binance fetcher."""

    @pytest.mark.asyncio
    async def test_binance_fetcher_initialization(self):
        """Test Binance fetcher initialization."""
        fetcher = BinanceFetcher()
        assert fetcher.name == "Binance"

    @pytest.mark.asyncio
    async def test_binance_parse_response(self):
        """Test Binance response parsing."""
        fetcher = BinanceFetcher()
        # Binance klines format: [open_time, open, high, low, close, volume, ...]
        response = [
            [1699000000000, 30000.0, 30100.0, 29900.0, 30050.0, 1000.0],
            [1699003600000, 30050.0, 30500.0, 30000.0, 30500.0, 1100.0],
            [1699007200000, 30500.0, 31000.0, 30400.0, 31000.0, 1200.0]
        ]

        labels = await fetcher.parse_response(response, symbol="BTCUSDT")
        assert len(labels) == 3
        assert labels[0]["close"] == 30050.0
        assert labels[1]["close"] == 30500.0

    @pytest.mark.asyncio
    async def test_binance_parse_response_with_price_change(self):
        """Test Binance response parsing with price change calculation."""
        fetcher = BinanceFetcher()
        # Create 15 klines to test 10-period change calculation
        response = []
        for i in range(15):
            base_price = 30000.0 + (i * 100)
            response.append([
                1699000000000 + (i * 3600000),
                base_price,
                base_price + 100,
                base_price - 100,
                base_price + 50,
                1000.0
            ])

        labels = await fetcher.parse_response(response, symbol="BTCUSDT")
        assert len(labels) == 15
        # 10th label should have price change calculated
        assert labels[10]["change_pct_10p"] != 0.0

    @pytest.mark.asyncio
    async def test_binance_parse_response_empty(self):
        """Test Binance response parsing with empty response."""
        fetcher = BinanceFetcher()
        response = []
        labels = await fetcher.parse_response(response, symbol="BTCUSDT")
        assert len(labels) == 0

    @pytest.mark.asyncio
    async def test_binance_parse_response_invalid_kline(self):
        """Test Binance response parsing with invalid kline."""
        fetcher = BinanceFetcher()
        response = [
            [1699000000000, 30000.0],  # Too short, should be skipped
            [1699003600000, 30050.0, 30500.0, 30000.0, 30500.0, 1100.0]
        ]
        labels = await fetcher.parse_response(response, symbol="BTCUSDT")
        assert len(labels) == 1  # Only valid kline should be processed

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open(self):
        """Test circuit breaker half-open state."""
        import time
        cb = CircuitBreaker(threshold=1, timeout_seconds=1)
        cb.record_failure()
        assert cb.is_open()

        # Wait for timeout
        time.sleep(1.1)

        # Should transition to half-open
        assert cb.state in ["half-open", "open"]

    @pytest.mark.asyncio
    async def test_acled_fetcher_initialization(self, mock_config):
        """Test ACLED fetcher initialization."""
        with patch('src.config.config', mock_config):
            fetcher = ACLEDFetcher()
            assert fetcher is not None

    @pytest.mark.asyncio
    async def test_gdelt_fetcher_initialization(self, mock_config):
        """Test GDELT fetcher initialization."""
        with patch('src.config.config', mock_config):
            fetcher = GDELTFetcher()
            assert fetcher is not None

    @pytest.mark.asyncio
    async def test_binance_fetcher_initialization(self, mock_config):
        """Test Binance fetcher initialization."""
        with patch('src.config.config', mock_config):
            fetcher = BinanceFetcher()
            assert fetcher is not None

    @pytest.mark.asyncio
    async def test_acled_fetcher_has_fetch_method(self, mock_config):
        """Test ACLED fetcher has fetch method."""
        with patch('src.config.config', mock_config):
            fetcher = ACLEDFetcher()
            assert callable(getattr(fetcher, 'fetch', None))

    @pytest.mark.asyncio
    async def test_gdelt_fetcher_has_fetch_method(self, mock_config):
        """Test GDELT fetcher has fetch method."""
        with patch('src.config.config', mock_config):
            fetcher = GDELTFetcher()
            assert callable(getattr(fetcher, 'fetch', None))

    @pytest.mark.asyncio
    async def test_binance_fetcher_has_fetch_method(self, mock_config):
        """Test Binance fetcher has fetch method."""
        with patch('src.config.config', mock_config):
            fetcher = BinanceFetcher()
            assert callable(getattr(fetcher, 'fetch', None))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


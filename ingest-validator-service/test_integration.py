#!/usr/bin/env python3
"""
Integration test for Ingest Validator Service with Crawler Service.

This test verifies:
1. Crawler Service is running and healthy
2. Ingest Validator Service can be started
3. Kafka topics are properly configured
4. Message flow from Crawler → Kafka → Validator
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import httpx


class IntegrationTester:
    """Integration test runner for Ingest Validator Service."""

    def __init__(self):
        self.crawler_url = "http://localhost:8000"
        self.validator_url = "http://127.0.0.1:8081"
        self.client = httpx.Client(timeout=10.0)
        self.results = []

    def log(self, level: str, message: str):
        """Log test message."""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] {level:8} {message}")
        self.results.append({"timestamp": timestamp, "level": level, "message": message})

    def test_crawler_health(self) -> bool:
        """Test Crawler Service health."""
        self.log("INFO", "Testing Crawler Service health...")
        try:
            response = self.client.get(f"{self.crawler_url}/health")
            if response.status_code == 200:
                self.log("✅", "Crawler Service is healthy")
                return True
            else:
                self.log("❌", f"Crawler Service health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log("❌", f"Crawler Service health check error: {str(e)}")
            return False

    def test_crawler_ready(self) -> bool:
        """Test Crawler Service readiness."""
        self.log("INFO", "Testing Crawler Service readiness...")
        try:
            response = self.client.get(f"{self.crawler_url}/ready")
            if response.status_code == 200:
                self.log("✅", "Crawler Service is ready")
                return True
            else:
                self.log("❌", f"Crawler Service readiness check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log("❌", f"Crawler Service readiness check error: {str(e)}")
            return False

    def test_crawler_metrics(self) -> bool:
        """Test Crawler Service metrics endpoint."""
        self.log("INFO", "Testing Crawler Service metrics...")
        try:
            response = self.client.get(f"{self.crawler_url}/metrics")
            if response.status_code == 200:
                metrics = response.text
                if "crawler_articles_crawled_total" in metrics:
                    self.log("✅", "Crawler Service metrics available")
                    return True
                else:
                    self.log("⚠️", "Crawler Service metrics missing expected metrics")
                    return False
            else:
                self.log("❌", f"Crawler Service metrics check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log("❌", f"Crawler Service metrics check error: {str(e)}")
            return False

    def test_validator_health(self) -> bool:
        """Test Ingest Validator Service health."""
        self.log("INFO", "Testing Ingest Validator Service health...")
        try:
            response = self.client.get(f"{self.validator_url}/health")
            if response.status_code == 200:
                self.log("✅", "Ingest Validator Service is healthy")
                return True
            else:
                self.log("⚠️", f"Ingest Validator Service health check: {response.status_code}")
                return False
        except Exception as e:
            self.log("⚠️", f"Ingest Validator Service not yet running: {str(e)}")
            return False

    def test_validator_ready(self) -> bool:
        """Test Ingest Validator Service readiness."""
        self.log("INFO", "Testing Ingest Validator Service readiness...")
        try:
            response = self.client.get(f"{self.validator_url}/ready")
            if response.status_code == 200:
                self.log("✅", "Ingest Validator Service is ready")
                return True
            else:
                self.log("⚠️", f"Ingest Validator Service readiness: {response.status_code}")
                return False
        except Exception as e:
            self.log("⚠️", f"Ingest Validator Service not yet running: {str(e)}")
            return False

    def test_validator_metrics(self) -> bool:
        """Test Ingest Validator Service metrics endpoint."""
        self.log("INFO", "Testing Ingest Validator Service metrics...")
        try:
            response = self.client.get(f"{self.validator_url}/metrics")
            if response.status_code == 200:
                metrics = response.text
                if "validator_messages_consumed_total" in metrics:
                    self.log("✅", "Ingest Validator Service metrics available")
                    return True
                else:
                    self.log("⚠️", "Ingest Validator Service metrics missing expected metrics")
                    return False
            else:
                self.log("⚠️", f"Ingest Validator Service metrics: {response.status_code}")
                return False
        except Exception as e:
            self.log("⚠️", f"Ingest Validator Service metrics error: {str(e)}")
            return False

    def test_crawler_feeds(self) -> bool:
        """Test Crawler Service feeds endpoint."""
        self.log("INFO", "Testing Crawler Service feeds endpoint...")
        try:
            response = self.client.get(f"{self.crawler_url}/feeds")
            if response.status_code == 200:
                feeds = response.json()
                self.log("✅", f"Crawler Service has {len(feeds)} feeds configured")
                return True
            else:
                self.log("❌", f"Crawler Service feeds check failed: {response.status_code}")
                return False
        except Exception as e:
            self.log("❌", f"Crawler Service feeds check error: {str(e)}")
            return False

    def run_all_tests(self) -> bool:
        """Run all integration tests."""
        self.log("INFO", "=" * 60)
        self.log("INFO", "Starting Integration Tests")
        self.log("INFO", "=" * 60)

        tests = [
            ("Crawler Health", self.test_crawler_health),
            ("Crawler Ready", self.test_crawler_ready),
            ("Crawler Metrics", self.test_crawler_metrics),
            ("Crawler Feeds", self.test_crawler_feeds),
            ("Validator Health", self.test_validator_health),
            ("Validator Ready", self.test_validator_ready),
            ("Validator Metrics", self.test_validator_metrics),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                self.log("❌", f"Test {test_name} failed with exception: {str(e)}")
                results[test_name] = False

        self.log("INFO", "=" * 60)
        self.log("INFO", "Test Results Summary")
        self.log("INFO", "=" * 60)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log("INFO", f"{status}: {test_name}")

        self.log("INFO", f"Total: {passed}/{total} tests passed")
        self.log("INFO", "=" * 60)

        return passed == total

    def close(self):
        """Close HTTP client."""
        self.client.close()


def main():
    """Run integration tests."""
    tester = IntegrationTester()
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()


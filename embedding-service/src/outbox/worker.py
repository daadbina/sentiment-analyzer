"""Outbox worker for async processing."""

import logging
import asyncio
from typing import Optional, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OutboxWorker:
    """Worker for processing outbox entries asynchronously."""

    def __init__(
        self,
        batch_size: int = 100,
        poll_interval_seconds: float = 5.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 10.0,
    ):
        """
        Initialize outbox worker.

        Args:
            batch_size: Number of entries to process per batch
            poll_interval_seconds: Interval between polls
            max_retries: Maximum number of retries
            retry_delay_seconds: Delay between retries
        """
        self.batch_size = batch_size
        self.poll_interval_seconds = poll_interval_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.is_running = False
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0

    async def start(
        self,
        fetch_entries_fn: Callable,
        process_entry_fn: Callable,
        mark_processed_fn: Callable,
        mark_failed_fn: Callable,
    ) -> None:
        """
        Start outbox worker.

        Args:
            fetch_entries_fn: Async function to fetch unprocessed entries
            process_entry_fn: Async function to process entry
            mark_processed_fn: Async function to mark entry as processed
            mark_failed_fn: Async function to mark entry as failed
        """
        self.is_running = True
        logger.info("Outbox worker started")

        try:
            while self.is_running:
                try:
                    # Fetch unprocessed entries
                    entries = await fetch_entries_fn(self.batch_size)

                    if not entries:
                        logger.debug("No entries to process, waiting...")
                        await asyncio.sleep(self.poll_interval_seconds)
                        continue

                    logger.info(f"Processing {len(entries)} outbox entries")

                    # Process each entry
                    for entry in entries:
                        try:
                            # Process entry
                            await process_entry_fn(entry)

                            # Mark as processed
                            await mark_processed_fn(entry)

                            self.processed_count += 1
                            logger.debug(f"Processed entry: {entry.get('id')}")

                        except Exception as e:
                            logger.error(f"Error processing entry {entry.get('id')}: {e}")

                            # Retry logic
                            retry_count = entry.get("retry_count", 0)

                            if retry_count < self.max_retries:
                                # Increment retry count and reschedule
                                entry["retry_count"] = retry_count + 1
                                entry["next_retry_at"] = (
                                    datetime.now() + timedelta(seconds=self.retry_delay_seconds)
                                ).isoformat()

                                logger.info(
                                    f"Retrying entry {entry.get('id')} "
                                    f"(attempt {retry_count + 1}/{self.max_retries})"
                                )

                                self.retry_count += 1

                            else:
                                # Max retries exceeded, mark as failed
                                await mark_failed_fn(entry)
                                self.failed_count += 1

                                logger.error(
                                    f"Entry {entry.get('id')} failed after "
                                    f"{self.max_retries} retries"
                                )

                except Exception as e:
                    logger.error(f"Error in outbox worker loop: {e}")
                    await asyncio.sleep(self.poll_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Outbox worker cancelled")
            self.is_running = False

        except Exception as e:
            logger.error(f"Outbox worker error: {e}")
            self.is_running = False

    def stop(self) -> None:
        """Stop outbox worker."""
        self.is_running = False
        logger.info("Outbox worker stopped")

    def get_statistics(self) -> dict:
        """
        Get worker statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "is_running": self.is_running,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "retry_count": self.retry_count,
            "batch_size": self.batch_size,
            "poll_interval_seconds": self.poll_interval_seconds,
        }

    def reset_statistics(self) -> None:
        """Reset worker statistics."""
        self.processed_count = 0
        self.failed_count = 0
        self.retry_count = 0
        logger.info("Worker statistics reset")


class OutboxWorkerPool:
    """Pool of outbox workers for parallel processing."""

    def __init__(self, num_workers: int = 3):
        """
        Initialize worker pool.

        Args:
            num_workers: Number of workers in pool
        """
        self.num_workers = num_workers
        self.workers = [
            OutboxWorker() for _ in range(num_workers)
        ]
        self.tasks = []

    async def start(
        self,
        fetch_entries_fn: Callable,
        process_entry_fn: Callable,
        mark_processed_fn: Callable,
        mark_failed_fn: Callable,
    ) -> None:
        """
        Start all workers.

        Args:
            fetch_entries_fn: Async function to fetch entries
            process_entry_fn: Async function to process entry
            mark_processed_fn: Async function to mark processed
            mark_failed_fn: Async function to mark failed
        """
        logger.info(f"Starting outbox worker pool with {self.num_workers} workers")

        for worker in self.workers:
            task = asyncio.create_task(
                worker.start(
                    fetch_entries_fn,
                    process_entry_fn,
                    mark_processed_fn,
                    mark_failed_fn,
                )
            )
            self.tasks.append(task)

    async def stop(self) -> None:
        """Stop all workers."""
        logger.info("Stopping outbox worker pool")

        for worker in self.workers:
            worker.stop()

        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def get_pool_statistics(self) -> dict:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        total_processed = sum(w.processed_count for w in self.workers)
        total_failed = sum(w.failed_count for w in self.workers)
        total_retries = sum(w.retry_count for w in self.workers)

        return {
            "num_workers": self.num_workers,
            "total_processed": total_processed,
            "total_failed": total_failed,
            "total_retries": total_retries,
            "workers": [w.get_statistics() for w in self.workers],
        }


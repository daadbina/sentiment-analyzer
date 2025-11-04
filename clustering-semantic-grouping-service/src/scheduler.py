"""Job scheduler for clustering pipeline."""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import config
from .pipeline_orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


class ClusteringScheduler:
    """Manages scheduled clustering jobs."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.orchestrator = PipelineOrchestrator()
        self.last_run_time = None
        logger.info("Initialized ClusteringScheduler")

    def start(self):
        """Start scheduler."""
        try:
            # Schedule clustering job
            self.scheduler.add_job(
                self._run_clustering_job,
                trigger=IntervalTrigger(
                    hours=config.clustering.execution_frequency_hours
                ),
                id="clustering_job",
                name="Clustering Job",
                replace_existing=True,
            )

            self.scheduler.start()
            logger.info(
                f"Started scheduler: clustering job every "
                f"{config.clustering.execution_frequency_hours} hours"
            )

        except Exception as e:
            logger.error(f"Error starting scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop scheduler."""
        try:
            self.scheduler.shutdown()
            self.orchestrator.close()
            logger.info("Stopped scheduler")

        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    def _run_clustering_job(self):
        """Run clustering job."""
        try:
            logger.info("Executing scheduled clustering job")

            total, valid, invalid = self.orchestrator.run_clustering_job(
                last_run_time=self.last_run_time
            )

            self.last_run_time = datetime.utcnow()

            logger.info(
                f"Clustering job completed: "
                f"total={total}, valid={valid}, invalid={invalid}"
            )

        except Exception as e:
            logger.error(f"Clustering job failed: {e}", exc_info=True)

    def get_job_status(self) -> dict:
        """Get scheduler status."""
        jobs = self.scheduler.get_jobs()
        return {
            "running": self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                }
                for job in jobs
            ],
            "last_run_time": self.last_run_time.isoformat()
            if self.last_run_time
            else None,
        }


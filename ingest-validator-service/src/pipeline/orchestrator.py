"""Validation pipeline orchestrator."""

import logging
import time
from typing import List
from src.models import ValidationContext, ValidationResult
from src.pipeline.stage import ValidationStage
from src.validation.scoring import ValidationScorer
from src.metrics import get_metrics

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Orchestrates validation pipeline stages."""

    def __init__(self, stages: List[ValidationStage]):
        """Initialize pipeline.

        Args:
            stages: List of validation stages in order
        """
        self.stages = stages

    async def execute(self, context: ValidationContext) -> ValidationResult:
        """Execute validation pipeline.

        Args:
            context: Validation context

        Returns:
            Validation result
        """
        logger.info(f"Starting validation pipeline for {context.article_id}")
        metrics = get_metrics()
        pipeline_start_time = time.time()

        try:
            # Execute stages in order
            for stage in self.stages:
                logger.debug(f"Executing stage: {stage.name}")
                stage_start_time = time.time()

                context = await stage.execute(context)

                # Record per-stage latency
                stage_duration = time.time() - stage_start_time
                metrics.validation_duration_seconds.labels(stage=stage.name).observe(stage_duration)
                logger.debug(f"Stage {stage.name} completed in {stage_duration:.3f}s")

                # Early exit if critical errors (only for schema, encoding, timestamp stages)
                # Check if THIS stage failed, not future stages
                if stage.name == "SchemaValidation" and not context.validation_details.schema_valid:
                    logger.debug(f"Early exit after {stage.name}: schema_valid=False")
                    break
                elif stage.name == "EncodingValidation" and not context.validation_details.encoding_valid:
                    logger.debug(f"Early exit after {stage.name}: encoding_valid=False")
                    break
                elif stage.name == "TimestampValidation" and not context.validation_details.timestamp_valid:
                    logger.debug(f"Early exit after {stage.name}: timestamp_valid=False")
                    break

            # Determine routing
            routing = ValidationScorer.decide_routing(context.validation_score)

            # Create result
            result = ValidationResult(
                article_id=context.article_id,
                trace_id=context.trace_id,
                job_id=context.job_id,
                is_valid=routing == "accept",
                validation_score=context.validation_score,
                errors=context.errors,
                warnings=context.warnings,
            )

            # Record end-to-end pipeline latency
            pipeline_duration = time.time() - pipeline_start_time
            metrics.validation_duration_seconds.labels(stage="pipeline_total").observe(pipeline_duration)
            logger.info(
                f"Validation complete for {context.article_id}: "
                f"score={context.validation_score:.2f}, routing={routing}, duration={pipeline_duration:.3f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}")
            pipeline_duration = time.time() - pipeline_start_time
            metrics.validation_duration_seconds.labels(stage="pipeline_error").observe(pipeline_duration)
            return ValidationResult(
                article_id=context.article_id,
                trace_id=context.trace_id,
                job_id=context.job_id,
                is_valid=False,
                validation_score=0.0,
                errors=[str(e)],
                warnings=context.warnings,
            )

    def _should_exit_early(self, context: ValidationContext) -> bool:
        """Determine if pipeline should exit early.

        Args:
            context: Validation context

        Returns:
            True if should exit
        """
        # Exit if schema validation failed
        if not context.validation_details.schema_valid:
            logger.debug(f"Early exit: schema_valid={context.validation_details.schema_valid}")
            return True

        # Exit if encoding validation failed
        if not context.validation_details.encoding_valid:
            logger.debug(f"Early exit: encoding_valid={context.validation_details.encoding_valid}")
            return True

        # Exit if timestamp validation failed
        if not context.validation_details.timestamp_valid:
            logger.debug(f"Early exit: timestamp_valid={context.validation_details.timestamp_valid}")
            return True

        return False

"""Main canonicalizer-normalizer service."""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from ulid import ULID as ULIDClass

from src.config import get_settings
from src.clients import KafkaCanonicalConsumer, KafkaCanonicalProducer
from src.clients.postgres_client import PostgresClient
from src.clients.redis_client import RedisClient
from src.canonicalization import URLCanonicalizer
from src.publisher import PublisherResolver
from src.normalization import ContentNormalizer
from src.enrichment import MetadataEnricher
from src.classification import DomainClassifier
from src.deduplication import FuzzyDeduplicator
from src.scoring import NormalizationScorer
from src.sentiment import SentimentAnalyzer
from src.models import NewsValidatedMessage, NewsCanonicalMessage, NormalizationDetails
from src.exceptions import NormalizationError
import src.metrics as metrics

logger = logging.getLogger(__name__)


class CanonicalizeNormalizerService:
    """Main canonicalizer-normalizer service."""

    def __init__(self):
        """Initialize service."""
        self.settings = get_settings()
        self.consumer = KafkaCanonicalConsumer()
        self.producer = KafkaCanonicalProducer()
        self.postgres_client = PostgresClient()
        self.redis_client = RedisClient()
        self.url_canonicalizer = URLCanonicalizer(
            redirect_max_hops=self.settings.normalization.redirect_max_hops,
            redirect_timeout_seconds=self.settings.normalization.redirect_timeout_seconds,
        )
        self.publisher_resolver = PublisherResolver(self.postgres_client, self.redis_client)
        self.content_normalizer = ContentNormalizer()
        self.metadata_enricher = MetadataEnricher()
        self.domain_classifier = DomainClassifier()
        self.fuzzy_deduplicator = FuzzyDeduplicator(
            threshold=self.settings.normalization.fuzzy_dedup_threshold
        )
        self.scorer = NormalizationScorer()
        self.sentiment_analyzer = SentimentAnalyzer()

    async def start(self) -> None:
        """Start service."""
        try:
            logger.info("Starting canonicalizer-normalizer service")

            # Connect to databases
            await self.postgres_client.connect()
            self.redis_client.connect()

            # Subscribe to input topic
            self.consumer.subscribe([self.settings.kafka.input_topic])

            # Main processing loop
            await self._process_messages()

        except Exception as e:
            logger.error(f"Service error: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop service."""
        logger.info("Stopping canonicalizer-normalizer service")
        self.consumer.close()
        self.producer.close()
        await self.postgres_client.disconnect()
        self.redis_client.disconnect()

    async def _process_messages(self) -> None:
        """Process messages from Kafka."""
        logger.info("Starting message processing loop...")
        logger.info("Waiting for messages from 'news_validated' topic...")
        message_count = 0
        idle_count = 0

        while True:
            try:
                # Poll for message
                msg = self.consumer.poll(timeout_ms=1000)
                if not msg:
                    idle_count += 1
                    # Log every 30 seconds when idle
                    if idle_count % 30 == 0:
                        logger.info(f"No new messages. Waiting... (idle for {idle_count} seconds)")
                    continue

                # Reset idle counter when message received
                idle_count = 0

                # Deserialize message
                validated_msg = self.consumer.deserialize_message(msg)

                message_count += 1
                logger.info(
                    f"Processing message #{message_count}: article_id={validated_msg.article_id}, "
                    f"url={validated_msg.url}, partition={msg.partition()}, offset={msg.offset()}"
                )

                # Process message
                await self._process_article(validated_msg)

                # Commit offset
                self.consumer.commit(msg)

                metrics.messages_processed.labels(status="success").inc()
                logger.info(
                    f"Successfully processed message #{message_count}: article_id={validated_msg.article_id}"
                )

            except Exception as e:
                logger.error(f"Error processing message #{message_count}: {e}", exc_info=True)
                metrics.messages_processed.labels(status="error").inc()
                metrics.errors_total.labels(error_type=type(e).__name__).inc()

    async def _process_article(self, validated_msg: NewsValidatedMessage) -> None:
        """Process single article through normalization pipeline.

        Args:
            validated_msg: Validated news message
        """
        start_time = datetime.utcnow()
        trace_id = validated_msg.trace_id
        article_id = validated_msg.article_id

        try:
            # Step 1: URL Canonicalization
            url_result = self.url_canonicalizer.canonicalize(validated_msg.canonical_url)
            if not url_result.canonicalized:
                logger.warning(f"URL canonicalization failed for {article_id}")
                metrics.url_canonicalization_failures.inc()
            else:
                metrics.url_canonicalization_success.inc()

            # Step 2: Publisher Resolution
            publisher = await self.publisher_resolver.resolve_publisher(url_result.normalized_url)
            if not publisher:
                logger.warning(f"Publisher resolution failed for {article_id}")
                metrics.publisher_resolution_failures.inc()
                publisher_id = "unknown"
                publisher_name = "Unknown"
                publisher_credibility = 0.5
            else:
                metrics.publisher_resolution_success.inc()
                publisher_id = publisher.publisher_id
                publisher_name = publisher.name
                publisher_credibility = publisher.credibility_score

            # Step 3: Content Normalization
            content_result = self.content_normalizer.normalize(
                validated_msg.title,
                validated_msg.body,
            )
            if content_result.error:
                logger.warning(f"Content normalization failed for {article_id}")
                metrics.content_normalization_failures.inc()
            else:
                metrics.content_normalization_success.inc()

            # Step 4: Metadata Enrichment
            metadata_result = self.metadata_enricher.enrich(
                content_result.normalized_title,
                content_result.normalized_body,
                url_result.normalized_url,
            )
            if metadata_result.error:
                logger.warning(f"Metadata enrichment failed for {article_id}")
                metrics.metadata_enrichment_failures.inc()
            else:
                metrics.metadata_enrichment_success.inc()

            # Step 5: Domain Classification
            domain_result = self.domain_classifier.classify(
                content_result.normalized_title,
                content_result.normalized_body,
            )
            if domain_result.error:
                logger.warning(f"Domain classification failed for {article_id}")
                metrics.domain_classification_failures.inc()
            else:
                metrics.domain_classification_success.inc()

            # Step 6: Fuzzy Deduplication
            combined_content = f"{content_result.normalized_title} {content_result.normalized_body}"
            dedup_result = self.fuzzy_deduplicator.check_duplicate(article_id, combined_content)
            if dedup_result.similar_articles:
                metrics.fuzzy_dedup_duplicates_found.inc(len(dedup_result.similar_articles))

            # Step 7: Sentiment Analysis
            sentiment_text = f"{content_result.normalized_title} {content_result.normalized_body}"

            # Log sentiment text details for debugging
            logger.info(
                f"[{trace_id}] Preparing sentiment analysis: article_id={article_id}, "
                f"title_length={len(content_result.normalized_title)}, "
                f"body_length={len(content_result.normalized_body)}, "
                f"total_length={len(sentiment_text)}"
            )

            sentiment_score = self.sentiment_analyzer.analyze(
                sentiment_text,
                language=validated_msg.language
            )

            logger.info(
                f"[{trace_id}] Sentiment analysis complete: article_id={article_id}, "
                f"language={validated_msg.language}, sentiment_score={sentiment_score:.3f}"
            )

            # Step 8: Calculate Normalization Score
            normalization_score = self.scorer.calculate_score(
                url_canonicalized=url_result.canonicalized,
                publisher_credibility=publisher_credibility,
                content_cleaned=not content_result.error,
                metadata_enriched=not metadata_result.error,
                domain_classified=not domain_result.error,
                fuzzy_dedup_checked=dedup_result.checked,
                word_count=content_result.word_count,
                readability_score=metadata_result.readability_score,
            )
            metrics.normalization_score.observe(normalization_score)

            # Step 9: Create output message
            canonicalized_at = datetime.utcnow().isoformat() + "Z"
            canonical_msg = NewsCanonicalMessage(
                article_id=article_id,
                canonical_url=validated_msg.canonical_url,
                normalized_url=url_result.normalized_url,
                url_hash=url_result.url_hash,
                title=validated_msg.title,
                normalized_title=content_result.normalized_title,
                body=validated_msg.body,
                normalized_body=content_result.normalized_body,
                url=validated_msg.url,
                source=validated_msg.source,
                publisher_id=publisher_id,
                publisher_name=publisher_name,
                publisher_credibility=publisher_credibility,
                publisher_country=publisher.country if publisher else None,
                language=validated_msg.language,
                sentiment_score=sentiment_score,
                source_published_at_utc=validated_msg.source_published_at_utc,
                validated_at=validated_msg.validated_at,
                canonicalized_at=canonicalized_at,
                domain=url_result.domain,  # Domain from URL normalization (required by NER)
                published_at=validated_msg.source_published_at_utc,  # Alias for NER service
                normalized_at=canonicalized_at,  # Alias for NER service
                country=metadata_result.country,
                region=metadata_result.region,
                domain_category=domain_result.domain_category,
                content_type=metadata_result.content_type,
                readability_score=metadata_result.readability_score,
                word_count=content_result.word_count,
                sentence_count=content_result.sentence_count,
                checksum=validated_msg.checksum,
                normalized_checksum=content_result.normalized_checksum,
                validation_score=validated_msg.validation_score,
                normalization_score=normalization_score,
                normalization_details=NormalizationDetails(
                    url_canonicalized=url_result.canonicalized,
                    redirects_resolved=url_result.redirects_resolved,
                    publisher_identified=publisher is not None,
                    content_cleaned=not content_result.error,
                    metadata_enriched=not metadata_result.error,
                    domain_classified=not domain_result.error,
                    fuzzy_dedup_checked=dedup_result.checked,
                ),
                schema_version="1.0",
                ingest_job_id=validated_msg.ingest_job_id,
                validation_job_id=validated_msg.validation_job_id,
                canonicalization_job_id=str(ULIDClass()),
                trace_id=trace_id,
            )

            # Step 10: Publish message
            decision = self.scorer.get_decision(
                normalization_score,
                self.settings.normalization.normalization_score_accept,
                self.settings.normalization.normalization_score_review,
            )

            if decision in ["accept", "review"]:
                self.producer.publish_canonical(canonical_msg)
                metrics.messages_published.labels(topic=self.settings.kafka.output_topic).inc()
                logger.info(
                    f"Published to news_canonical: article_id={article_id}, "
                    f"decision={decision}, score={normalization_score:.3f}, "
                    f"publisher={publisher_name}"
                )
            else:
                self.producer.publish_dlq(
                    article_id,
                    f"Low normalization score: {normalization_score}",
                    canonical_msg.to_dict(),
                )
                metrics.dlq_messages.labels(reason="low_score").inc()
                logger.info(
                    f"Published to DLQ: article_id={article_id}, "
                    f"score={normalization_score:.3f}, reason=low_score"
                )

            # Log processing duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics.processing_duration.labels(stage="full_pipeline").observe(duration)
            logger.info(f"Pipeline completed in {duration:.2f}s for article_id={article_id}")

        except Exception as e:
            logger.error(f"Article processing failed: {e}")
            self.producer.publish_dlq(
                article_id,
                f"Processing error: {str(e)}",
                validated_msg.model_dump(),
            )
            metrics.dlq_messages.labels(reason="processing_error").inc()


"""Label reconciliation engine."""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from src.config import config
from src.exceptions import ReconciliationError
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


# Lazy import NER client to avoid circular dependencies
_ner_client = None


def _get_ner_client():
    """Get or initialize NER client (lazy loading)."""
    global _ner_client
    if _ner_client is None:
        try:
            from src.clients.ner_client import NERClient
            _ner_client = NERClient()
            logger.info("NER client initialized for country extraction in reconciler")
        except Exception as e:
            logger.warning(
                f"Failed to initialize NER client in reconciler: {str(e)}. "
                "Country extraction for reconciled matches will be skipped.",
                operation="init_ner_client",
                error_type=type(e).__name__
            )
            _ner_client = False  # Mark as failed to avoid repeated attempts
    return _ner_client if _ner_client is not False else None


class TemporalMatcher:
    """Temporal matching for labels and semantic groups."""

    def __init__(self, threshold_hours: int = 48):
        """Initialize temporal matcher."""
        self.threshold_hours = threshold_hours

    @staticmethod
    def parse_timestamp(ts: Union[str, int, float]) -> Optional[datetime]:
        """Parse timestamp from various formats.

        Args:
            ts: Timestamp as ISO string, Unix timestamp (int/float), or other format

        Returns:
            datetime object (always offset-aware with UTC timezone) or None if parsing fails
        """
        if not ts:
            return None

        try:
            # Try Unix timestamp (int or float)
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(ts, tz=timezone.utc)

            # Try ISO format string
            if isinstance(ts, str):
                # Handle ISO format with Z suffix
                ts_clean = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_clean)

                # Ensure the datetime is offset-aware (has timezone info)
                if dt.tzinfo is None:
                    # If no timezone info, assume UTC
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt

            return None

        except Exception as e:
            logger.debug(f"Failed to parse timestamp {ts}: {str(e)}")
            return None

    def match(
        self,
        label_timestamp: Union[str, int, float],
        group_timestamp: Union[str, int, float]
    ) -> Tuple[bool, float]:
        """
        Match label and group by temporal constraint (R8).

        R8: Labels can be assigned to groups created ≥24h AFTER the event.
        This ensures the model has time to observe event outcomes before labeling.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            label_dt = self.parse_timestamp(label_timestamp)
            group_dt = self.parse_timestamp(group_timestamp)

            if not label_dt or not group_dt:
                logger.debug(
                    f"Could not parse timestamps",
                    operation="temporal_match",
                    label_ts=label_timestamp,
                    group_ts=group_timestamp
                )
                return False, 0.0

            # R8: Group must be created at least 24 hours AFTER the event
            min_group_creation_time = label_dt + timedelta(hours=24)

            if group_dt >= min_group_creation_time:
                # Confidence is high if group was created soon after the 24h window
                # Decreases if group was created much later
                hours_after_min = (group_dt - min_group_creation_time).total_seconds() / 3600
                # Confidence: 1.0 if created exactly at 24h, decreases over time
                confidence = max(0.5, 1.0 - (hours_after_min / 720))  # 720h = 30 days
                return True, confidence
            else:
                return False, 0.0

        except Exception as e:
            logger.error(
                f"Temporal matching failed: {str(e)}",
                operation="temporal_match",
                error_type=type(e).__name__
            )
            return False, 0.0


class CountryEventTypeMatcher:
    """Match labels to semantic groups by country and event type.

    This matcher is designed for GDELT event data which provides structured
    country and event type information. It matches based on:
    1. Country overlap (does the group mention the same country?)
    2. Event type keywords (does the group mention conflict/violence/etc?)
    3. Returns confidence based on match strength
    """

    def __init__(self, country_threshold: float = 0.6, event_type_threshold: float = 0.6):
        """Initialize country+event type matcher.

        Args:
            country_threshold: Confidence boost for country match (0.6)
            event_type_threshold: Confidence boost for event type match (0.6)
        """
        self.country_threshold = country_threshold
        self.event_type_threshold = event_type_threshold

        # Event type keywords for matching
        self.conflict_keywords = {
            'conflict', 'violence', 'war', 'battle', 'attack', 'protest',
            'riot', 'strike', 'demonstration', 'armed', 'military', 'combat',
            'fighting', 'clash', 'confrontation', 'uprising', 'rebellion',
            'insurgency', 'terrorism', 'extremism', 'militant', 'guerrilla'
        }

    def match(
        self,
        label_countries: List[str],
        label_event_type: str,
        group_description: str
    ) -> Tuple[bool, float]:
        """
        Match label to group by country and event type.

        Args:
            label_countries: List of countries from label (e.g., ['India', 'Pakistan'])
            label_event_type: Event type from label (e.g., 'VIOLENCE_AGAINST_CIVILIANS')
            group_description: Topic label from semantic group

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            if not group_description:
                return False, 0.0

            group_words = set(w.lower() for w in group_description.split() if len(w) > 2)

            # Check for country match
            country_matched = False
            if label_countries:
                for country in label_countries:
                    country_lower = country.lower()
                    if country_lower in group_words:
                        country_matched = True
                        break

            # Check for event type keywords
            event_type_matched = False
            if label_event_type:
                event_type_lower = label_event_type.lower()
                # Check if event type contains conflict keywords
                has_conflict_keyword = any(keyword in event_type_lower for keyword in self.conflict_keywords)
                if has_conflict_keyword:
                    # Check if group mentions conflict-related keywords
                    group_has_conflict = any(keyword in group_words for keyword in self.conflict_keywords)
                    if group_has_conflict:
                        event_type_matched = True

            # REQUIRE BOTH country AND event type to match for a valid match
            # This prevents matching labels to unrelated groups
            if country_matched and event_type_matched:
                # Both match: high confidence
                combined_confidence = 0.8
                matched = True
            elif country_matched:
                # Only country matches: medium confidence
                combined_confidence = 0.6
                matched = True
            elif event_type_matched:
                # Only event type matches: low confidence (not enough)
                combined_confidence = 0.0
                matched = False
            else:
                # No match
                combined_confidence = 0.0
                matched = False

            # logger.debug(
            #     f"Country+EventType matching result",
            #     operation="country_event_match",
            #     label_countries=label_countries,
            #     label_event_type=label_event_type,
            #     country_conf=country_confidence,
            #     event_type_conf=event_type_confidence,
            #     combined_conf=combined_confidence,
            #     matched=matched
            # )

            return matched, combined_confidence

        except Exception as e:
            logger.error(
                f"Country+EventType matching failed: {str(e)}",
                operation="country_event_match",
                error_type=type(e).__name__
            )
            return False, 0.0


class SemanticMatcher:
    """Semantic matching for labels and semantic groups."""

    def __init__(self, similarity_threshold: float = 0.3):
        """Initialize semantic matcher.

        Args:
            similarity_threshold: Minimum Jaccard similarity for match (default 0.3 for lenient matching)
        """
        self.similarity_threshold = similarity_threshold
        self.match_count = 0  # Track number of matches attempted

    def match(
        self,
        label_description: str,
        group_description: str
    ) -> Tuple[bool, float]:
        """
        Match label and group by semantic similarity using Jaccard index.

        Uses lenient keyword-based matching to handle diverse label formats.
        Returns confidence based on word overlap between label and group descriptions.

        Returns:
            Tuple of (matched: bool, confidence: float)
        """
        try:
            # Extract words and filter out common stop words
            label_words = set(w.lower() for w in label_description.split() if len(w) > 2)
            group_words = set(w.lower() for w in group_description.split() if len(w) > 2)

            if not label_words or not group_words:
                # If either is empty, return low confidence but don't reject
                return False, 0.1

            # Calculate Jaccard similarity
            intersection = len(label_words & group_words)
            union = len(label_words | group_words)

            similarity = intersection / union if union > 0 else 0.0

            # Match if similarity meets threshold
            matched = similarity >= self.similarity_threshold

            # DEBUG: Log ONLY successful matches to verify quality (not noise)
            # Log first 100 successful matches to analyze match quality
            if matched:
                self.match_count += 1
                if self.match_count <= 100:
                    logger.info(
                        f"DEBUG: SUCCESSFUL MATCH #{self.match_count}",
                        operation="semantic_match",
                        label_desc=label_description[:100],
                        group_desc=group_description[:100],
                        label_words_count=len(label_words),
                        group_words_count=len(group_words),
                        intersection=intersection,
                        union=union,
                        similarity=round(similarity, 3),
                        threshold=self.similarity_threshold,
                        matched=matched
                    )

            return matched, similarity

        except Exception as e:
            logger.error(
                f"Semantic matching failed: {str(e)}",
                operation="semantic_match",
                error_type=type(e).__name__
            )
            return False, 0.0


class LabelReconciler:
    """Reconcile labels with semantic groups."""

    def __init__(self):
        """Initialize label reconciler."""
        self.temporal_matcher = TemporalMatcher(
            threshold_hours=config.label.reconciliation_threshold_hours
        )
        # Threshold set to 0.2 to filter out single-word noise matches
        # 0.2 means at least 2 words must match out of 10 (20% overlap)
        # This filters out weak matches like "COMPANY" matching "company" only
        self.semantic_matcher = SemanticMatcher(
            similarity_threshold=0.2  # Increased from 0.1 to reduce noise
        )
        self.country_event_matcher = CountryEventTypeMatcher(
            country_threshold=0.6,
            event_type_threshold=0.4
        )
        # NER client will be lazily initialized when needed
        self.ner_client = None

    async def reconcile(
        self,
        label: Dict[str, Any],
        semantic_groups: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Reconcile label with semantic groups.

        Returns:
            Reconciliation result with group_id and confidence, or None if no match
        """
        try:
            best_match = None
            best_confidence = 0.0

            # Use event_timestamp (actual event time) instead of fetched_at (when fetched from API)
            label_timestamp = label.get("event_timestamp") or label.get("fetched_at", "")

            if not label_timestamp:
                logger.warning(
                    f"Label has no timestamp for reconciliation",
                    operation="reconcile",
                    event_id=label.get("event_id")
                )
                return None

            # Log label details for debugging (first label only)
            label_countries = label.get("countries", [])
            label_event_type = label.get("event_type", "")
            # Use description (event_type + countries + title) for richer context
            label_description = (
                label.get("description") or
                label.get("title") or
                label.get("event_type") or
                ""
            )

            # DEBUG: Log first label details
            if not hasattr(self, '_logged_first_label'):
                self._logged_first_label = True
                # Log ALL group IDs to see if they're diverse
                all_group_ids = [g.get("group_id") for g in semantic_groups]
                unique_group_ids = set(all_group_ids)
                logger.info(
                    f"DEBUG: First label details",
                    operation="reconcile",
                    event_id=label.get("event_id"),
                    countries=label_countries,
                    event_type=label_event_type,
                    description=label_description[:100] if label_description else None,
                    total_groups=len(semantic_groups),
                    unique_group_ids=len(unique_group_ids),
                    all_group_ids=all_group_ids[:5]  # Show first 5
                )

            for group in semantic_groups:
                # TEMPORARY: Skip temporal matching to allow historical GDELT events to match
                # temporal_match, temporal_conf = self.temporal_matcher.match(
                #     label_timestamp,
                #     group.get("created_at", "")
                # )
                #
                # if not temporal_match:
                #     continue

                # Set temporal confidence to 1.0 (always pass)
                temporal_conf = 1.0

                # Get group description for matching
                group_description = (
                    group.get("topic_label") or
                    group.get("cluster_metadata", {}).get("topic_label") or
                    ""
                )

                # DEBUG: Log first group details
                if not hasattr(self, '_logged_first_group'):
                    self._logged_first_group = True
                    logger.info(
                        f"DEBUG: First group details",
                        operation="reconcile",
                        group_id=group.get("group_id"),
                        topic_label=group_description,
                        countries=group.get("countries"),
                        article_count=group.get("article_count")
                    )

                if not group_description:
                    continue  # Skip groups without topic labels

                # PRIMARY: Try semantic matching first (more reliable for diverse content)
                # Use description (event_type + countries + title) for richer context
                label_description = (
                    label.get("description") or
                    label.get("title") or
                    label.get("event_type") or
                    ""
                )

                semantic_match, semantic_conf = self.semantic_matcher.match(
                    label_description,
                    group_description
                )

                if semantic_match:
                    # Semantic match found: use it with high weight
                    # Combined confidence: temporal (0.3) + semantic (0.7)
                    combined_confidence = (temporal_conf * 0.3) + (semantic_conf * 0.7)

                    # Only log if this is the best match so far (reduce noise)
                    if combined_confidence > best_confidence:
                        best_confidence = combined_confidence
                        best_match = {
                            "group_id": group.get("group_id"),
                            "confidence": combined_confidence,
                            "temporal_confidence": temporal_conf,
                            "semantic_confidence": semantic_conf,
                            "match_type": "semantic"
                        }
                else:
                    # FALLBACK: Try country+event type matching if semantic matching fails
                    label_countries = label.get("countries", [])
                    label_event_type = label.get("event_type", "")

                    country_event_match, country_event_conf = self.country_event_matcher.match(
                        label_countries,
                        label_event_type,
                        group_description
                    )

                    if country_event_match:
                        # Country+event match found: use it with lower weight than semantic
                        # Combined confidence: temporal (0.4) + country_event (0.6)
                        combined_confidence = (temporal_conf * 0.4) + (country_event_conf * 0.6)

                        # Only log if this is the best match so far (reduce noise)
                        if combined_confidence > best_confidence:
                            best_confidence = combined_confidence
                            best_match = {
                                "group_id": group.get("group_id"),
                                "confidence": combined_confidence,
                                "temporal_confidence": temporal_conf,
                                "semantic_confidence": country_event_conf,
                                "match_type": "country_event"
                            }

            if best_match and best_confidence >= config.reconciliation.confidence_threshold:
                return best_match
            else:
                # Log rejected matches to understand why they're failing
                if best_match and not hasattr(self, '_logged_rejected_match'):
                    self._logged_rejected_match = True
                    logger.info(
                        f"DEBUG: REJECTED MATCH (confidence too low)",
                        operation="reconcile",
                        best_confidence=best_confidence,
                        threshold=config.reconciliation.confidence_threshold,
                        group_id=best_match.get("group_id"),
                        match_type=best_match.get("match_type"),
                        semantic_confidence=best_match.get("semantic_confidence"),
                        temporal_confidence=best_match.get("temporal_confidence")
                    )
                # No matching group found - this is normal for many labels
                # Only log at debug level to reduce noise
                return None

        except Exception as e:
            logger.error(
                f"Reconciliation failed: {str(e)}",
                operation="reconcile",
                event_id=label.get("event_id"),
                error_type=type(e).__name__
            )
            raise ReconciliationError(
                label.get("event_id", "unknown"),
                "unknown",
                str(e)
            )

    async def _enrich_with_ner_countries(
        self,
        result: Dict[str, Any],
        semantic_groups: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enrich reconciled match with NER-extracted countries when no countries are identified.

        Extracts countries from:
        1. Label description/title (GDELT data)
        2. Semantic group topic_label

        Avoids duplicates by deduplicating extracted countries.

        Args:
            result: Reconciliation result with label and group_id
            semantic_groups: List of semantic groups for lookup

        Returns:
            Enriched result with countries added to label if missing
        """
        try:
            label = result.get("label", {})
            label_countries = label.get("countries", [])

            # DEBUG: Log entry to method
            logger.debug(
                f"_enrich_with_ner_countries called",
                operation="enrich_ner_countries",
                event_id=label.get("event_id"),
                has_countries=bool(label_countries),
                countries_count=len(label_countries) if label_countries else 0
            )

            # Only extract if no countries are present
            if label_countries:
                logger.debug(
                    f"Label already has countries, skipping NER extraction",
                    operation="enrich_ner_countries",
                    event_id=label.get("event_id"),
                    existing_countries=label_countries
                )
                return result

            # Initialize NER client if needed
            if self.ner_client is None:
                self.ner_client = _get_ner_client()

            if self.ner_client is None:
                logger.debug(
                    f"NER client not available, skipping country extraction",
                    operation="enrich_ner_countries",
                    event_id=label.get("event_id")
                )
                return result

            extracted_countries = []

            # Extract from label description/title (GDELT data)
            label_text = (
                label.get("description") or
                label.get("title") or
                label.get("event_type") or
                ""
            )

            if label_text:
                try:
                    label_language = label.get("language", "en")
                    label_id = label.get("event_id", "unknown")

                    countries_from_label = await self.ner_client.extract_countries(
                        text=label_text,
                        language=label_language,
                        article_id=label_id
                    )

                    if countries_from_label:
                        extracted_countries.extend(countries_from_label)
                        logger.info(
                            f"Extracted {len(countries_from_label)} countries from label text",
                            operation="enrich_ner_countries",
                            event_id=label_id,
                            countries=countries_from_label
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to extract countries from label text: {str(e)}",
                        operation="enrich_ner_countries",
                        event_id=label.get("event_id"),
                        error_type=type(e).__name__
                    )

            # Extract from semantic group topic_label
            group_id = result.get("group_id")
            if group_id:
                # Find the matching semantic group
                matching_group = next(
                    (g for g in semantic_groups if g.get("group_id") == group_id),
                    None
                )

                if matching_group:
                    group_topic = (
                        matching_group.get("topic_label") or
                        matching_group.get("cluster_metadata", {}).get("topic_label") or
                        ""
                    )

                    if group_topic:
                        try:
                            countries_from_group = await self.ner_client.extract_countries(
                                text=group_topic,
                                language="en",  # Topic labels are typically in English
                                article_id=f"group_{group_id}"
                            )

                            if countries_from_group:
                                extracted_countries.extend(countries_from_group)
                                logger.info(
                                    f"Extracted {len(countries_from_group)} countries from group topic",
                                    operation="enrich_ner_countries",
                                    group_id=group_id,
                                    countries=countries_from_group
                                )
                        except Exception as e:
                            logger.warning(
                                f"Failed to extract countries from group topic: {str(e)}",
                                operation="enrich_ner_countries",
                                group_id=group_id,
                                error_type=type(e).__name__
                            )

            # Deduplicate extracted countries (case-insensitive)
            if extracted_countries:
                seen = set()
                unique_countries = []
                for country in extracted_countries:
                    country_lower = country.lower()
                    if country_lower not in seen:
                        seen.add(country_lower)
                        unique_countries.append(country)

                # Update label with extracted countries
                label["countries"] = unique_countries
                result["label"] = label

                logger.info(
                    f"Enriched reconciled match with {len(unique_countries)} NER-extracted countries",
                    operation="enrich_ner_countries",
                    event_id=label.get("event_id"),
                    group_id=group_id,
                    countries=unique_countries
                )
            else:
                logger.debug(
                    f"No countries extracted from label or group",
                    operation="enrich_ner_countries",
                    event_id=label.get("event_id"),
                    group_id=group_id
                )

            return result

        except Exception as e:
            logger.error(
                f"Failed to enrich with NER countries: {str(e)}",
                operation="enrich_ner_countries",
                event_id=label.get("event_id"),
                error_type=type(e).__name__
            )
            # Return original result on error
            return result

    async def reconcile_batch(
        self,
        labels: List[Dict[str, Any]],
        semantic_groups: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reconcile batch of labels."""
        results = []
        total_labels = len(labels)
        ner_enrichment_attempts = 0
        ner_enrichment_success = 0

        logger.info(
            f"Starting batch reconciliation",
            operation="reconcile_batch",
            total_labels=total_labels,
            semantic_groups=len(semantic_groups)
        )

        for idx, label in enumerate(labels):
            result = await self.reconcile(label, semantic_groups)
            if result:
                result["label"] = label

                # Enrich with NER-extracted countries if no countries present
                label_had_no_countries = not label.get("countries")
                result = await self._enrich_with_ner_countries(result, semantic_groups)

                # Track NER enrichment stats
                if label_had_no_countries:
                    ner_enrichment_attempts += 1
                    if result.get("label", {}).get("countries"):
                        ner_enrichment_success += 1

                results.append(result)

            # Log progress every 1000 labels
            if (idx + 1) % 1000 == 0:
                logger.debug(
                    f"Reconciliation progress",
                    operation="reconcile_batch",
                    processed=idx + 1,
                    total=total_labels,
                    matched_so_far=len(results)
                )

        # Log diversity of group_ids in results
        if results:
            result_group_ids = [r.get("group_id") for r in results]
            unique_result_group_ids = set(result_group_ids)
            logger.info(
                f"DEBUG: Reconciliation results diversity",
                operation="reconcile_batch",
                total_results=len(results),
                unique_group_ids=len(unique_result_group_ids),
                sample_group_ids=list(unique_result_group_ids)[:5]
            )

        logger.info(
            f"Batch reconciliation completed",
            operation="reconcile_batch",
            total_labels=len(labels),
            matched_labels=len(results),
            ner_enrichment_attempts=ner_enrichment_attempts,
            ner_enrichment_success=ner_enrichment_success
        )

        return results


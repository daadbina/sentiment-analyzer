"""Tests for future enhancements."""

import pytest
from src.future.enhancements import (
    EnhancementPhase,
    EnhancementPriority,
    Enhancement,
    FutureEnhancements,
)


class TestEnhancementPhase:
    """Tests for EnhancementPhase enum."""

    def test_all_phases_defined(self):
        """Test all phases are defined."""
        phases = [
            EnhancementPhase.PHASE_1,
            EnhancementPhase.PHASE_2,
            EnhancementPhase.PHASE_3,
            EnhancementPhase.PHASE_4,
            EnhancementPhase.FUTURE,
        ]
        assert len(phases) == 5


class TestEnhancementPriority:
    """Tests for EnhancementPriority enum."""

    def test_all_priorities_defined(self):
        """Test all priorities are defined."""
        priorities = [
            EnhancementPriority.CRITICAL,
            EnhancementPriority.HIGH,
            EnhancementPriority.MEDIUM,
            EnhancementPriority.LOW,
        ]
        assert len(priorities) == 4


class TestEnhancement:
    """Tests for Enhancement."""

    def test_create_enhancement(self):
        """Test creating enhancement."""
        enhancement = Enhancement(
            id="enh_001",
            title="Test Enhancement",
            description="Test description",
            phase=EnhancementPhase.PHASE_1,
            priority=EnhancementPriority.HIGH,
            estimated_effort="2 weeks",
        )
        assert enhancement.id == "enh_001"
        assert enhancement.title == "Test Enhancement"

    def test_enhancement_to_dict(self):
        """Test converting enhancement to dictionary."""
        enhancement = Enhancement(
            id="enh_001",
            title="Test Enhancement",
            description="Test description",
            phase=EnhancementPhase.PHASE_1,
            priority=EnhancementPriority.HIGH,
            estimated_effort="2 weeks",
        )
        enh_dict = enhancement.to_dict()
        assert enh_dict["id"] == "enh_001"
        assert enh_dict["phase"] == "phase_1"


class TestFutureEnhancements:
    """Tests for FutureEnhancements."""

    def test_get_all_enhancements(self):
        """Test getting all enhancements."""
        enhancements = FutureEnhancements.get_all_enhancements()
        assert len(enhancements) == 9

    def test_get_enhancements_by_phase(self):
        """Test getting enhancements by phase."""
        phase_1_enhancements = FutureEnhancements.get_enhancements_by_phase(
            EnhancementPhase.PHASE_1
        )
        assert len(phase_1_enhancements) == 3

        phase_2_enhancements = FutureEnhancements.get_enhancements_by_phase(
            EnhancementPhase.PHASE_2
        )
        assert len(phase_2_enhancements) == 3

    def test_get_enhancements_by_priority(self):
        """Test getting enhancements by priority."""
        high_priority = FutureEnhancements.get_enhancements_by_priority(
            EnhancementPriority.HIGH
        )
        assert len(high_priority) > 0
        assert all(e.priority == EnhancementPriority.HIGH for e in high_priority)

    def test_get_enhancement_by_id(self):
        """Test getting enhancement by ID."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_001")
        assert enhancement is not None
        assert enhancement.id == "enh_001"
        assert enhancement.title == "Advanced NER Models"

    def test_get_enhancement_by_id_not_found(self):
        """Test getting non-existent enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_999")
        assert enhancement is None

    def test_get_enhancement_roadmap(self):
        """Test getting enhancement roadmap."""
        roadmap = FutureEnhancements.get_enhancement_roadmap()
        assert "phase_1" in roadmap
        assert "phase_2" in roadmap
        assert "phase_3" in roadmap
        assert "phase_4" in roadmap
        assert "future" in roadmap

    def test_get_high_priority_enhancements(self):
        """Test getting high priority enhancements."""
        high_priority = FutureEnhancements.get_high_priority_enhancements()
        assert len(high_priority) > 0
        assert all(
            e.priority in [EnhancementPriority.CRITICAL, EnhancementPriority.HIGH]
            for e in high_priority
        )

    def test_get_enhancement_dependencies(self):
        """Test getting enhancement dependencies."""
        # Get enhancement with dependencies
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_001")
        dependencies = FutureEnhancements.get_enhancement_dependencies("enh_001")
        # Should match the dependencies list
        assert len(dependencies) == len(enhancement.dependencies)

    def test_get_roadmap_summary(self):
        """Test getting roadmap summary."""
        summary = FutureEnhancements.get_roadmap_summary()
        assert "total_enhancements" in summary
        assert "by_phase" in summary
        assert "by_priority" in summary
        assert "high_priority_count" in summary
        assert summary["total_enhancements"] == 9


class TestEnhancementDetails:
    """Tests for specific enhancements."""

    def test_advanced_ner_models_enhancement(self):
        """Test Advanced NER Models enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_001")
        assert enhancement.title == "Advanced NER Models"
        assert enhancement.phase == EnhancementPhase.PHASE_1
        assert enhancement.priority == EnhancementPriority.HIGH
        assert len(enhancement.benefits) > 0
        assert len(enhancement.risks) > 0

    def test_real_time_entity_tracking_enhancement(self):
        """Test Real-time Entity Tracking enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_002")
        assert enhancement.title == "Real-time Entity Tracking"
        assert enhancement.phase == EnhancementPhase.PHASE_1

    def test_entity_relationship_graphs_enhancement(self):
        """Test Entity Relationship Graphs enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_003")
        assert enhancement.title == "Entity Relationship Graphs"
        assert enhancement.phase == EnhancementPhase.PHASE_1

    def test_cross_lingual_entity_linking_enhancement(self):
        """Test Cross-lingual Entity Linking enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_004")
        assert enhancement.title == "Cross-lingual Entity Linking"
        assert enhancement.phase == EnhancementPhase.PHASE_2

    def test_active_learning_pipeline_enhancement(self):
        """Test Active Learning Pipeline enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_005")
        assert enhancement.title == "Active Learning Pipeline"
        assert enhancement.phase == EnhancementPhase.PHASE_2

    def test_federated_learning_support_enhancement(self):
        """Test Federated Learning Support enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_006")
        assert enhancement.title == "Federated Learning Support"
        assert enhancement.phase == EnhancementPhase.PHASE_2

    def test_explainability_enhancement(self):
        """Test Explainability and Interpretability enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_007")
        assert enhancement.title == "Explainability and Interpretability"
        assert enhancement.phase == EnhancementPhase.PHASE_3

    def test_zero_shot_entity_linking_enhancement(self):
        """Test Zero-shot Entity Linking enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_008")
        assert enhancement.title == "Zero-shot Entity Linking"
        assert enhancement.phase == EnhancementPhase.PHASE_3

    def test_advanced_caching_strategies_enhancement(self):
        """Test Advanced Caching Strategies enhancement."""
        enhancement = FutureEnhancements.get_enhancement_by_id("enh_009")
        assert enhancement.title == "Advanced Caching Strategies"
        assert enhancement.phase == EnhancementPhase.PHASE_4


class TestEnhancementRoadmap:
    """Tests for enhancement roadmap."""

    def test_roadmap_phases_coverage(self):
        """Test roadmap covers all phases."""
        roadmap = FutureEnhancements.get_enhancement_roadmap()
        assert len(roadmap) == 5

    def test_roadmap_phase_1_enhancements(self):
        """Test Phase 1 enhancements."""
        phase_1 = FutureEnhancements.get_enhancements_by_phase(EnhancementPhase.PHASE_1)
        assert len(phase_1) == 3
        titles = [e.title for e in phase_1]
        assert "Advanced NER Models" in titles
        assert "Real-time Entity Tracking" in titles
        assert "Entity Relationship Graphs" in titles

    def test_roadmap_phase_2_enhancements(self):
        """Test Phase 2 enhancements."""
        phase_2 = FutureEnhancements.get_enhancements_by_phase(EnhancementPhase.PHASE_2)
        assert len(phase_2) == 3
        titles = [e.title for e in phase_2]
        assert "Cross-lingual Entity Linking" in titles
        assert "Active Learning Pipeline" in titles
        assert "Federated Learning Support" in titles

    def test_roadmap_phase_3_enhancements(self):
        """Test Phase 3 enhancements."""
        phase_3 = FutureEnhancements.get_enhancements_by_phase(EnhancementPhase.PHASE_3)
        assert len(phase_3) == 2
        titles = [e.title for e in phase_3]
        assert "Explainability and Interpretability" in titles
        assert "Zero-shot Entity Linking" in titles

    def test_roadmap_phase_4_enhancements(self):
        """Test Phase 4 enhancements."""
        phase_4 = FutureEnhancements.get_enhancements_by_phase(EnhancementPhase.PHASE_4)
        assert len(phase_4) == 1
        assert phase_4[0].title == "Advanced Caching Strategies"


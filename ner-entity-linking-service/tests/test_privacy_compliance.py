"""Tests for privacy and compliance."""

import pytest
from src.compliance.privacy_manager import (
    PrivacyLevel,
    ComplianceFramework,
    PrivacyPolicy,
    PrivacyManager,
    ComplianceChecker,
    DataProcessingAgreement,
)


class TestPrivacyLevel:
    """Tests for PrivacyLevel enum."""

    def test_privacy_levels_defined(self):
        """Test privacy levels are defined."""
        assert PrivacyLevel.PUBLIC.value == "public"
        assert PrivacyLevel.INTERNAL.value == "internal"
        assert PrivacyLevel.CONFIDENTIAL.value == "confidential"
        assert PrivacyLevel.RESTRICTED.value == "restricted"


class TestPrivacyPolicy:
    """Tests for PrivacyPolicy."""

    def test_create_privacy_policy(self):
        """Test creating privacy policy."""
        policy = PrivacyPolicy(
            entity_type="PERSON",
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            retention_days=90,
            allow_export=False,
            allow_sharing=False,
            requires_consent=True,
            anonymization_required=True,
        )
        assert policy.entity_type == "PERSON"
        assert policy.privacy_level == PrivacyLevel.CONFIDENTIAL
        assert policy.retention_days == 90


class TestPrivacyManager:
    """Tests for privacy manager."""

    def test_get_privacy_policy_person(self):
        """Test getting privacy policy for PERSON."""
        policy = PrivacyManager.get_privacy_policy("PERSON")
        assert policy.entity_type == "PERSON"
        assert policy.privacy_level == PrivacyLevel.CONFIDENTIAL

    def test_get_privacy_policy_organization(self):
        """Test getting privacy policy for ORGANIZATION."""
        policy = PrivacyManager.get_privacy_policy("ORGANIZATION")
        assert policy.entity_type == "ORGANIZATION"
        assert policy.privacy_level == PrivacyLevel.INTERNAL

    def test_get_privacy_policy_location(self):
        """Test getting privacy policy for LOCATION."""
        policy = PrivacyManager.get_privacy_policy("LOCATION")
        assert policy.entity_type == "LOCATION"
        assert policy.privacy_level == PrivacyLevel.PUBLIC

    def test_can_export_person(self):
        """Test export permission for PERSON."""
        assert not PrivacyManager.can_export("PERSON")

    def test_can_export_organization(self):
        """Test export permission for ORGANIZATION."""
        assert PrivacyManager.can_export("ORGANIZATION")

    def test_can_share_person(self):
        """Test sharing permission for PERSON."""
        assert not PrivacyManager.can_share("PERSON")

    def test_can_share_organization(self):
        """Test sharing permission for ORGANIZATION."""
        assert PrivacyManager.can_share("ORGANIZATION")

    def test_requires_consent_person(self):
        """Test consent requirement for PERSON."""
        assert PrivacyManager.requires_consent("PERSON")

    def test_requires_consent_organization(self):
        """Test consent requirement for ORGANIZATION."""
        assert not PrivacyManager.requires_consent("ORGANIZATION")

    def test_requires_anonymization_person(self):
        """Test anonymization requirement for PERSON."""
        assert PrivacyManager.requires_anonymization("PERSON")

    def test_requires_anonymization_organization(self):
        """Test anonymization requirement for ORGANIZATION."""
        assert not PrivacyManager.requires_anonymization("ORGANIZATION")

    def test_anonymize_entity_person(self):
        """Test anonymizing PERSON entity."""
        anonymized = PrivacyManager.anonymize_entity("John Smith", "PERSON")
        assert anonymized.startswith("PERSON_")
        assert len(anonymized) > len("PERSON_")

    def test_anonymize_entity_organization(self):
        """Test anonymizing ORGANIZATION entity."""
        anonymized = PrivacyManager.anonymize_entity("Microsoft", "ORGANIZATION")
        # ORGANIZATION doesn't require anonymization
        assert anonymized == "Microsoft"

    def test_anonymize_entity_consistent(self):
        """Test anonymization is consistent."""
        anonymized1 = PrivacyManager.anonymize_entity("John Smith", "PERSON")
        anonymized2 = PrivacyManager.anonymize_entity("John Smith", "PERSON")
        assert anonymized1 == anonymized2

    def test_get_retention_days_person(self):
        """Test retention days for PERSON."""
        retention = PrivacyManager.get_retention_days("PERSON")
        assert retention == 90

    def test_get_retention_days_location(self):
        """Test retention days for LOCATION."""
        retention = PrivacyManager.get_retention_days("LOCATION")
        assert retention is None

    def test_get_privacy_level(self):
        """Test getting privacy level."""
        level = PrivacyManager.get_privacy_level("PERSON")
        assert level == PrivacyLevel.CONFIDENTIAL


class TestComplianceChecker:
    """Tests for compliance checker."""

    def test_check_gdpr_compliance_person(self):
        """Test GDPR compliance for PERSON."""
        checks = ComplianceChecker.check_gdpr_compliance("PERSON")
        assert isinstance(checks, dict)
        assert "data_minimization" in checks
        assert "purpose_limitation" in checks

    def test_check_ccpa_compliance_person(self):
        """Test CCPA compliance for PERSON."""
        checks = ComplianceChecker.check_ccpa_compliance("PERSON")
        assert isinstance(checks, dict)
        assert "right_to_know" in checks
        assert "right_to_delete" in checks

    def test_is_gdpr_compliant_person(self):
        """Test GDPR compliance status for PERSON."""
        compliant = ComplianceChecker.is_gdpr_compliant("PERSON")
        assert isinstance(compliant, bool)

    def test_is_ccpa_compliant_person(self):
        """Test CCPA compliance status for PERSON."""
        compliant = ComplianceChecker.is_ccpa_compliant("PERSON")
        assert isinstance(compliant, bool)

    def test_get_compliance_report(self):
        """Test getting compliance report."""
        report = ComplianceChecker.get_compliance_report("PERSON")
        assert report["entity_type"] == "PERSON"
        assert "gdpr" in report
        assert "ccpa" in report
        assert "privacy_level" in report
        assert "retention_days" in report

    def test_compliance_report_structure(self):
        """Test compliance report structure."""
        report = ComplianceChecker.get_compliance_report("PERSON")
        assert "compliant" in report["gdpr"]
        assert "checks" in report["gdpr"]
        assert "compliant" in report["ccpa"]
        assert "checks" in report["ccpa"]


class TestDataProcessingAgreement:
    """Tests for data processing agreement."""

    def test_get_dpa_requirements(self):
        """Test getting DPA requirements."""
        requirements = DataProcessingAgreement.get_dpa_requirements("PERSON")
        assert "data_controller" in requirements
        assert "data_processor" in requirements
        assert "processing_purpose" in requirements
        assert "data_categories" in requirements
        assert "retention_period" in requirements
        assert "security_measures" in requirements
        assert "sub_processors" in requirements

    def test_get_dpa_requirements_person(self):
        """Test DPA requirements for PERSON."""
        requirements = DataProcessingAgreement.get_dpa_requirements("PERSON")
        assert requirements["data_categories"] == "PERSON"
        assert requirements["retention_period"] == "90"

    def test_get_dpa_requirements_location(self):
        """Test DPA requirements for LOCATION."""
        requirements = DataProcessingAgreement.get_dpa_requirements("LOCATION")
        assert requirements["retention_period"] == "Indefinite"

    def test_get_data_subject_rights(self):
        """Test getting data subject rights."""
        rights = DataProcessingAgreement.get_data_subject_rights("PERSON")
        assert isinstance(rights, list)
        assert len(rights) > 0
        assert "Right to access" in rights
        assert "Right to erasure" in rights

    def test_get_data_subject_rights_person(self):
        """Test data subject rights for PERSON."""
        rights = DataProcessingAgreement.get_data_subject_rights("PERSON")
        # PERSON requires consent, so should have right to withdraw
        assert "Right to withdraw consent" in rights

    def test_get_data_subject_rights_organization(self):
        """Test data subject rights for ORGANIZATION."""
        rights = DataProcessingAgreement.get_data_subject_rights("ORGANIZATION")
        # ORGANIZATION doesn't require consent
        assert "Right to withdraw consent" not in rights


class TestPrivacyComplianceIntegration:
    """Integration tests for privacy and compliance."""

    def test_full_privacy_workflow_person(self):
        """Test full privacy workflow for PERSON."""
        entity_type = "PERSON"

        # Check privacy policy
        policy = PrivacyManager.get_privacy_policy(entity_type)
        assert policy.requires_consent

        # Check permissions
        assert not PrivacyManager.can_export(entity_type)
        assert not PrivacyManager.can_share(entity_type)

        # Check anonymization
        anonymized = PrivacyManager.anonymize_entity("John Smith", entity_type)
        assert anonymized.startswith("PERSON_")

        # Check compliance
        gdpr_compliant = ComplianceChecker.is_gdpr_compliant(entity_type)
        assert isinstance(gdpr_compliant, bool)

        # Get compliance report
        report = ComplianceChecker.get_compliance_report(entity_type)
        assert report["entity_type"] == entity_type

    def test_full_privacy_workflow_organization(self):
        """Test full privacy workflow for ORGANIZATION."""
        entity_type = "ORGANIZATION"

        # Check privacy policy
        policy = PrivacyManager.get_privacy_policy(entity_type)
        assert not policy.requires_consent

        # Check permissions
        assert PrivacyManager.can_export(entity_type)
        assert PrivacyManager.can_share(entity_type)

        # Check anonymization (not required)
        anonymized = PrivacyManager.anonymize_entity("Microsoft", entity_type)
        assert anonymized == "Microsoft"

        # Get DPA requirements
        requirements = DataProcessingAgreement.get_dpa_requirements(entity_type)
        assert requirements["data_categories"] == entity_type


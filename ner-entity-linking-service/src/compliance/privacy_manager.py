"""Privacy and compliance management."""

import logging
import hashlib
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PrivacyLevel(str, Enum):
    """Privacy levels for entities."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ComplianceFramework(str, Enum):
    """Compliance frameworks."""

    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"


@dataclass
class PrivacyPolicy:
    """Privacy policy for entity processing."""

    entity_type: str
    privacy_level: PrivacyLevel
    retention_days: int
    allow_export: bool
    allow_sharing: bool
    requires_consent: bool
    anonymization_required: bool


class PrivacyManager:
    """Manages privacy and compliance."""

    # Default privacy policies
    DEFAULT_POLICIES = {
        "PERSON": PrivacyPolicy(
            entity_type="PERSON",
            privacy_level=PrivacyLevel.CONFIDENTIAL,
            retention_days=90,
            allow_export=False,
            allow_sharing=False,
            requires_consent=True,
            anonymization_required=True,
        ),
        "ORGANIZATION": PrivacyPolicy(
            entity_type="ORGANIZATION",
            privacy_level=PrivacyLevel.INTERNAL,
            retention_days=365,
            allow_export=True,
            allow_sharing=True,
            requires_consent=False,
            anonymization_required=False,
        ),
        "LOCATION": PrivacyPolicy(
            entity_type="LOCATION",
            privacy_level=PrivacyLevel.PUBLIC,
            retention_days=None,  # No retention limit
            allow_export=True,
            allow_sharing=True,
            requires_consent=False,
            anonymization_required=False,
        ),
        "GPE": PrivacyPolicy(
            entity_type="GPE",
            privacy_level=PrivacyLevel.PUBLIC,
            retention_days=None,
            allow_export=True,
            allow_sharing=True,
            requires_consent=False,
            anonymization_required=False,
        ),
    }

    @staticmethod
    def get_privacy_policy(entity_type: str) -> PrivacyPolicy:
        """Get privacy policy for entity type.

        Args:
            entity_type: Entity type

        Returns:
            PrivacyPolicy
        """
        return PrivacyManager.DEFAULT_POLICIES.get(
            entity_type,
            PrivacyManager.DEFAULT_POLICIES["ORGANIZATION"],
        )

    @staticmethod
    def can_export(entity_type: str) -> bool:
        """Check if entity can be exported.

        Args:
            entity_type: Entity type

        Returns:
            True if can export
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.allow_export

    @staticmethod
    def can_share(entity_type: str) -> bool:
        """Check if entity can be shared.

        Args:
            entity_type: Entity type

        Returns:
            True if can share
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.allow_sharing

    @staticmethod
    def requires_consent(entity_type: str) -> bool:
        """Check if entity processing requires consent.

        Args:
            entity_type: Entity type

        Returns:
            True if consent required
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.requires_consent

    @staticmethod
    def requires_anonymization(entity_type: str) -> bool:
        """Check if entity requires anonymization.

        Args:
            entity_type: Entity type

        Returns:
            True if anonymization required
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.anonymization_required

    @staticmethod
    def anonymize_entity(entity_text: str, entity_type: str) -> str:
        """Anonymize entity text.

        Args:
            entity_text: Entity text
            entity_type: Entity type

        Returns:
            Anonymized entity text
        """
        if not PrivacyManager.requires_anonymization(entity_type):
            return entity_text

        # Create hash-based anonymization
        entity_hash = hashlib.sha256(entity_text.encode()).hexdigest()[:8]

        if entity_type == "PERSON":
            return f"PERSON_{entity_hash}"
        elif entity_type == "ORGANIZATION":
            return f"ORG_{entity_hash}"
        else:
            return f"ENTITY_{entity_hash}"

    @staticmethod
    def get_retention_days(entity_type: str) -> Optional[int]:
        """Get data retention period in days.

        Args:
            entity_type: Entity type

        Returns:
            Retention days or None for indefinite
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.retention_days

    @staticmethod
    def get_privacy_level(entity_type: str) -> PrivacyLevel:
        """Get privacy level for entity type.

        Args:
            entity_type: Entity type

        Returns:
            PrivacyLevel
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)
        return policy.privacy_level


class ComplianceChecker:
    """Checks compliance with regulations."""

    # GDPR requirements
    GDPR_REQUIREMENTS = {
        "data_minimization": True,
        "purpose_limitation": True,
        "storage_limitation": True,
        "integrity_confidentiality": True,
        "accountability": True,
    }

    # CCPA requirements
    CCPA_REQUIREMENTS = {
        "right_to_know": True,
        "right_to_delete": True,
        "right_to_opt_out": True,
        "non_discrimination": True,
    }

    @staticmethod
    def check_gdpr_compliance(entity_type: str) -> Dict[str, bool]:
        """Check GDPR compliance for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Dictionary of compliance checks
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)

        return {
            "data_minimization": policy.privacy_level != PrivacyLevel.PUBLIC,
            "purpose_limitation": policy.requires_consent,
            "storage_limitation": policy.retention_days is not None,
            "integrity_confidentiality": policy.anonymization_required,
            "accountability": True,
        }

    @staticmethod
    def check_ccpa_compliance(entity_type: str) -> Dict[str, bool]:
        """Check CCPA compliance for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Dictionary of compliance checks
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)

        return {
            "right_to_know": True,
            "right_to_delete": policy.retention_days is not None,
            "right_to_opt_out": policy.requires_consent,
            "non_discrimination": True,
        }

    @staticmethod
    def is_gdpr_compliant(entity_type: str) -> bool:
        """Check if entity processing is GDPR compliant.

        Args:
            entity_type: Entity type

        Returns:
            True if compliant
        """
        checks = ComplianceChecker.check_gdpr_compliance(entity_type)
        return all(checks.values())

    @staticmethod
    def is_ccpa_compliant(entity_type: str) -> bool:
        """Check if entity processing is CCPA compliant.

        Args:
            entity_type: Entity type

        Returns:
            True if compliant
        """
        checks = ComplianceChecker.check_ccpa_compliance(entity_type)
        return all(checks.values())

    @staticmethod
    def get_compliance_report(entity_type: str) -> Dict:
        """Get compliance report for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Compliance report
        """
        return {
            "entity_type": entity_type,
            "gdpr": {
                "compliant": ComplianceChecker.is_gdpr_compliant(entity_type),
                "checks": ComplianceChecker.check_gdpr_compliance(entity_type),
            },
            "ccpa": {
                "compliant": ComplianceChecker.is_ccpa_compliant(entity_type),
                "checks": ComplianceChecker.check_ccpa_compliance(entity_type),
            },
            "privacy_level": PrivacyManager.get_privacy_level(entity_type).value,
            "retention_days": PrivacyManager.get_retention_days(entity_type),
        }


class DataProcessingAgreement:
    """Data processing agreement tracking."""

    @staticmethod
    def get_dpa_requirements(entity_type: str) -> Dict[str, str]:
        """Get DPA requirements for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Dictionary of DPA requirements
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)

        requirements = {
            "data_controller": "Sentiment Analyzer Service",
            "data_processor": "NER Entity Linking Service",
            "processing_purpose": "Named entity extraction and linking",
            "data_categories": entity_type,
            "retention_period": str(policy.retention_days) if policy.retention_days else "Indefinite",
            "security_measures": "Encryption, access control, audit logging",
            "sub_processors": "Wikidata, DBpedia, OpenSanctions",
        }

        return requirements

    @staticmethod
    def get_data_subject_rights(entity_type: str) -> List[str]:
        """Get data subject rights for entity type.

        Args:
            entity_type: Entity type

        Returns:
            List of rights
        """
        policy = PrivacyManager.get_privacy_policy(entity_type)

        rights = [
            "Right to access",
            "Right to rectification",
            "Right to erasure",
            "Right to restrict processing",
            "Right to data portability",
            "Right to object",
        ]

        if policy.requires_consent:
            rights.append("Right to withdraw consent")

        return rights


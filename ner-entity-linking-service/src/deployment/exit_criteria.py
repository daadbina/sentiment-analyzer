"""Exit criteria validation for deployment."""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class CriteriaStatus(str, Enum):
    """Status of exit criteria."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_CHECKED = "not_checked"


@dataclass
class CriteriaResult:
    """Result of a single exit criteria check."""

    name: str
    status: CriteriaStatus
    value: Any = None
    threshold: Any = None
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class ExitCriteria:
    """Exit criteria for deployment."""

    # Thresholds
    MIN_UNIT_TEST_COVERAGE = 0.90  # 90%
    MIN_INTEGRATION_TEST_COVERAGE = 0.80  # 80%
    MIN_THROUGHPUT = 200  # articles/min
    MAX_AVG_LATENCY = 5.0  # seconds
    MAX_P95_LATENCY = 8.0  # seconds
    MIN_AVAILABILITY = 0.999  # 99.9%
    MIN_CODE_QUALITY_SCORE = 8.0  # out of 10
    MIN_SECURITY_SCORE = 9.0  # out of 10

    @staticmethod
    def check_unit_test_coverage(coverage: float) -> CriteriaResult:
        """Check unit test coverage.

        Args:
            coverage: Test coverage percentage (0-1)

        Returns:
            CriteriaResult
        """
        passed = coverage >= ExitCriteria.MIN_UNIT_TEST_COVERAGE
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Unit test coverage {coverage:.1%} meets requirement"
            if passed
            else f"Unit test coverage {coverage:.1%} below {ExitCriteria.MIN_UNIT_TEST_COVERAGE:.1%}"
        )
        return CriteriaResult(
            name="Unit Test Coverage",
            status=status,
            value=coverage,
            threshold=ExitCriteria.MIN_UNIT_TEST_COVERAGE,
            message=message,
        )

    @staticmethod
    def check_integration_test_coverage(coverage: float) -> CriteriaResult:
        """Check integration test coverage.

        Args:
            coverage: Test coverage percentage (0-1)

        Returns:
            CriteriaResult
        """
        passed = coverage >= ExitCriteria.MIN_INTEGRATION_TEST_COVERAGE
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Integration test coverage {coverage:.1%} meets requirement"
            if passed
            else f"Integration test coverage {coverage:.1%} below {ExitCriteria.MIN_INTEGRATION_TEST_COVERAGE:.1%}"
        )
        return CriteriaResult(
            name="Integration Test Coverage",
            status=status,
            value=coverage,
            threshold=ExitCriteria.MIN_INTEGRATION_TEST_COVERAGE,
            message=message,
        )

    @staticmethod
    def check_throughput(throughput: float) -> CriteriaResult:
        """Check throughput performance.

        Args:
            throughput: Throughput in articles/min

        Returns:
            CriteriaResult
        """
        passed = throughput >= ExitCriteria.MIN_THROUGHPUT
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Throughput {throughput:.0f} articles/min meets requirement"
            if passed
            else f"Throughput {throughput:.0f} articles/min below {ExitCriteria.MIN_THROUGHPUT} articles/min"
        )
        return CriteriaResult(
            name="Throughput Performance",
            status=status,
            value=throughput,
            threshold=ExitCriteria.MIN_THROUGHPUT,
            message=message,
        )

    @staticmethod
    def check_avg_latency(latency: float) -> CriteriaResult:
        """Check average latency.

        Args:
            latency: Average latency in seconds

        Returns:
            CriteriaResult
        """
        passed = latency <= ExitCriteria.MAX_AVG_LATENCY
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Average latency {latency:.2f}s meets requirement"
            if passed
            else f"Average latency {latency:.2f}s exceeds {ExitCriteria.MAX_AVG_LATENCY}s"
        )
        return CriteriaResult(
            name="Average Latency",
            status=status,
            value=latency,
            threshold=ExitCriteria.MAX_AVG_LATENCY,
            message=message,
        )

    @staticmethod
    def check_p95_latency(latency: float) -> CriteriaResult:
        """Check P95 latency.

        Args:
            latency: P95 latency in seconds

        Returns:
            CriteriaResult
        """
        passed = latency <= ExitCriteria.MAX_P95_LATENCY
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"P95 latency {latency:.2f}s meets requirement"
            if passed
            else f"P95 latency {latency:.2f}s exceeds {ExitCriteria.MAX_P95_LATENCY}s"
        )
        return CriteriaResult(
            name="P95 Latency",
            status=status,
            value=latency,
            threshold=ExitCriteria.MAX_P95_LATENCY,
            message=message,
        )

    @staticmethod
    def check_availability(availability: float) -> CriteriaResult:
        """Check availability.

        Args:
            availability: Availability percentage (0-1)

        Returns:
            CriteriaResult
        """
        passed = availability >= ExitCriteria.MIN_AVAILABILITY
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Availability {availability:.3%} meets requirement"
            if passed
            else f"Availability {availability:.3%} below {ExitCriteria.MIN_AVAILABILITY:.3%}"
        )
        return CriteriaResult(
            name="Availability",
            status=status,
            value=availability,
            threshold=ExitCriteria.MIN_AVAILABILITY,
            message=message,
        )

    @staticmethod
    def check_code_quality(score: float) -> CriteriaResult:
        """Check code quality score.

        Args:
            score: Code quality score (0-10)

        Returns:
            CriteriaResult
        """
        passed = score >= ExitCriteria.MIN_CODE_QUALITY_SCORE
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Code quality score {score:.1f}/10 meets requirement"
            if passed
            else f"Code quality score {score:.1f}/10 below {ExitCriteria.MIN_CODE_QUALITY_SCORE}/10"
        )
        return CriteriaResult(
            name="Code Quality",
            status=status,
            value=score,
            threshold=ExitCriteria.MIN_CODE_QUALITY_SCORE,
            message=message,
        )

    @staticmethod
    def check_security_score(score: float) -> CriteriaResult:
        """Check security score.

        Args:
            score: Security score (0-10)

        Returns:
            CriteriaResult
        """
        passed = score >= ExitCriteria.MIN_SECURITY_SCORE
        status = CriteriaStatus.PASSED if passed else CriteriaStatus.FAILED
        message = (
            f"Security score {score:.1f}/10 meets requirement"
            if passed
            else f"Security score {score:.1f}/10 below {ExitCriteria.MIN_SECURITY_SCORE}/10"
        )
        return CriteriaResult(
            name="Security Score",
            status=status,
            value=score,
            threshold=ExitCriteria.MIN_SECURITY_SCORE,
            message=message,
        )

    @staticmethod
    def check_documentation(has_api_docs: bool, has_runbook: bool, has_deployment: bool) -> CriteriaResult:
        """Check documentation completeness.

        Args:
            has_api_docs: Has API documentation
            has_runbook: Has operational runbook
            has_deployment: Has deployment guide

        Returns:
            CriteriaResult
        """
        all_present = has_api_docs and has_runbook and has_deployment
        status = CriteriaStatus.PASSED if all_present else CriteriaStatus.FAILED
        missing = []
        if not has_api_docs:
            missing.append("API documentation")
        if not has_runbook:
            missing.append("operational runbook")
        if not has_deployment:
            missing.append("deployment guide")

        message = (
            "All documentation present"
            if all_present
            else f"Missing: {', '.join(missing)}"
        )
        return CriteriaResult(
            name="Documentation",
            status=status,
            value={"api_docs": has_api_docs, "runbook": has_runbook, "deployment": has_deployment},
            message=message,
        )

    @staticmethod
    def check_kubernetes_readiness(
        has_deployment: bool,
        has_service: bool,
        has_hpa: bool,
        has_configmap: bool,
    ) -> CriteriaResult:
        """Check Kubernetes readiness.

        Args:
            has_deployment: Has Kubernetes deployment
            has_service: Has Kubernetes service
            has_hpa: Has horizontal pod autoscaler
            has_configmap: Has ConfigMap

        Returns:
            CriteriaResult
        """
        all_present = has_deployment and has_service and has_hpa and has_configmap
        status = CriteriaStatus.PASSED if all_present else CriteriaStatus.FAILED
        missing = []
        if not has_deployment:
            missing.append("deployment")
        if not has_service:
            missing.append("service")
        if not has_hpa:
            missing.append("HPA")
        if not has_configmap:
            missing.append("ConfigMap")

        message = (
            "All Kubernetes resources present"
            if all_present
            else f"Missing: {', '.join(missing)}"
        )
        return CriteriaResult(
            name="Kubernetes Readiness",
            status=status,
            value={
                "deployment": has_deployment,
                "service": has_service,
                "hpa": has_hpa,
                "configmap": has_configmap,
            },
            message=message,
        )


class DeploymentReadinessReport:
    """Deployment readiness report."""

    def __init__(self):
        """Initialize report."""
        self.results: List[CriteriaResult] = []
        self.timestamp = datetime.utcnow().isoformat()

    def add_result(self, result: CriteriaResult) -> None:
        """Add result to report.

        Args:
            result: CriteriaResult
        """
        self.results.append(result)

    def is_ready_for_deployment(self) -> bool:
        """Check if ready for deployment.

        Returns:
            True if all criteria passed
        """
        return all(r.status == CriteriaStatus.PASSED for r in self.results)

    def get_summary(self) -> Dict[str, Any]:
        """Get report summary.

        Returns:
            Summary dictionary
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == CriteriaStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CriteriaStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == CriteriaStatus.WARNING)

        return {
            "timestamp": self.timestamp,
            "total_criteria": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "ready_for_deployment": self.is_ready_for_deployment(),
            "pass_rate": passed / total if total > 0 else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
        }


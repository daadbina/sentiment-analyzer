"""Tests for exit criteria validation."""

import pytest
from src.deployment.exit_criteria import (
    CriteriaStatus,
    CriteriaResult,
    ExitCriteria,
    DeploymentReadinessReport,
)


class TestCriteriaResult:
    """Tests for CriteriaResult."""

    def test_create_criteria_result(self):
        """Test creating criteria result."""
        result = CriteriaResult(
            name="Test Criteria",
            status=CriteriaStatus.PASSED,
            value=0.95,
            threshold=0.90,
            message="Test passed",
        )
        assert result.name == "Test Criteria"
        assert result.status == CriteriaStatus.PASSED

    def test_criteria_result_to_dict(self):
        """Test converting criteria result to dictionary."""
        result = CriteriaResult(
            name="Test Criteria",
            status=CriteriaStatus.PASSED,
            value=0.95,
        )
        result_dict = result.to_dict()
        assert result_dict["name"] == "Test Criteria"
        assert result_dict["status"] == "passed"


class TestExitCriteria:
    """Tests for exit criteria checks."""

    def test_check_unit_test_coverage_passed(self):
        """Test unit test coverage check - passed."""
        result = ExitCriteria.check_unit_test_coverage(0.95)
        assert result.status == CriteriaStatus.PASSED
        assert result.value == 0.95

    def test_check_unit_test_coverage_failed(self):
        """Test unit test coverage check - failed."""
        result = ExitCriteria.check_unit_test_coverage(0.85)
        assert result.status == CriteriaStatus.FAILED
        assert result.value == 0.85

    def test_check_integration_test_coverage_passed(self):
        """Test integration test coverage check - passed."""
        result = ExitCriteria.check_integration_test_coverage(0.85)
        assert result.status == CriteriaStatus.PASSED

    def test_check_integration_test_coverage_failed(self):
        """Test integration test coverage check - failed."""
        result = ExitCriteria.check_integration_test_coverage(0.70)
        assert result.status == CriteriaStatus.FAILED

    def test_check_throughput_passed(self):
        """Test throughput check - passed."""
        result = ExitCriteria.check_throughput(250)
        assert result.status == CriteriaStatus.PASSED
        assert result.value == 250

    def test_check_throughput_failed(self):
        """Test throughput check - failed."""
        result = ExitCriteria.check_throughput(150)
        assert result.status == CriteriaStatus.FAILED

    def test_check_avg_latency_passed(self):
        """Test average latency check - passed."""
        result = ExitCriteria.check_avg_latency(4.5)
        assert result.status == CriteriaStatus.PASSED

    def test_check_avg_latency_failed(self):
        """Test average latency check - failed."""
        result = ExitCriteria.check_avg_latency(6.0)
        assert result.status == CriteriaStatus.FAILED

    def test_check_p95_latency_passed(self):
        """Test P95 latency check - passed."""
        result = ExitCriteria.check_p95_latency(7.5)
        assert result.status == CriteriaStatus.PASSED

    def test_check_p95_latency_failed(self):
        """Test P95 latency check - failed."""
        result = ExitCriteria.check_p95_latency(9.0)
        assert result.status == CriteriaStatus.FAILED

    def test_check_availability_passed(self):
        """Test availability check - passed."""
        result = ExitCriteria.check_availability(0.9995)
        assert result.status == CriteriaStatus.PASSED

    def test_check_availability_failed(self):
        """Test availability check - failed."""
        result = ExitCriteria.check_availability(0.998)
        assert result.status == CriteriaStatus.FAILED

    def test_check_code_quality_passed(self):
        """Test code quality check - passed."""
        result = ExitCriteria.check_code_quality(8.5)
        assert result.status == CriteriaStatus.PASSED

    def test_check_code_quality_failed(self):
        """Test code quality check - failed."""
        result = ExitCriteria.check_code_quality(7.5)
        assert result.status == CriteriaStatus.FAILED

    def test_check_security_score_passed(self):
        """Test security score check - passed."""
        result = ExitCriteria.check_security_score(9.5)
        assert result.status == CriteriaStatus.PASSED

    def test_check_security_score_failed(self):
        """Test security score check - failed."""
        result = ExitCriteria.check_security_score(8.5)
        assert result.status == CriteriaStatus.FAILED

    def test_check_documentation_all_present(self):
        """Test documentation check - all present."""
        result = ExitCriteria.check_documentation(
            has_api_docs=True,
            has_runbook=True,
            has_deployment=True,
        )
        assert result.status == CriteriaStatus.PASSED

    def test_check_documentation_missing_api_docs(self):
        """Test documentation check - missing API docs."""
        result = ExitCriteria.check_documentation(
            has_api_docs=False,
            has_runbook=True,
            has_deployment=True,
        )
        assert result.status == CriteriaStatus.FAILED
        assert "API documentation" in result.message

    def test_check_kubernetes_readiness_all_present(self):
        """Test Kubernetes readiness check - all present."""
        result = ExitCriteria.check_kubernetes_readiness(
            has_deployment=True,
            has_service=True,
            has_hpa=True,
            has_configmap=True,
        )
        assert result.status == CriteriaStatus.PASSED

    def test_check_kubernetes_readiness_missing_hpa(self):
        """Test Kubernetes readiness check - missing HPA."""
        result = ExitCriteria.check_kubernetes_readiness(
            has_deployment=True,
            has_service=True,
            has_hpa=False,
            has_configmap=True,
        )
        assert result.status == CriteriaStatus.FAILED
        assert "HPA" in result.message


class TestDeploymentReadinessReport:
    """Tests for deployment readiness report."""

    def test_create_report(self):
        """Test creating report."""
        report = DeploymentReadinessReport()
        assert len(report.results) == 0

    def test_add_result_to_report(self):
        """Test adding result to report."""
        report = DeploymentReadinessReport()
        result = CriteriaResult(
            name="Test",
            status=CriteriaStatus.PASSED,
        )
        report.add_result(result)
        assert len(report.results) == 1

    def test_is_ready_for_deployment_all_passed(self):
        """Test deployment readiness - all passed."""
        report = DeploymentReadinessReport()
        report.add_result(
            CriteriaResult(name="Test1", status=CriteriaStatus.PASSED)
        )
        report.add_result(
            CriteriaResult(name="Test2", status=CriteriaStatus.PASSED)
        )
        assert report.is_ready_for_deployment()

    def test_is_ready_for_deployment_one_failed(self):
        """Test deployment readiness - one failed."""
        report = DeploymentReadinessReport()
        report.add_result(
            CriteriaResult(name="Test1", status=CriteriaStatus.PASSED)
        )
        report.add_result(
            CriteriaResult(name="Test2", status=CriteriaStatus.FAILED)
        )
        assert not report.is_ready_for_deployment()

    def test_get_summary(self):
        """Test getting report summary."""
        report = DeploymentReadinessReport()
        report.add_result(
            CriteriaResult(name="Test1", status=CriteriaStatus.PASSED)
        )
        report.add_result(
            CriteriaResult(name="Test2", status=CriteriaStatus.PASSED)
        )
        report.add_result(
            CriteriaResult(name="Test3", status=CriteriaStatus.FAILED)
        )

        summary = report.get_summary()
        assert summary["total_criteria"] == 3
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 2 / 3

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = DeploymentReadinessReport()
        report.add_result(
            CriteriaResult(name="Test", status=CriteriaStatus.PASSED)
        )
        report_dict = report.to_dict()
        assert "summary" in report_dict
        assert "results" in report_dict


class TestDeploymentReadinessWorkflow:
    """Integration tests for deployment readiness workflow."""

    def test_full_deployment_readiness_check(self):
        """Test full deployment readiness check."""
        report = DeploymentReadinessReport()

        # Add all criteria checks
        report.add_result(ExitCriteria.check_unit_test_coverage(0.95))
        report.add_result(ExitCriteria.check_integration_test_coverage(0.85))
        report.add_result(ExitCriteria.check_throughput(250))
        report.add_result(ExitCriteria.check_avg_latency(4.5))
        report.add_result(ExitCriteria.check_p95_latency(7.5))
        report.add_result(ExitCriteria.check_availability(0.9995))
        report.add_result(ExitCriteria.check_code_quality(8.5))
        report.add_result(ExitCriteria.check_security_score(9.5))
        report.add_result(
            ExitCriteria.check_documentation(
                has_api_docs=True,
                has_runbook=True,
                has_deployment=True,
            )
        )
        report.add_result(
            ExitCriteria.check_kubernetes_readiness(
                has_deployment=True,
                has_service=True,
                has_hpa=True,
                has_configmap=True,
            )
        )

        # Check readiness
        assert report.is_ready_for_deployment()
        summary = report.get_summary()
        assert summary["passed"] == 10
        assert summary["failed"] == 0

    def test_deployment_readiness_with_failures(self):
        """Test deployment readiness with failures."""
        report = DeploymentReadinessReport()

        # Add criteria with some failures
        report.add_result(ExitCriteria.check_unit_test_coverage(0.85))  # FAILED
        report.add_result(ExitCriteria.check_throughput(150))  # FAILED
        report.add_result(ExitCriteria.check_avg_latency(4.5))  # PASSED

        # Check readiness
        assert not report.is_ready_for_deployment()
        summary = report.get_summary()
        assert summary["failed"] == 2
        assert summary["passed"] == 1


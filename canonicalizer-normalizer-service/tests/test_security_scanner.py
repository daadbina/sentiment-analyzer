"""Tests for security scanner."""

import pytest
from src.security.security_scanner import (
    SecurityScanner,
    SecurityIssue,
    SeverityLevel,
)


class TestSecurityScanner:
    """Test security scanner functionality."""

    def test_scanner_initialization(self):
        """Test initializing security scanner."""
        scanner = SecurityScanner()

        assert scanner.issues == []
        assert len(scanner.patterns) > 0

    def test_scan_hardcoded_secrets(self):
        """Test scanning for hardcoded secrets."""
        scanner = SecurityScanner()
        code = 'password = "mysecretpassword"'

        issues = scanner.scan_code(code)

        assert len(issues) > 0
        assert any(issue.severity == SeverityLevel.CRITICAL for issue in issues)

    def test_scan_api_key(self):
        """Test scanning for hardcoded API keys."""
        scanner = SecurityScanner()
        code = 'api_key = "sk-1234567890abcdef"'

        issues = scanner.scan_code(code)

        assert len(issues) > 0

    def test_scan_debug_mode(self):
        """Test scanning for debug mode enabled."""
        scanner = SecurityScanner()
        code = "DEBUG = True"

        issues = scanner.scan_code(code)

        assert len(issues) > 0
        assert any(issue.severity == SeverityLevel.HIGH for issue in issues)

    def test_scan_insecure_random(self):
        """Test scanning for insecure random usage."""
        scanner = SecurityScanner()
        code = "random_value = random.random()"

        issues = scanner.scan_code(code)

        assert len(issues) > 0

    def test_scan_hardcoded_http_url(self):
        """Test scanning for hardcoded HTTP URLs."""
        scanner = SecurityScanner()
        code = 'url = "http://example.com/api"'

        issues = scanner.scan_code(code)

        assert len(issues) > 0

    def test_scan_dependencies(self):
        """Test scanning dependencies for vulnerabilities."""
        scanner = SecurityScanner()
        requirements = ["pyyaml==5.3", "requests==2.24.0", "django==3.0.0"]

        issues = scanner.scan_dependencies(requirements)

        assert len(issues) > 0
        assert all(issue.severity == SeverityLevel.HIGH for issue in issues)

    def test_scan_safe_dependencies(self):
        """Test scanning safe dependencies."""
        scanner = SecurityScanner()
        requirements = ["pyyaml==5.4", "requests==2.26.0", "django==3.2.0"]

        issues = scanner.scan_dependencies(requirements)

        # Should have no issues for safe versions
        assert len(issues) == 0

    def test_check_input_validation(self):
        """Test checking for input validation."""
        scanner = SecurityScanner()
        code = "user_input = request.args['user_id']"

        issues = scanner.check_input_validation(code)

        assert len(issues) > 0

    def test_check_authentication(self):
        """Test checking for authentication."""
        scanner = SecurityScanner()
        code = """
def get_user_data(request):
    user_id = request.args['id']
    return get_user(user_id)
"""

        issues = scanner.check_authentication(code)

        assert len(issues) > 0

    def test_check_weak_encryption(self):
        """Test checking for weak encryption."""
        scanner = SecurityScanner()
        code = "hash_value = md5(password)"

        issues = scanner.check_encryption(code)

        assert len(issues) > 0
        assert any(issue.severity == SeverityLevel.HIGH for issue in issues)

    def test_get_issues_by_severity(self):
        """Test filtering issues by severity."""
        scanner = SecurityScanner()
        code = 'password = "secret"'
        scanner.scan_code(code)

        critical_issues = scanner.get_issues_by_severity(SeverityLevel.CRITICAL)

        assert len(critical_issues) > 0

    def test_get_critical_issues(self):
        """Test getting critical issues."""
        scanner = SecurityScanner()
        code = 'password = "secret"'
        scanner.scan_code(code)

        critical_issues = scanner.get_critical_issues()

        assert len(critical_issues) > 0

    def test_get_high_issues(self):
        """Test getting high severity issues."""
        scanner = SecurityScanner()
        code = "DEBUG = True"
        scanner.scan_code(code)

        high_issues = scanner.get_high_issues()

        assert len(high_issues) > 0

    def test_generate_report(self):
        """Test generating security report."""
        scanner = SecurityScanner()
        code = 'password = "secret"\nDEBUG = True'
        scanner.scan_code(code)

        report = scanner.generate_report()

        assert "total_issues" in report
        assert "critical" in report
        assert "high" in report
        assert "issues" in report
        assert report["total_issues"] > 0

    def test_clear_issues(self):
        """Test clearing found issues."""
        scanner = SecurityScanner()
        code = 'password = "secret"'
        scanner.scan_code(code)

        assert len(scanner.issues) > 0

        scanner.clear_issues()

        assert len(scanner.issues) == 0

    def test_multiple_scans(self):
        """Test multiple scans accumulate issues."""
        scanner = SecurityScanner()

        code1 = 'password = "secret1"'
        code2 = 'api_key = "key123"'

        scanner.scan_code(code1)
        count_after_first = len(scanner.issues)

        scanner.scan_code(code2)
        count_after_second = len(scanner.issues)

        assert count_after_second > count_after_first

    def test_security_issue_creation(self):
        """Test creating security issue."""
        issue = SecurityIssue(
            issue_id="test_001",
            title="Test Issue",
            description="This is a test issue",
            severity=SeverityLevel.HIGH,
            file_path="test.py",
            line_number=10,
        )

        assert issue.issue_id == "test_001"
        assert issue.severity == SeverityLevel.HIGH
        assert issue.file_path == "test.py"

    def test_scan_with_file_path(self):
        """Test scanning with file path tracking."""
        scanner = SecurityScanner()
        code = 'password = "secret"'

        issues = scanner.scan_code(code, file_path="config.py")

        assert all(issue.file_path == "config.py" for issue in issues)

    def test_scan_with_line_numbers(self):
        """Test scanning with line number tracking."""
        scanner = SecurityScanner()
        code = """
line1
line2
password = "secret"
line4
"""

        issues = scanner.scan_code(code)

        assert len(issues) > 0
        assert all(issue.line_number is not None for issue in issues)

    def test_no_false_positives_on_safe_code(self):
        """Test no false positives on safe code."""
        scanner = SecurityScanner()
        code = """
def process_data(data):
    result = data.strip()
    return result
"""

        issues = scanner.scan_code(code)

        # Should have minimal or no issues
        assert len(issues) == 0

    def test_report_summary(self):
        """Test report summary statistics."""
        scanner = SecurityScanner()
        code = 'password = "secret"\nDEBUG = True\nrandom.random()'
        scanner.scan_code(code)

        report = scanner.generate_report()

        assert report["total_issues"] > 0
        assert report["critical"] >= 0
        assert report["high"] >= 0
        assert report["medium"] >= 0


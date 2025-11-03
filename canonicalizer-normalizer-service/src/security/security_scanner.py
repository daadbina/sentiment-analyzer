"""Security scanning and vulnerability detection."""

import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Severity levels for security issues."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SecurityIssue:
    """Security issue found during scanning."""

    issue_id: str
    title: str
    description: str
    severity: SeverityLevel
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    remediation: str = ""
    cve_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityScanner:
    """Security scanner for detecting vulnerabilities."""

    def __init__(self):
        self.issues: List[SecurityIssue] = []
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> Dict[str, Any]:
        """Initialize security patterns to scan for."""
        return {
            "hardcoded_secrets": {
                "patterns": [
                    r"password\s*=\s*['\"]([^'\"]+)['\"]",
                    r"api_key\s*=\s*['\"]([^'\"]+)['\"]",
                    r"secret\s*=\s*['\"]([^'\"]+)['\"]",
                    r"token\s*=\s*['\"]([^'\"]+)['\"]",
                ],
                "severity": SeverityLevel.CRITICAL,
            },
            "sql_injection": {
                "patterns": [
                    r"execute\s*\(\s*['\"].*\{.*\}.*['\"]",
                    r"query\s*\(\s*['\"].*\+.*['\"]",
                ],
                "severity": SeverityLevel.HIGH,
            },
            "insecure_random": {
                "patterns": [
                    r"random\.random\(\)",
                    r"random\.randint\(\)",
                ],
                "severity": SeverityLevel.MEDIUM,
            },
            "hardcoded_urls": {
                "patterns": [
                    r"http://(?!localhost)",
                ],
                "severity": SeverityLevel.MEDIUM,
            },
            "debug_mode": {
                "patterns": [
                    r"debug\s*=\s*True",
                    r"DEBUG\s*=\s*True",
                ],
                "severity": SeverityLevel.HIGH,
            },
        }

    def scan_code(self, code: str, file_path: str = "unknown") -> List[SecurityIssue]:
        """Scan code for security issues."""
        issues = []

        for pattern_name, pattern_config in self.patterns.items():
            for pattern in pattern_config["patterns"]:
                matches = re.finditer(pattern, code, re.IGNORECASE)

                for match in matches:
                    line_number = code[: match.start()].count("\n") + 1
                    issue = SecurityIssue(
                        issue_id=f"{pattern_name}_{hashlib.md5(match.group().encode()).hexdigest()[:8]}",
                        title=f"Potential {pattern_name.replace('_', ' ').title()}",
                        description=f"Found potential {pattern_name.replace('_', ' ')} vulnerability",
                        severity=pattern_config["severity"],
                        file_path=file_path,
                        line_number=line_number,
                        code_snippet=match.group(),
                    )
                    issues.append(issue)

        self.issues.extend(issues)
        return issues

    def scan_dependencies(self, requirements: List[str]) -> List[SecurityIssue]:
        """Scan dependencies for known vulnerabilities."""
        issues = []

        # Known vulnerable packages with version ranges (simplified)
        vulnerable_packages = {
            "pyyaml": {"max_safe_version": "5.4", "cve": "CVE-2020-14343"},
            "requests": {"max_safe_version": "2.25.0", "cve": "CVE-2020-28493"},
            "django": {"max_safe_version": "3.1.3", "cve": "CVE-2020-9402"},
        }

        for req in requirements:
            # Extract package name and version
            parts = req.split("==")
            package_name = parts[0].split(">=")[0].split("<")[0].lower()
            version = parts[1] if len(parts) > 1 else None

            if package_name in vulnerable_packages and version:
                vuln = vulnerable_packages[package_name]
                max_safe = vuln["max_safe_version"]

                # Simple version comparison (assumes semantic versioning)
                try:
                    version_parts = [int(x) for x in version.split(".")]
                    safe_parts = [int(x) for x in max_safe.split(".")]

                    if version_parts < safe_parts:
                        issue = SecurityIssue(
                            issue_id=f"vuln_{package_name}",
                            title=f"Vulnerable Package: {package_name}",
                            description=f"Package {package_name} version {version} has known vulnerabilities",
                            severity=SeverityLevel.HIGH,
                            cve_id=vuln.get("cve"),
                            remediation=f"Update {package_name} to {max_safe} or later",
                        )
                        issues.append(issue)
                except (ValueError, AttributeError):
                    # Skip if version parsing fails
                    pass

        self.issues.extend(issues)
        return issues

    def check_input_validation(self, code: str) -> List[SecurityIssue]:
        """Check for missing input validation."""
        issues = []

        # Check for user input without validation
        patterns = [
            (r"request\.args\[", "Missing validation on request.args"),
            (r"request\.form\[", "Missing validation on request.form"),
            (r"input\(", "Missing validation on user input"),
        ]

        for pattern, description in patterns:
            if re.search(pattern, code):
                issue = SecurityIssue(
                    issue_id=f"input_validation_{hashlib.md5(pattern.encode()).hexdigest()[:8]}",
                    title="Missing Input Validation",
                    description=description,
                    severity=SeverityLevel.HIGH,
                    remediation="Validate and sanitize all user input",
                )
                issues.append(issue)

        self.issues.extend(issues)
        return issues

    def check_authentication(self, code: str) -> List[SecurityIssue]:
        """Check for authentication issues."""
        issues = []

        # Check for missing authentication
        if "def " in code and "@auth" not in code and "@login_required" not in code:
            if re.search(r"def\s+\w+\s*\(.*request", code):
                issue = SecurityIssue(
                    issue_id="missing_auth",
                    title="Missing Authentication",
                    description="Function handles requests but lacks authentication",
                    severity=SeverityLevel.HIGH,
                    remediation="Add authentication decorator or check",
                )
                issues.append(issue)

        self.issues.extend(issues)
        return issues

    def check_encryption(self, code: str) -> List[SecurityIssue]:
        """Check for encryption issues."""
        issues = []

        # Check for weak encryption
        weak_patterns = [
            (r"md5\(", "MD5 is cryptographically broken"),
            (r"sha1\(", "SHA1 is cryptographically weak"),
            (r"DES\(", "DES is cryptographically weak"),
        ]

        for pattern, description in weak_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issue = SecurityIssue(
                    issue_id=f"weak_crypto_{hashlib.md5(pattern.encode()).hexdigest()[:8]}",
                    title="Weak Cryptography",
                    description=description,
                    severity=SeverityLevel.HIGH,
                    remediation="Use SHA256 or stronger algorithms",
                )
                issues.append(issue)

        self.issues.extend(issues)
        return issues

    def get_issues_by_severity(self, severity: SeverityLevel) -> List[SecurityIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_critical_issues(self) -> List[SecurityIssue]:
        """Get all critical issues."""
        return self.get_issues_by_severity(SeverityLevel.CRITICAL)

    def get_high_issues(self) -> List[SecurityIssue]:
        """Get all high severity issues."""
        return self.get_issues_by_severity(SeverityLevel.HIGH)

    def generate_report(self) -> Dict[str, Any]:
        """Generate security scan report."""
        return {
            "total_issues": len(self.issues),
            "critical": len(self.get_critical_issues()),
            "high": len(self.get_high_issues()),
            "medium": len(self.get_issues_by_severity(SeverityLevel.MEDIUM)),
            "low": len(self.get_issues_by_severity(SeverityLevel.LOW)),
            "info": len(self.get_issues_by_severity(SeverityLevel.INFO)),
            "issues": [
                {
                    "id": issue.issue_id,
                    "title": issue.title,
                    "severity": issue.severity.value,
                    "file": issue.file_path,
                    "line": issue.line_number,
                    "remediation": issue.remediation,
                }
                for issue in self.issues
            ],
        }

    def clear_issues(self) -> None:
        """Clear all found issues."""
        self.issues = []


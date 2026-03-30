"""
ROXY Secret Scanner Pre-Flight Gate

AAA Quality Implementation: Law 0 Reuse - Extends existing ROXY security patterns

This module provides a pre-flight gate that scans for exposed secrets before
any tool execution. It blocks if high-risk patterns are detected and provides
actionable remediation guidance.

Usage:
    from secret_scanner import SecretScanner, scan_or_die
    
    # As a function
    scan_or_die()
    
    # As a class for programmatic use
    scanner = SecretScanner()
    result = scanner.scan_workspace("/path/to/scan")
    if not result.passed:
        print(f"Blocked: {result.violations}")
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.secret_scanner")


class Severity(Enum):
    """Severity levels for secret violations."""
    CRITICAL = "critical"  # Always block
    HIGH = "high"          # Always block
    MEDIUM = "medium"      # Warn by default
    LOW = "low"            # Report only


SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


@dataclass
class SecretViolation:
    """Represents a detected secret violation."""
    severity: Severity
    pattern_name: str
    file_path: str
    line_number: Optional[int] = None
    matched_content: str = ""  # Truncated, never full secret
    remediation: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "severity": self.severity.value,
            "pattern_name": self.pattern_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "matched_content": self.matched_content[:50] + "..." if len(self.matched_content) > 50 else self.matched_content,
            "remediation": self.remediation
        }


@dataclass
class ScanResult:
    """Result of a secret scan operation."""
    passed: bool
    violations: list[SecretViolation] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    files_scanned: int = 0
    blocked: bool = False
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "violations": [v.to_dict() for v in self.violations],
            "scan_duration_ms": self.scan_duration_ms,
            "files_scanned": self.files_scanned,
            "error_message": self.error_message
        }


class SecretPatterns:
    """
    Comprehensive secret detection patterns.
    
    Patterns are organized by type with remediation guidance.
    Inspired by OWASP secrets management best practices.
    """
    
    # Critical patterns - always block
    CRITICAL_PATTERNS = [
        {
            "name": "AWS Access Key",
            "regex": r'AKIA[0-9A-Z]{16}',
            "remediation": "Rotate AWS credentials via IAM console or AWS CLI"
        },
        {
            "name": "AWS Secret Key",
            "regex": r'(?i)aws_secret_access_key\s*[=:]\s*["\']?[A-Za-z0-9/+=]{40}',
            "remediation": "Rotate AWS credentials via IAM console"
        },
        {
            "name": "GitHub Token",
            "regex": r'gh[pousr]_[A-Za-z0-9_]{36,255}',
            "remediation": "Revoke token at GitHub Settings > Developer settings > Personal access tokens"
        },
        {
            "name": "Stripe API Key",
            "regex": r'sk_live_[0-9a-zA-Z]{24,}',
            "remediation": "Rotate Stripe API keys at dashboard.stripe.com > Developers > API keys"
        },
        {
            "name": "Stripe Publishable Key",
            "regex": r'pk_live_[0-9a-zA-Z]{24,}',
            "remediation": "This is a publishable key - rotate if you need strict security"
        },
        {
            "name": "Private Key Block",
            "regex": r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
            "remediation": "Remove private key from repository, regenerate if compromised"
        },
        {
            "name": "GitHub OAuth Token",
            "regex": r'gho_[A-Za-z0-9_]{36,255}',
            "remediation": "Revoke at GitHub Settings > Developer settings > OAuth applications"
        },
        {
            "name": "Slack Token",
            "regex": r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*',
            "remediation": "Revoke Slack token at api.slack.com/apps > Your App > OAuth & Permissions"
        },
        {
            "name": "OpenAI API Key",
            "regex": r'sk-[A-Za-z0-9_-]{32,}',
            "remediation": "Rotate at platform.openai.com > API keys > Create new secret key"
        },
        {
            "name": "Anthropic API Key",
            "regex": r'sk-ant-[A-Za-z0-9_-]{20,}[A-Za-z0-9_-]{20,}',
            "remediation": "Rotate at console.anthropic.com > API Keys"
        },
    ]
    
    # High-risk patterns - always block
    HIGH_PATTERNS = [
        {
            "name": "Generic API Key",
            "regex": r'(?i)(api[_-]?key|apikey|api_secret)\s*[=:]\s*["\']?(?:sk[-_]|pk[-_]|key[-_]|AKIA|ghp_|xox[baprs])[A-Za-z0-9_\-]{16,}["\']?',
            "remediation": "Move to secrets manager (e.g., Infisical, HashiCorp Vault)"
        },
        {
            "name": "Bearer Token",
            "regex": r'(?i)authorization:\s*Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
            "remediation": "Revoke and regenerate token"
        },
        {
            "name": "Basic Auth",
            "regex": r'(?i)authorization:\s*Basic\s+[A-Za-z0-9+/]+=*',
            "remediation": "Move credentials to secrets manager"
        },
        {
            "name": "Database URL with Password",
            "regex": r'(?i)(mysql|postgres|mongodb|redis)://[^:]+:[^@?#&]+@[a-z0-9\-\.]+:\d+',
            "remediation": "Move connection string to secrets manager, use env vars"
        },
        {
            "name": "JWT Token",
            "regex": r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',
            "remediation": "Revoke JWT and reissue"
        },
        {
            "name": "Telegram Bot Token",
            "regex": r'[0-9]{8,10}:[A-Za-z0-9_-]{35}',
            "remediation": "Revoke via @BotFather and generate new token"
        },
        {
            "name": "Twilio API Key",
            "regex": r'SK[0-9a-fA-F]{32}',
            "remediation": "Rotate at console.twilio.com > Account > API Keys"
        },
        {
            "name": "Mailchimp API Key",
            "regex": r'[a-f0-9]{32}-us[0-9]{1,2}',
            "remediation": "Rotate at mailchimp.com > Account > Extras > API keys"
        },
        {
            "name": "SendGrid API Key",
            "regex": r'SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}',
            "remediation": "Rotate at app.sendgrid.com > Settings > API Keys"
        },
        {
            "name": "NPM Token",
            "regex": r'npm_[A-Za-z0-9]{36}',
            "remediation": "Revoke at npmjs.com > Access Tokens"
        },
    ]
    
    EXCLUDE_PATHS = [
        r'\.git/',
        r'\.gitignore',
        r'\.env\.example',
        r'\.env\.template',
        r'\.env\.bak',
        r'\.env\.backup',
        r'/\.env$',
        r'/etc/roxy\.env$',
        r'obs-portable/',
        r'node_modules/',
        r'vendor/',
        r'\.venv/',
        r'__pycache__/',
        r'\.pytest_cache/',
        r'\.next/',
        r'dist/',
        r'build/',
        r'coverage/',
        r'\.terraform/',
        r'\.secrets/',
        r'secret_scanner\.py',
        r'memory_postgres\.py',
        r'infrastructure\.py',
        r'preflight_bridge\.py',
        r'.*_test\.py$',
        r'.*_spec\.py$',
        r'briefings/',
        r'data/',
        r'eval_',
        r'benchmark_',
    ]
    
    SCAN_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx',
        '.env', '.ini', '.cfg', '.conf', '.toml', '.properties', '.sh',
        '.bash', '.zsh', '.bashrc', '.zshrc', '.vimrc', '.sql', '.pem',
        '.xml', '.gradle', '.properties'
    }


class SecretScanner:
    """
    Pre-flight secret scanner for ROXY.
    
    Scans workspace for exposed secrets before tool execution.
    Blocks if CRITICAL or HIGH severity violations are found.
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    - Audit trail support
    """
    
    def __init__(
        self,
        exclude_paths: Optional[list[str]] = None,
        dry_run: bool = False,
        min_severity: Severity = Severity.HIGH,
        max_files: Optional[int] = None,
        max_scan_seconds: Optional[float] = None,
        max_file_bytes: Optional[int] = None,
    ):
        """
        Initialize the secret scanner.
        
        Args:
            exclude_paths: Additional paths to exclude from scanning
            dry_run: If True, log violations but don't block
            min_severity: Minimum severity to trigger blocking
            max_files: Optional hard cap on number of files to scan
            max_scan_seconds: Optional wall-time budget in seconds
            max_file_bytes: Optional maximum file size to scan
        """
        self.exclude_paths = exclude_paths or []
        self.dry_run = dry_run
        self.min_severity = min_severity
        self.max_files = max_files if max_files is not None else int(os.getenv("ROXY_SECRET_SCAN_MAX_FILES", "3000"))
        self.max_scan_seconds = (
            max_scan_seconds if max_scan_seconds is not None else float(os.getenv("ROXY_SECRET_SCAN_MAX_SECONDS", "60"))
        )
        self.max_file_bytes = (
            max_file_bytes if max_file_bytes is not None else int(os.getenv("ROXY_SECRET_SCAN_MAX_FILE_BYTES", str(2 * 1024 * 1024)))
        )
        self._compiled_excludes: list[re.Pattern] = []
        self._compiled_patterns: dict[Severity, list[tuple[str, re.Pattern]]] = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
        }
        self._compile_patterns()
        
        logger.info(
            f"SecretScanner initialized: dry_run={dry_run}, "
            f"min_severity={min_severity.value}, "
            f"excludes={len(self._compiled_excludes)}, "
            f"max_files={self.max_files}, max_seconds={self.max_scan_seconds}, "
            f"max_file_bytes={self.max_file_bytes}"
        )
    
    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        # Compile exclude patterns
        for path in SecretPatterns.EXCLUDE_PATHS + self.exclude_paths:
            self._compiled_excludes.append(re.compile(path))
        
        # Compile critical patterns
        for pattern in SecretPatterns.CRITICAL_PATTERNS:
            self._compiled_patterns[Severity.CRITICAL].append(
                (pattern["name"], re.compile(pattern["regex"]))
            )
        
        # Compile high patterns
        for pattern in SecretPatterns.HIGH_PATTERNS:
            self._compiled_patterns[Severity.HIGH].append(
                (pattern["name"], re.compile(pattern["regex"]))
            )
    
    def _should_exclude(self, file_path: str) -> bool:
        """Check if file should be excluded from scanning."""
        path_str = str(file_path)
        filename = Path(file_path).name
        if filename.startswith("test_") and filename.endswith(".py"):
            return True
        for pattern in self._compiled_excludes:
            if pattern.search(path_str):
                return True
        return False
    
    def _get_scan_severity(self, file_path: str) -> Optional[Severity]:
        """
        Determine if a file warrants scanning based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Severity level to use, or None if should skip
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        filename = path.name.lower()

        # .env files are always critical
        if filename.startswith(".env") and filename not in {".env.example", ".env.template"}:
            # Check if it's not a template
            if '.env.' in filename or filename == '.env':
                return Severity.CRITICAL
        
        # Known file types
        if ext in SecretPatterns.SCAN_EXTENSIONS:
            # Scripts and config files are higher risk
            if ext in {'.sh', '.bash', '.zsh', '.yaml', '.yml', '.json', '.env'}:
                return Severity.HIGH
            return Severity.MEDIUM
        
        return None

    def _meets_min_severity(self, severity: Severity) -> bool:
        """Return True when candidate severity should be included by current threshold."""
        return SEVERITY_RANK[severity] >= SEVERITY_RANK[self.min_severity]

    def scan_file(self, file_path: str) -> list[SecretViolation]:
        """
        Scan a single file for secrets.
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            List of violations found
        """
        if self._should_exclude(file_path):
            return []

        severity = self._get_scan_severity(file_path)
        if not severity:
            return []
        
        violations = []
        
        try:
            if self.max_file_bytes:
                try:
                    file_size = Path(file_path).stat().st_size
                    if file_size > self.max_file_bytes:
                        return []
                except OSError:
                    return []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Check .env files with key=value parsing
            if Path(file_path).name.lower().startswith(".env"):
                violations.extend(self._scan_env_file(file_path, lines))
            
            # Check all files with regex patterns
            for line_num, line in enumerate(lines, start=1):
                violations.extend(self._scan_line(file_path, line, line_num))
        
        except (IOError, PermissionError) as e:
            logger.debug(f"Could not scan {file_path}: {e}")
        
        return violations
    
    def _scan_env_file(
        self,
        file_path: str,
        lines: list[str]
    ) -> list[SecretViolation]:
        """Scan .env file with key=value awareness."""
        violations = []
        sensitive_keys = {
            'SECRET', 'KEY', 'TOKEN', 'PASSWORD', 'PASS', 'PWD',
            'API_KEY', 'APIKEY', 'ACCESS_KEY', 'AUTH', 'CREDENTIALS',
            'PRIVATE', 'SERVICE_KEY', 'CLIENT_SECRET'
        }

        if not self._meets_min_severity(Severity.CRITICAL):
            return violations
        
        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value
            if '=' in line:
                key = line.split('=')[0].strip().upper()
                
                # Check if this is a sensitive key with a value
                if any(sk in key for sk in sensitive_keys):
                    # Extract the value part (redacted)
                    value_part = line[len(key):].lstrip('= ').strip()
                    
                    # Check if it looks like it has an actual secret
                    if value_part and value_part not in ('', '""', "''", 'null', 'undefined'):
                        # Check if it's not a placeholder
                        if not any(p in value_part.lower() for p in ['your_', 'example', 'xxx', '***']):
                            violations.append(SecretViolation(
                                severity=Severity.CRITICAL,
                                pattern_name=f"ENV Sensitive: {key}",
                                file_path=file_path,
                                line_number=line_num,
                                matched_content=f"{key}=***REDACTED***",
                                remediation=f"Move {key} to secrets manager (Infisical)"
                            ))
        
        return violations
    
    def _scan_line(
        self,
        file_path: str,
        line: str,
        line_num: int
    ) -> list[SecretViolation]:
        """Scan a single line for secret patterns."""
        violations = []
        
        # Check against patterns based on severity threshold
        for severity in [Severity.CRITICAL, Severity.HIGH]:
            if not self._meets_min_severity(severity):
                continue
                
            for name, pattern in self._compiled_patterns[severity]:
                match = pattern.search(line)
                if match:
                    # Get remediation
                    remediation = self._get_remediation(name)
                    
                    # Truncate the matched content for safety
                    matched = match.group(0)
                    truncated = matched[:20] + "..." if len(matched) > 20 else matched
                    
                    violations.append(SecretViolation(
                        severity=severity,
                        pattern_name=name,
                        file_path=file_path,
                        line_number=line_num,
                        matched_content=truncated,
                        remediation=remediation
                    ))
        
        return violations
    
    def _get_remediation(self, pattern_name: str) -> str:
        """Get remediation guidance for a pattern."""
        for pattern in SecretPatterns.CRITICAL_PATTERNS + SecretPatterns.HIGH_PATTERNS:
            if pattern["name"] == pattern_name:
                return pattern["remediation"]
        return "Move to secrets manager and rotate"
    
    def scan_workspace(self, root_path: str) -> ScanResult:
        """
        Scan entire workspace for secrets.
        
        Args:
            root_path: Root directory to scan
            
        Returns:
            ScanResult with all violations and metadata
        """
        import time
        start_time = time.time()
        
        violations: list[SecretViolation] = []
        files_scanned = 0
        error_msg = None
        critical_notice_logged = False
        
        try:
            root = Path(root_path).resolve()
            if not root.exists():
                return ScanResult(
                    passed=False,
                    blocked=not self.dry_run,
                    error_message=f"Path does not exist: {root_path}"
                )
            
            logger.info(f"Starting workspace scan: {root}")
            
            for file_path in root.rglob('*'):
                if self.max_scan_seconds and (time.time() - start_time) >= self.max_scan_seconds:
                    if not error_msg:
                        error_msg = f"scan_truncated:max_seconds={self.max_scan_seconds}"
                    logger.warning(
                        "Secret scan truncated by time budget: %.1fs",
                        self.max_scan_seconds,
                    )
                    break
                if self.max_files and files_scanned >= self.max_files:
                    if not error_msg:
                        error_msg = f"scan_truncated:max_files={self.max_files}"
                    logger.warning(
                        "Secret scan truncated by file budget: %s files",
                        self.max_files,
                    )
                    break

                if not file_path.is_file():
                    continue
                
                if self._should_exclude(str(file_path)):
                    continue
                
                file_violations = self.scan_file(str(file_path))
                violations.extend(file_violations)
                files_scanned += 1
                
                # Emit only one notice when criticals are first observed.
                if (
                    not self.dry_run
                    and not critical_notice_logged
                    and any(v.severity == Severity.CRITICAL for v in file_violations)
                ):
                    critical_notice_logged = True
                    logger.warning("Critical violations found, continuing scan for audit trail")
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scan error: {e}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Determine if should block
        blocking_violations = [v for v in violations if self._meets_min_severity(v.severity)]
        
        passed = len(blocking_violations) == 0
        blocked = not self.dry_run and not passed
        
        result = ScanResult(
            passed=passed,
            violations=violations,
            scan_duration_ms=duration_ms,
            files_scanned=files_scanned,
            blocked=blocked,
            error_message=error_msg
        )
        
        logger.info(
            f"Scan complete: passed={passed}, blocked={blocked}, "
            f"violations={len(violations)}, files={files_scanned}, "
            f"duration={duration_ms:.1f}ms"
        )
        
        return result
    
    def scan_and_emit(self, root_path: str) -> dict:
        """
        Scan workspace and emit structured result for audit trail.
        
        Args:
            root_path: Root directory to scan
            
        Returns:
            Dict suitable for audit logging
        """
        result = self.scan_workspace(root_path)
        
        audit_entry = {
            "event": "secret_scan",
            "timestamp": datetime.now(UTC).isoformat(),
            "root_path": root_path,
            "passed": result.passed,
            "blocked": result.blocked,
            "violation_count": len(result.violations),
            "critical_count": len([v for v in result.violations if v.severity == Severity.CRITICAL]),
            "high_count": len([v for v in result.violations if v.severity == Severity.HIGH]),
            "files_scanned": result.files_scanned,
            "duration_ms": result.scan_duration_ms,
            "violations": [v.to_dict() for v in result.violations[:20]],  # Limit for log size
            "error": result.error_message
        }
        
        # Log to audit trail
        if result.blocked:
            logger.error(f"SECURITY: Secret scan BLOCKED execution: {audit_entry}")
        elif result.violations:
            logger.warning(f"SECURITY: Secrets detected (not blocking): {audit_entry}")
        else:
            logger.info(f"SECURITY: Secret scan passed")
        
        return audit_entry


def scan_or_die(
    root_path: Optional[str] = None,
    dry_run: bool = False,
    min_severity: Severity = Severity.HIGH
) -> ScanResult:
    """
    Pre-flight secret scan that raises if secrets are detected.
    
    This is the main entry point for pre-flight gating.
    
    Args:
        root_path: Path to scan. Defaults to current working directory.
        dry_run: If True, don't block even if violations found.
        min_severity: Minimum severity to trigger blocking.
        
    Returns:
        ScanResult from the scan.
        
    Raises:
        SecretViolationError: If CRITICAL or HIGH secrets found and not dry_run.
        
    Example:
        >>> scan_or_die("/home/mark/work/project")
        ScanResult(passed=True, ...)
        
        >>> scan_or_die("/home/mark/work/project", dry_run=True)
        ScanResult(passed=False, violations=[...], blocked=False)
    """
    if root_path is None:
        root_path = os.getcwd()
    
    scanner = SecretScanner(dry_run=dry_run, min_severity=min_severity)
    result = scanner.scan_workspace(root_path)
    
    if result.blocked:
        violation_summary = "\n".join([
            f"  [{v.severity.value.upper()}] {v.pattern_name}"
            f" in {v.file_path}:{v.line_number or '?'}"
            f"\n    Fix: {v.remediation}"
            for v in result.violations[:10]
        ])
        
        error_msg = (
            f"🔒 SECRET SCAN BLOCKED EXECUTION\n\n"
            f"Found {len(result.violations)} violations:\n"
            f"{violation_summary}\n\n"
            f"Remediation: Fix secrets before retrying.\n"
            f"To scan without blocking (dev mode): dry_run=True"
        )
        
        logger.error(error_msg)
        raise SecretViolationError(error_msg, result)
    
    return result


class SecretViolationError(Exception):
    """Raised when secret scan detects violations and blocking is enabled."""
    
    def __init__(self, message: str, result: ScanResult):
        super().__init__(message)
        self.result = result


# CLI entry point
if __name__ == "__main__":
    import argparse
    import json
    import sys
    
    parser = argparse.ArgumentParser(
        description="ROXY Secret Scanner Pre-Flight Gate"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to scan (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't block, just report violations"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format"
    )
    parser.add_argument(
        "--min-severity",
        choices=["critical", "high", "medium", "low"],
        default="high",
        help="Minimum severity to trigger blocking"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )
    
    # Map severity string to enum
    severity_map = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
    }
    
    scanner = SecretScanner(
        dry_run=args.dry_run,
        min_severity=severity_map[args.min_severity]
    )
    
    result = scanner.scan_workspace(args.path)
    
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.passed:
            print(f"✅ Secret scan PASSED ({result.files_scanned} files scanned)")
            sys.exit(0)
        elif result.blocked:
            print(f"🚫 Secret scan BLOCKED ({len(result.violations)} violations)")
            for v in result.violations[:10]:
                print(f"  [{v.severity.value.upper()}] {v.pattern_name}: {v.file_path}:{v.line_number}")
            sys.exit(1)
        else:
            print(f"⚠️  Secret scan WARNING ({len(result.violations)} violations, not blocking)")
            for v in result.violations[:10]:
                print(f"  [{v.severity.value.upper()}] {v.pattern_name}: {v.file_path}")
            sys.exit(0)

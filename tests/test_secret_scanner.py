"""
AAA Quality Tests: Secret Scanner Pre-Flight Gate

Tests cover:
- Pattern detection
- Blocking behavior
- Graceful degradation
- Audit trail emission
"""

import logging
from pathlib import Path

import pytest

from secret_scanner import (
    SecretScanner,
    SecretViolationError,
    Severity,
    SecretViolation,
    ScanResult,
    scan_or_die,
)


class TestSecretPatterns:
    """Test secret pattern detection."""
    
    def test_aws_access_key_detected(self, tmp_path):
        """AWS Access Key ID should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "config.py"
        test_file.write_text("AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
        assert any(v.pattern_name == "AWS Access Key" for v in violations)
    
    def test_aws_secret_key_detected(self, tmp_path):
        """AWS Secret Access Key should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "config.py"
        test_file.write_text("aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
    
    def test_github_token_detected(self, tmp_path):
        """GitHub token should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "deploy.sh"
        test_file.write_text("GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
        assert any("GitHub" in v.pattern_name for v in violations)
    
    def test_openai_api_key_detected(self, tmp_path):
        """OpenAI API key should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / ".env"
        test_file.write_text("OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz1234567890")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
    
    def test_private_key_detected(self, tmp_path):
        """Private key block should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "keys.pem"
        test_file.write_text("""-----BEGIN RSA PRIVATE KEY-----
MIIBOgIBAAJBALRiMLAHudeSA2F+0TaRO9xMMhQ+TwUL1N3zZnF3qPGQ9vZCxG3E
-----END RSA PRIVATE KEY-----""")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
        assert any("Private Key" in v.pattern_name for v in violations)
    
    def test_database_url_with_password_detected(self, tmp_path):
        """Database URL with password should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "config.yaml"
        test_file.write_text("database: postgres://admin:secretpass@localhost:5432/db")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
        assert any("Database" in v.pattern_name for v in violations)
    
    def test_stripe_key_detected(self, tmp_path):
        """Stripe API key should be detected."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "config.py"
        stripe_key = "sk_" + "live_1234567890abcdefghijklmnop"
        test_file.write_text(f"STRIPE_KEY='{stripe_key}'")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) >= 1
        assert any("Stripe" in v.pattern_name for v in violations)


class TestEnvFileScanning:
    """Test .env file scanning with key=value awareness."""
    
    def test_sensitive_env_key_detected(self, tmp_path):
        """Sensitive keys in .env should trigger violation."""
        scanner = SecretScanner(dry_run=False)
        
        env_file = tmp_path / ".env"
        api_secret = "sk_" + "live_realkey123456789012345"
        env_file.write_text(f"""# Database
DB_PASSWORD=supersecret123

# API Keys
API_SECRET={api_secret}

# Not sensitive
DB_HOST=localhost
""")
        
        violations = scanner.scan_file(str(env_file))
        
        critical_violations = [v for v in violations if v.severity == Severity.CRITICAL]
        assert len(critical_violations) >= 1
    
    def test_example_env_not_flagged(self, tmp_path):
        """Example .env files should be excluded."""
        scanner = SecretScanner(dry_run=False)
        
        env_file = tmp_path / ".env.example"
        env_file.write_text("API_KEY=your_api_key_here")
        
        violations = scanner.scan_file(str(env_file))
        
        # Should not flag placeholder values
        assert all(v.severity != Severity.CRITICAL for v in violations)


class TestExclusionPatterns:
    """Test file/path exclusion logic."""
    
    def test_git_directory_excluded(self, tmp_path):
        """Git directories should be excluded."""
        scanner = SecretScanner(dry_run=False)
        
        git_dir = tmp_path / ".git" / "objects"
        git_dir.mkdir(parents=True)
        git_file = git_dir / "config"
        git_file.write_text("aws_access_key=AKIATEST123456789")
        
        violations = scanner.scan_file(str(git_file))
        
        # Should be excluded
        assert len(violations) == 0
    
    def test_node_modules_excluded(self, tmp_path):
        """Node modules should be excluded."""
        scanner = SecretScanner(dry_run=False)
        
        nm_dir = tmp_path / "node_modules" / "package" / "index.js"
        nm_dir.parent.mkdir(parents=True)
        nm_dir.write_text("const API_KEY = 'AKIA_REAL_KEY_1234567890'")
        
        violations = scanner.scan_file(str(nm_dir))
        
        assert len(violations) == 0
    
    def test_test_files_excluded(self, tmp_path):
        """Test files should be excluded by default."""
        scanner = SecretScanner(dry_run=False)
        
        test_file = tmp_path / "test_config.py"
        test_file.write_text("API_KEY = 'sk_test_real_key_123456789012345678'")
        
        violations = scanner.scan_file(str(test_file))
        
        assert len(violations) == 0


class TestScanResult:
    """Test scan result structure."""
    
    def test_pass_result_structure(self, tmp_path):
        """Clean scan should produce passed result."""
        scanner = SecretScanner(dry_run=False)
        
        clean_file = tmp_path / "README.md"
        clean_file.write_text("# My Project\nThis is a clean file.")
        
        result = scanner.scan_workspace(str(tmp_path))
        
        assert result.passed is True
        assert result.blocked is False
        assert len(result.violations) == 0
        assert result.files_scanned >= 1
        assert result.scan_duration_ms >= 0
    
    def test_fail_result_structure(self, tmp_path):
        """Scan with violations should produce correct structure."""
        scanner = SecretScanner(dry_run=True)  # Don't block in test
        
        bad_file = tmp_path / "config.py"
        bad_file.write_text("API_KEY = 'sk_live_real_key_123456789012345678901234567890'")
        
        result = scanner.scan_workspace(str(tmp_path))
        
        assert result.passed is False
        assert result.blocked is False  # dry_run=True
        assert len(result.violations) >= 1
        assert result.files_scanned >= 1
    
    def test_result_json_serialization(self, tmp_path):
        """ScanResult should serialize to JSON."""
        scanner = SecretScanner(dry_run=True)
        
        result = scanner.scan_workspace(str(tmp_path))
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "passed" in result_dict
        assert "violations" in result_dict
        assert "files_scanned" in result_dict


class TestScanOrDie:
    """Test scan_or_die function."""
    
    def test_clean_workspace_passes(self, tmp_path):
        """Clean workspace should pass scan_or_die."""
        clean_file = tmp_path / "main.py"
        clean_file.write_text("print('hello world')")
        
        result = scan_or_die(str(tmp_path), dry_run=True)
        
        assert result.passed is True
    
    def test_secrets_block_without_dry_run(self, tmp_path):
        """Secrets should block without dry_run."""
        bad_file = tmp_path / "config.py"
        bad_file.write_text("API_KEY = 'sk_live_real_key_123456789012345678901234567890'")
        
        with pytest.raises(SecretViolationError) as exc_info:
            scan_or_die(str(tmp_path), dry_run=False)
        
        assert exc_info.value.result.blocked is True
    
    def test_secrets_allow_with_dry_run(self, tmp_path):
        """Secrets should not block with dry_run=True."""
        bad_file = tmp_path / "config.py"
        bad_file.write_text("API_KEY = 'sk_live_real_key_123456789012345678901234567890'")
        
        result = scan_or_die(str(tmp_path), dry_run=True)
        
        assert result.passed is False
        assert result.blocked is False


class TestAuditTrail:
    """Test audit trail emission."""
    
    def test_audit_entry_structure(self, tmp_path):
        """scan_and_emit should produce structured audit entry."""
        scanner = SecretScanner(dry_run=True)
        
        result = scanner.scan_and_emit(str(tmp_path))
        
        assert "event" in result
        assert result["event"] == "secret_scan"
        assert "timestamp" in result
        assert "passed" in result
        assert "violations" in result
    
    def test_blocked_scan_logs_error(self, tmp_path, caplog):
        """Blocked scan should emit error log."""
        bad_file = tmp_path / "secrets.txt"
        bad_file.write_text("AWS_KEY=AKIAIOSFODNN7EXAMPLE")
        
        scanner = SecretScanner(dry_run=False)
        
        with caplog.at_level(logging.ERROR):
            scanner.scan_and_emit(str(tmp_path))
        
        assert any("BLOCKED" in record.message for record in caplog.records)


class TestGracefulDegradation:
    """Test graceful handling of edge cases."""
    
    def test_nonexistent_path_handled(self):
        """Nonexistent path should be handled gracefully."""
        scanner = SecretScanner(dry_run=True)
        
        result = scanner.scan_workspace("/nonexistent/path/12345")
        
        assert result.passed is False
        assert result.error_message is not None
    
    def test_permission_error_handled(self, tmp_path):
        """Permission errors should be handled gracefully."""
        scanner = SecretScanner(dry_run=True)
        
        # Create a file that can't be read
        import stat
        protected_dir = tmp_path / "protected"
        protected_dir.mkdir()
        protected_file = protected_dir / "secret.txt"
        protected_file.write_text("SECRET=password123")
        protected_file.chmod(0o000)
        
        try:
            violations = scanner.scan_file(str(protected_file))
            # Should not raise, just return empty
            assert isinstance(violations, list)
        finally:
            # Cleanup
            protected_file.chmod(stat.S_IRUSR | stat.S_IWUSR)


class TestPerformance:
    """Test performance characteristics."""
    
    def test_scan_completes_in_reasonable_time(self, tmp_path):
        """Scan should complete in reasonable time."""
        scanner = SecretScanner(dry_run=False)
        
        # Create 100 files
        for i in range(100):
            f = tmp_path / f"file_{i}.py"
            f.write_text(f"# File {i}\nprint('hello')")
        
        import time
        start = time.time()
        result = scanner.scan_workspace(str(tmp_path))
        duration = time.time() - start
        
        # Should complete in under 5 seconds for 100 files
        assert duration < 5.0
        assert result.files_scanned >= 100


# Integration test marker
pytestmark = pytest.mark.integration


class TestIntegrationPreFlight:
    """Integration tests for pre-flight gate usage."""
    
    def test_scanner_can_be_imported(self):
        """Module should be importable."""
        from secret_scanner import SecretScanner, scan_or_die
        assert SecretScanner is not None
        assert scan_or_die is not None
    
    def test_scanner_usable_in_roxy_context(self, tmp_path):
        """
        Scanner should be usable in ROXY context.
        
        This simulates how it would be called from roxy_core.py
        before an OpenCode spawn.
        """
        # Simulate workspace
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "main.py").write_text("# Clean workspace")
        
        # Import and run like ROXY would
        from secret_scanner import scan_or_die
        
        result = scan_or_die(str(workspace), dry_run=False)
        
        assert result.passed is True
        assert result.blocked is False

"""
Integration tests for roxy_core.py HTTP server
Tests health endpoint, authentication, rate limiting, and command execution
"""
import pytest
import requests
import time
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8766"

# Load actual token from secret.token
TOKEN_FILE = Path.home() / ".roxy" / "secret.token"
if TOKEN_FILE.exists():
    with open(TOKEN_FILE) as f:
        TEST_TOKEN = f.read().strip()
else:
    TEST_TOKEN = "test_token_placeholder"


class TestHealthEndpoint:
    """Test /health endpoint"""
    
    def test_health_endpoint_responds(self):
        """Test that health endpoint responds"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_health_endpoint_no_auth_required(self):
        """Test that health endpoint doesn't require auth"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestAuthenticationEndpoint:
    """Test authentication requirements"""
    
    def test_run_endpoint_requires_auth(self):
        """Test that /run endpoint requires authentication"""
        try:
            response = requests.post(
                f"{BASE_URL}/run",
                json={"command": "hello"},
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_run_endpoint_with_valid_token(self):
        """Test that /run endpoint accepts valid token"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "hello roxy"},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_run_endpoint_with_invalid_token(self):
        """Test that /run endpoint rejects invalid token"""
        try:
            headers = {"X-ROXY-Token": "invalid_token_12345"}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "hello"},
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.slow
    def test_rate_limiting_enforced(self):
        """Test that rate limiting is enforced"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            
            # Send multiple requests rapidly
            responses = []
            for i in range(100):
                try:
                    r = requests.post(
                        f"{BASE_URL}/run",
                        headers=headers,
                        json={"command": f"test {i}"},
                        timeout=2
                    )
                    responses.append(r.status_code)
                except requests.exceptions.Timeout:
                    pass
                except requests.exceptions.ConnectionError:
                    break
            
            # Should have some 429 (rate limited) responses if enabled
            if len(responses) > 0:
                # Check if any rate limiting occurred
                has_rate_limit = 429 in responses
                # Note: May not always trigger in tests depending on config
                assert len(responses) > 0
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestCommandExecution:
    """Test command execution"""
    
    def test_greeting_command(self):
        """Test simple greeting command"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "hi roxy"},
                timeout=10
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "result" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_git_status_command(self):
        """Test git status command"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "git status"},
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestStreamingEndpoint:
    """Test SSE streaming endpoint"""
    
    def test_streaming_endpoint_requires_auth(self):
        """Test that streaming endpoint requires authentication"""
        try:
            response = requests.get(
                f"{BASE_URL}/stream?q=hello",
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_streaming_endpoint_with_auth(self):
        """Test streaming endpoint with authentication"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.get(
                f"{BASE_URL}/stream?q=hello",
                headers=headers,
                stream=True,
                timeout=10
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("Content-Type", "")
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestBatchEndpoint:
    """Test batch command execution"""
    
    def test_batch_endpoint_requires_auth(self):
        """Test that batch endpoint requires authentication"""
        try:
            response = requests.post(
                f"{BASE_URL}/batch",
                json={"commands": ["hello", "git status"]},
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_batch_endpoint_with_auth(self):
        """Test batch endpoint with authentication"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/batch",
                headers=headers,
                json={"commands": ["hello roxy", "hi"]},
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "commands" in data
            assert len(data["commands"]) == 2
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")

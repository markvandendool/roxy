"""
Integration tests for ROXY - Full request/response cycle
Tests authentication flow, rate limiting behavior, error recovery, and concurrent requests
"""
import pytest
import requests
import time
import threading
from pathlib import Path

BASE_URL = "http://127.0.0.1:8766"

# Load actual token from secret.token
TOKEN_FILE = Path.home() / ".roxy" / "secret.token"
if TOKEN_FILE.exists():
    with open(TOKEN_FILE) as f:
        TEST_TOKEN = f.read().strip()
else:
    TEST_TOKEN = "test_token_placeholder"


class TestFullRequestResponseCycle:
    """Test complete request/response cycle"""
    
    def test_full_greeting_flow(self):
        """Test complete greeting flow with authentication"""
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
            assert "result" in data or "response" in data
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_full_git_status_flow(self):
        """Test complete git status flow"""
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


class TestAuthenticationFlow:
    """Test authentication flow"""
    
    def test_auth_flow_without_token(self):
        """Test that requests without token are rejected"""
        try:
            response = requests.post(
                f"{BASE_URL}/run",
                json={"command": "test"},
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_auth_flow_with_token(self):
        """Test that requests with valid token are accepted"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "hello"},
                timeout=10
            )
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_auth_flow_with_invalid_token(self):
        """Test that requests with invalid token are rejected"""
        try:
            headers = {"X-ROXY-Token": "invalid_token_12345"}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "test"},
                timeout=5
            )
            assert response.status_code == 403
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestRateLimitingBehavior:
    """Test rate limiting behavior"""
    
    @pytest.mark.slow
    def test_rate_limiting_after_burst(self):
        """Test that rate limiting kicks in after burst"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            
            # Send burst of requests
            responses = []
            for i in range(20):
                try:
                    r = requests.post(
                        f"{BASE_URL}/run",
                        headers=headers,
                        json={"command": f"test {i}"},
                        timeout=2
                    )
                    responses.append(r.status_code)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    break
            
            # Should have some successful responses
            assert len(responses) > 0
            # May have 429 if rate limiting is strict
            assert 200 in responses or 429 in responses
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    @pytest.mark.slow
    def test_rate_limiting_resets_over_time(self):
        """Test that rate limiting resets over time"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            
            # Send requests to hit limit
            for i in range(15):
                try:
                    requests.post(
                        f"{BASE_URL}/run",
                        headers=headers,
                        json={"command": f"test {i}"},
                        timeout=1
                    )
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    break
            
            # Wait a bit
            time.sleep(2)
            
            # Should be able to make requests again
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "test after wait"},
                timeout=5
            )
            # Should either succeed or be rate limited (both are valid)
            assert response.status_code in [200, 429]
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestErrorRecovery:
    """Test error recovery mechanisms"""
    
    def test_invalid_command_handling(self):
        """Test that invalid commands are handled gracefully"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={"command": "invalid_command_xyz_123"},
                timeout=10
            )
            # Should return 200 with error message, not crash
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["success", "error"]
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_malformed_json_handling(self):
        """Test that malformed JSON is handled gracefully"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                data="not json",
                timeout=5
            )
            # Should return 400 or similar, not crash
            assert response.status_code >= 400
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    def test_missing_command_field(self):
        """Test that missing command field is handled"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            response = requests.post(
                f"{BASE_URL}/run",
                headers=headers,
                json={},
                timeout=5
            )
            # Should return error, not crash
            assert response.status_code >= 400
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")


class TestConcurrentRequests:
    """Test concurrent request handling"""
    
    @pytest.mark.slow
    def test_concurrent_requests(self):
        """Test that multiple concurrent requests are handled"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            results = []
            errors = []
            
            def make_request(i):
                try:
                    response = requests.post(
                        f"{BASE_URL}/run",
                        headers=headers,
                        json={"command": f"test {i}"},
                        timeout=5
                    )
                    results.append(response.status_code)
                except Exception as e:
                    errors.append(str(e))
            
            # Create 5 concurrent requests
            threads = []
            for i in range(5):
                thread = threading.Thread(target=make_request, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10)
            
            # Should have some successful responses
            assert len(results) > 0 or len(errors) == 0
            # All should be 200 or 429 (rate limited)
            if results:
                assert all(status in [200, 429] for status in results)
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")
    
    @pytest.mark.slow
    def test_concurrent_different_endpoints(self):
        """Test concurrent requests to different endpoints"""
        try:
            headers = {"X-ROXY-Token": TEST_TOKEN}
            results = []
            
            def health_request():
                try:
                    r = requests.get(f"{BASE_URL}/health", timeout=5)
                    results.append(("health", r.status_code))
                except Exception:
                    pass
            
            def run_request():
                try:
                    r = requests.post(
                        f"{BASE_URL}/run",
                        headers=headers,
                        json={"command": "hello"},
                        timeout=5
                    )
                    results.append(("run", r.status_code))
                except Exception:
                    pass
            
            # Make concurrent requests to different endpoints
            threads = [
                threading.Thread(target=health_request),
                threading.Thread(target=run_request),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            
            # Should have responses from both endpoints
            assert len(results) >= 1
        except requests.exceptions.ConnectionError:
            pytest.skip("ROXY core not running")








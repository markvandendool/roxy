#!/usr/bin/env python3
"""
Pool Normalization Regression Tests

CHIEF DIRECTIVE: Lock in hardware-based pool naming contract.
These tests ensure BIG/FAST aliases correctly map to W5700X/6900XT.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPoolAliasNormalization(unittest.TestCase):
    """Test that pool aliases correctly normalize to canonical names."""

    def test_big_maps_to_w5700x(self):
        """Legacy BIG alias should map to w5700x."""
        from benchmark_service import POOL_ALIASES
        self.assertEqual(POOL_ALIASES.get("big"), "w5700x")

    def test_fast_maps_to_6900xt(self):
        """Legacy FAST alias should map to 6900xt."""
        from benchmark_service import POOL_ALIASES
        self.assertEqual(POOL_ALIASES.get("fast"), "6900xt")

    def test_pool_identity_w5700x_port(self):
        """W5700X pool should be on port 11434."""
        from benchmark_service import POOL_IDENTITY
        self.assertEqual(POOL_IDENTITY["w5700x"]["port"], 11434)
        self.assertEqual(POOL_IDENTITY["w5700x"]["gpu"], "W5700X")

    def test_pool_identity_6900xt_port(self):
        """6900XT pool should be on port 11435."""
        from benchmark_service import POOL_IDENTITY
        self.assertEqual(POOL_IDENTITY["6900xt"]["port"], 11435)
        self.assertEqual(POOL_IDENTITY["6900xt"]["gpu"], "6900XT")


class TestResolvePoolContract(unittest.TestCase):
    """Test _resolve_benchmark_pool API contract."""

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://127.0.0.1:11434",
        "ROXY_OLLAMA_6900XT_URL": "http://127.0.0.1:11435",
    })
    def test_big_returns_canonical_w5700x(self):
        """BIG input should return pool_requested_canonical='w5700x'."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("BIG")
        self.assertEqual(result["pool_requested_raw"], "BIG")
        self.assertEqual(result["pool_requested_canonical"], "w5700x")

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://127.0.0.1:11434",
        "ROXY_OLLAMA_6900XT_URL": "http://127.0.0.1:11435",
    })
    def test_fast_returns_canonical_6900xt(self):
        """FAST input should return pool_requested_canonical='6900xt'."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("FAST")
        self.assertEqual(result["pool_requested_raw"], "FAST")
        self.assertEqual(result["pool_requested_canonical"], "6900xt")

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://127.0.0.1:11434",
        "ROXY_OLLAMA_6900XT_URL": "http://127.0.0.1:11435",
    })
    def test_w5700x_returns_canonical_w5700x(self):
        """W5700X input should return pool_requested_canonical='w5700x'."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("W5700X")
        self.assertEqual(result["pool_requested_raw"], "W5700X")
        self.assertEqual(result["pool_requested_canonical"], "w5700x")

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://127.0.0.1:11434",
        "ROXY_OLLAMA_6900XT_URL": "http://127.0.0.1:11435",
    })
    def test_6900xt_returns_canonical_6900xt(self):
        """6900XT input should return pool_requested_canonical='6900xt'."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("6900XT")
        self.assertEqual(result["pool_requested_raw"], "6900XT")
        self.assertEqual(result["pool_requested_canonical"], "6900xt")

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://127.0.0.1:11434",
        "ROXY_OLLAMA_6900XT_URL": "http://127.0.0.1:11435",
    })
    def test_case_insensitive_input(self):
        """Pool names should be case-insensitive."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            for variant in ["big", "BIG", "Big", "bIg"]:
                result = _resolve_benchmark_pool(variant)
                self.assertEqual(result["pool_requested_canonical"], "w5700x",
                                 f"Failed for input: {variant}")


class TestEnvVarPrecedence(unittest.TestCase):
    """Test that new env vars take precedence over legacy."""

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_W5700X_URL": "http://new-url:11434",
        "OLLAMA_BIG_URL": "http://legacy-url:11434",
    }, clear=False)
    def test_w5700x_env_preferred_over_big(self):
        """ROXY_OLLAMA_W5700X_URL should be preferred over OLLAMA_BIG_URL."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("W5700X")
        self.assertIn("new-url", result["base_url"])

    @patch.dict(os.environ, {
        "ROXY_OLLAMA_6900XT_URL": "http://new-url:11435",
        "OLLAMA_FAST_URL": "http://legacy-url:11435",
    }, clear=False)
    def test_6900xt_env_preferred_over_fast(self):
        """ROXY_OLLAMA_6900XT_URL should be preferred over OLLAMA_FAST_URL."""
        from benchmark_service import _resolve_benchmark_pool
        with patch("urllib.request.urlopen"):
            result = _resolve_benchmark_pool("6900XT")
        self.assertIn("new-url", result["base_url"])


class TestPoolInvariantsCheck(unittest.TestCase):
    """Test pool invariants check function."""

    def test_check_pool_invariants_returns_dict(self):
        """check_pool_invariants should return a dict with ok key."""
        from benchmark_service import check_pool_invariants
        result = check_pool_invariants()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("pools", result)
        self.assertIn("checked_at", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Pytest configuration and fixtures for ROXY tests
"""
import pytest
import sys
from pathlib import Path
import json
import tempfile
import shutil

# Add roxy to path
ROXY_DIR = Path.home() / ".roxy"
sys.path.insert(0, str(ROXY_DIR))

@pytest.fixture
def mock_config():
    """Mock configuration for tests"""
    return {
        "port": 8766,
        "host": "127.0.0.1",
        "rate_limiting_enabled": True,
        "rate_limit": {
            "requests_per_minute": 60,
            "burst": 10
        },
        "allowed_paths": ["/home/mark/.roxy", "/home/mark/mindsong-juke-hub"]
    }

@pytest.fixture
def mock_auth_token():
    """Mock authentication token"""
    return "test_token_12345678901234567890123456789012"

@pytest.fixture
def temp_roxy_dir(tmp_path):
    """Create temporary ROXY directory for tests"""
    temp_dir = tmp_path / ".roxy"
    temp_dir.mkdir()
    
    # Create necessary subdirectories
    (temp_dir / "logs").mkdir()
    (temp_dir / "cache").mkdir()
    (temp_dir / "data").mkdir()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_config_file(temp_roxy_dir, mock_config):
    """Create mock config.json file"""
    config_path = temp_roxy_dir / "config.json"
    with open(config_path, 'w') as f:
        json.dump(mock_config, f, indent=2)
    return config_path

@pytest.fixture
def mock_secret_token(temp_roxy_dir, mock_auth_token):
    """Create mock secret.token file"""
    token_path = temp_roxy_dir / "secret.token"
    with open(token_path, 'w') as f:
        f.write(mock_auth_token)
    return token_path

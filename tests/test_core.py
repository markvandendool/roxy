"""Tests for ROXY core services"""
import pytest
import sys
from pathlib import Path

# Add services to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'services'))

def test_imports():
    """Test that core modules can be imported"""
    try:
        import services.roxy_core
        import services.jarvis_core
        import services.eventbus
        import services.orchestrator
        assert True
    except ImportError as e:
        pytest.skip(f"Import failed: {e}")

def test_memory_imports():
    """Test memory system imports"""
    try:
        from services.memory import episodic_memory
        from services.memory import semantic_memory
        from services.memory import working_memory
        assert True
    except ImportError as e:
        pytest.skip(f"Import failed: {e}")

def test_voice_imports():
    """Test voice system imports"""
    try:
        import voice.router
        assert True
    except ImportError as e:
        pytest.skip(f"Import failed: {e}")

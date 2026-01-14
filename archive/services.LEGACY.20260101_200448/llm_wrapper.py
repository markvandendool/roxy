#!/usr/bin/env python3
"""
LLM Service Wrapper - Clean import to avoid email module conflict
"""
import sys
import os

# Save and clean path
_original_path = sys.path.copy()
_clean_path = [p for p in sys.path if '/home/mark/.roxy/services' not in p]
sys.path = _clean_path

# Add services to end (not beginning) so stdlib takes precedence
sys.path.append('/home/mark/.roxy/services')

try:
    from llm_service import get_llm_service
    _llm_service_func = get_llm_service
except Exception as e:
    _llm_service_func = None
    import logging
    logging.warning(f"Could not import LLM service: {e}")

# Restore original path
sys.path = _original_path

def get_llm_service_safe():
    """Get LLM service without email conflict"""
    if _llm_service_func:
        return _llm_service_func()
    return None







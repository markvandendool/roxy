#!/usr/bin/env python3
"""
Fix LLM initialization by handling email module conflict properly
"""
import sys
import os

# The issue: services/email/ shadows Python's email module
# Solution: Import LLM service before adding services to path

# Save original path
original_path = sys.path.copy()

# Remove services if present
if '/opt/roxy/services' in sys.path:
    sys.path.remove('/opt/roxy/services')

# Import LLM service (needs standard library email)
try:
    # Change to services directory temporarily
    old_cwd = os.getcwd()
    os.chdir('/opt/roxy/services')
    
    # Import with services NOT in path
    from llm_service import get_llm_service
    
    # Restore
    os.chdir(old_cwd)
    sys.path = original_path
    
    # Test
    llm = get_llm_service()
    print(f"✅ LLM service initialized: {llm.is_available()}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.path = original_path




















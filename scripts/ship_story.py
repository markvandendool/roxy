#!/usr/bin/env python3
"""
ROXY Story Shipping - Implement and ship a feature
This tests ROXY's ability to understand requirements and implement code
"""
import sys
import asyncio
import os
sys.path.insert(0, '/opt/roxy/services')

from roxy_interface import RoxyInterface

async def ship_story():
    """Have ROXY implement and ship a story"""
    interface = RoxyInterface()
    
    print("="*70)
    print("📦 SHIPPING STORY: Real-time Status Dashboard")
    print("="*70)
    print("\nStory: Create a simple status dashboard API endpoint")
    print("Requirements:")
    print("  1. FastAPI endpoint at /api/status")
    print("  2. Returns system health, ROXY status, and metrics")
    print("  3. JSON response format")
    print("  4. Include timestamp")
    print("\nAsking ROXY to implement...\n")
    
    story_prompt = """I need you to implement a status dashboard API endpoint. 

Requirements:
1. Create a FastAPI endpoint at /api/status
2. It should return:
   - System health status
   - ROXY service status (running/stopped)
   - Memory statistics (conversations, facts)
   - Timestamp
3. Use JSON format
4. File should be at /opt/roxy/services/api/status_dashboard.py

Please provide the complete implementation code."""
    
    print("ROXY: Implementing status dashboard...")
    response = await interface.chat_terminal(story_prompt)
    
    print("\n" + "="*70)
    print("ROXY RESPONSE:")
    print("="*70)
    print(response)
    print("\n" + "="*70)
    
    # Extract code from response
    if "```python" in response or "def " in response or "from fastapi" in response:
        print("✅ ROXY provided code implementation!")
        
        # Try to extract and save code
        code_start = response.find("```python")
        if code_start != -1:
            code = response[code_start + 9:]
            code_end = code.find("```")
            if code_end != -1:
                code = code[:code_end].strip()
                
                # Save the file
                os.makedirs("/opt/roxy/services/api", exist_ok=True)
                with open("/opt/roxy/services/api/status_dashboard.py", "w") as f:
                    f.write(code)
                
                print(f"\n✅ Code saved to /opt/roxy/services/api/status_dashboard.py")
                print(f"📝 Code length: {len(code)} characters")
                
                # Validate code
                try:
                    compile(code, "/opt/roxy/services/api/status_dashboard.py", "exec")
                    print("✅ Code syntax is valid!")
                except SyntaxError as e:
                    print(f"⚠️ Syntax error: {e}")
    else:
        print("⚠️ ROXY response doesn't contain clear code")
    
    return response

if __name__ == "__main__":
    result = asyncio.run(ship_story())
    print("\n✅ Story shipping test complete!")




















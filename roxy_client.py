#!/usr/bin/env python3
"""
ROXY Client - Interactive Terminal Interface
Connects to roxy_core via HTTP IPC

Invoked by GNOME keyboard shortcut (Ctrl+Space)
"""

import sys
import json
import urllib.request
import urllib.error
import os
from pathlib import Path

# Configuration - single source of truth
ROXY_DIR = Path.home() / ".roxy"
CONFIG_FILE = ROXY_DIR / "config.json"
TOKEN_FILE = ROXY_DIR / "secret.token"

# Load config
if CONFIG_FILE.exists():
    with open(CONFIG_FILE) as f:
        config = json.load(f)
        host = config.get("host", "127.0.0.1")
        port = int(os.getenv("ROXY_PORT", config.get("port", 8766)))
        CORE_URL = f"http://{host}:{port}"
else:
    port = int(os.getenv("ROXY_PORT", 8766))
    CORE_URL = f"http://127.0.0.1:{port}"

# Load auth token
if TOKEN_FILE.exists():
    AUTH_TOKEN = TOKEN_FILE.read_text().strip()
else:
    AUTH_TOKEN = None


def check_core_running():
    """Check if ROXY core is running"""
    try:
        req = urllib.request.Request(f"{CORE_URL}/health")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            return data.get('status') == 'ok'
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def send_command(command, stream=False):
    """Send command to ROXY core and get response"""
    if stream:
        return send_command_streaming(command)
    
    try:
        data = json.dumps({"command": command}).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        
        # Add auth token if available
        if AUTH_TOKEN:
            headers['X-ROXY-Token'] = AUTH_TOKEN
        
        req = urllib.request.Request(
            f"{CORE_URL}/run",
            data=data,
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result.get('result', 'No response')
            
    except urllib.error.HTTPError as e:
        return f"ERROR: HTTP {e.code} - {e.reason}"
    except urllib.error.URLError as e:
        return f"ERROR: Connection failed - {e.reason}"
    except TimeoutError:
        return "ERROR: Request timed out"
    except Exception as e:
        return f"ERROR: {str(e)}"


def send_command_streaming(command):
    """Send command and stream response via SSE"""
    try:
        import urllib.parse
        url = f"{CORE_URL}/stream?command={urllib.parse.quote(command)}"
        headers = {}
        
        # Add auth token if available
        if AUTH_TOKEN:
            headers['X-ROXY-Token'] = AUTH_TOKEN
        
        req = urllib.request.Request(url, headers=headers)
        
        response_parts = []
        with urllib.request.urlopen(req, timeout=60) as response:
            buffer = ""
            for line in response:
                line = line.decode('utf-8')
                buffer += line
                
                # Process complete SSE events
                if buffer.endswith('\n\n'):
                    for event_line in buffer.strip().split('\n\n'):
                        if not event_line:
                            continue
                        
                        event_type = None
                        event_data = None
                        
                        for part in event_line.split('\n'):
                            if part.startswith('event:'):
                                event_type = part[6:].strip()
                            elif part.startswith('data:'):
                                data_str = part[5:].strip()
                                try:
                                    event_data = json.loads(data_str)
                                except:
                                    event_data = data_str
                        
                        if event_type == 'data' and event_data:
                            chunk = event_data.get('chunk', '')
                            if chunk:
                                response_parts.append(chunk)
                                # Print chunk as it arrives (streaming display)
                                print(chunk, end='', flush=True)
                        elif event_type == 'complete':
                            print()  # Newline after streaming
                        elif event_type == 'error':
                            error_msg = event_data.get('error', 'Unknown error') if isinstance(event_data, dict) else str(event_data)
                            return f"ERROR: {error_msg}"
                    
                    buffer = ""
        
        return ''.join(response_parts)
        
    except Exception as e:
        return f"ERROR: Streaming failed - {str(e)}"


def main():
    """Interactive terminal chat"""
    print("=" * 60)
    print("ROXY TERMINAL CHAT")
    print("=" * 60)
    
    # Check if core is running
    if not check_core_running():
        print("\n❌ ERROR: ROXY core is not running")
        print("\nStart the service with:")
        print("  systemctl --user start roxy-core")
        print("\nCheck status with:")
        print("  systemctl --user status roxy-core")
        print("\nView logs with:")
        print("  journalctl --user -u roxy-core -n 50")
        print("\n" + "=" * 60)
        sys.exit(1)
    
    print("\n✓ Connected to ROXY core")
    print("\nType your commands or questions.")
    print("Type 'exit', 'quit', or press Ctrl+D to close.")
    print("\n💡 After each response, you'll be asked for feedback:")
    print("   u = 👍 thumbs up    d = 👎 thumbs down    c = ✏️ correction    Enter = skip\n")
    
    # Interactive loop
    try:
        while True:
            try:
                user_input = input("🎤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Closing ROXY chat")
                    break
                
                # Send to core and get response (use streaming for better UX)
                print("🤖 ROXY: ", end='', flush=True)
                response = send_command(user_input, stream=True)
                if not response or response.startswith("ERROR"):
                    # Fallback to non-streaming if streaming fails
                    response = send_command(user_input, stream=False)
                    print(f"🤖 ROXY: {response}\n")
                else:
                    print()  # Newline after streaming
                
                # Feedback with keyboard shortcuts (blocking - wait for user)
                # User can press: u=👍, d=👎, c=correction, or Enter to skip
                try:
                    feedback = input("\n👍 u=up  👎 d=down  ✏️ c=correction  ⏭️ Enter=skip: ").strip().lower()
                    
                    if feedback in ['u', '👍', 'thumbs up', 'up', 'good', 'yes']:
                        from pathlib import Path
                        import sys
                        ROXY_DIR = Path.home() / ".roxy"
                        sys.path.insert(0, str(ROXY_DIR))
                        from feedback import get_feedback_collector
                        collector = get_feedback_collector()
                        collector.record_feedback(user_input, response, "thumbs_up")
                        print("✓ Thanks!")
                    elif feedback in ['d', '👎', 'thumbs down', 'down', 'bad', 'no']:
                        from pathlib import Path
                        import sys
                        ROXY_DIR = Path.home() / ".roxy"
                        sys.path.insert(0, str(ROXY_DIR))
                        from feedback import get_feedback_collector
                        collector = get_feedback_collector()
                        collector.record_feedback(user_input, response, "thumbs_down")
                        print("✓ Noted - thanks for feedback!")
                    elif feedback in ['c', '✏️', 'correction']:
                        correction = input("Enter correction: ").strip()
                        if correction:
                            from pathlib import Path
                            import sys
                            ROXY_DIR = Path.home() / ".roxy"
                            sys.path.insert(0, str(ROXY_DIR))
                            from feedback import get_feedback_collector
                            collector = get_feedback_collector()
                            collector.record_feedback(user_input, response, "correction", correction=correction)
                            print("✓ Correction recorded")
                    # Enter or empty = skip (no feedback)
                except (EOFError, KeyboardInterrupt):
                    pass  # Skip feedback on Ctrl+D or Ctrl+C
                except Exception as e:
                    pass  # Silently fail if feedback collection fails
                
            except EOFError:
                # Ctrl+D pressed
                print("\n\n👋 Closing ROXY chat")
                break
                
    except KeyboardInterrupt:
        # Ctrl+C pressed
        print("\n\n👋 Closing ROXY chat")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

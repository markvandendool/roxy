#!/usr/bin/env python3
"""
Enhanced feedback mechanism with keyboard shortcuts
This is a reference implementation showing how we could add
optional, non-intrusive feedback with keyboard shortcuts
"""

# Example: Optional feedback with keyboard shortcuts
# This would be added to the interactive loop

def handle_optional_feedback(user_input, response):
    """
    Optional feedback mechanism with keyboard shortcuts
    
    Usage:
    - After ROXY responds, user can optionally press:
      - 'u' or 'U' = thumbs up
      - 'd' or 'D' = thumbs down  
      - 'c' or 'C' = correction (then type correction)
      - Enter = skip (no feedback)
    
    This would be non-blocking - user can just press Enter to skip
    """
    import sys
    from pathlib import Path
    
    # Show brief hint (only once per session or configurable)
    print("\n[Optional: u=👍 d=👎 c=✏️ Enter=skip] ", end='', flush=True)
    
    # Use getch for single-key input (no Enter required)
    try:
        import termios
        import tty
        
        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        
        try:
            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        # Process single keypress
        if ch.lower() == 'u':
            # Thumbs up
            record_feedback(user_input, response, "thumbs_up")
            print("✓ Thanks!")
        elif ch.lower() == 'd':
            # Thumbs down
            record_feedback(user_input, response, "thumbs_down")
            print("✓ Noted - thanks for feedback!")
        elif ch.lower() == 'c':
            # Correction - need to get full input
            print("\nEnter correction: ", end='', flush=True)
            correction = input().strip()
            if correction:
                record_feedback(user_input, response, "correction", correction)
                print("✓ Correction recorded")
        # Enter or any other key = skip (no feedback)
        
    except (ImportError, Exception):
        # Fallback: use regular input if termios not available
        # But make it very brief and optional
        pass


def record_feedback(user_input, response, feedback_type, correction=None):
    """Record feedback to the feedback system"""
    try:
        from pathlib import Path
        import sys
        ROXY_DIR = Path.home() / ".roxy"
        sys.path.insert(0, str(ROXY_DIR))
        from feedback import get_feedback_collector
        collector = get_feedback_collector()
        collector.record_feedback(user_input, response, feedback_type, correction=correction)
    except Exception as e:
        pass  # Silently fail














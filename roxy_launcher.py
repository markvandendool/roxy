#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🚀 ROXY LAUNCHER - Ultra Premium UI Suite                                  ║
║                                                                              ║
║   Your gateway to the ROXY AI Operating System                               ║
║                                                                              ║
║   Launch Modes:                                                              ║
║   [1] 🌐 Web UI       - Browser-based dashboard (Open-WebUI style)           ║
║   [2] 💻 Terminal UI  - Premium Textual TUI (for terminal lovers)            ║
║   [3] 🎤 Voice Mode   - Real-time voice conversation                         ║
║   [4] 🌍 Voice Web    - Browser-based voice chat with WebRTC                 ║
║   [5] ⚡ Quick Chat   - Fast CLI for one-off queries                         ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import signal
from pathlib import Path

# Colors
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background
    BG_BLACK = "\033[40m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"


def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_banner():
    """Print the ultra premium banner."""
    C = Colors
    banner = f"""
{C.BRIGHT_MAGENTA}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   {C.BRIGHT_CYAN}██████╗  ██████╗ ██╗  ██╗██╗   ██╗{C.BRIGHT_MAGENTA}                                       ║
║   {C.BRIGHT_CYAN}██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝{C.BRIGHT_MAGENTA}                                       ║
║   {C.BRIGHT_CYAN}██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ {C.BRIGHT_MAGENTA}                                       ║
║   {C.BRIGHT_CYAN}██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  {C.BRIGHT_MAGENTA}                                       ║
║   {C.BRIGHT_CYAN}██║  ██║╚██████╔╝██╔╝ ██╗   ██║   {C.BRIGHT_MAGENTA}                                       ║
║   {C.BRIGHT_CYAN}╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   {C.BRIGHT_MAGENTA}                                       ║
║                                                                              ║
║         {C.BRIGHT_WHITE}🚀 AI OPERATING SYSTEM - ULTRA PREMIUM UI SUITE 🚀{C.BRIGHT_MAGENTA}               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝{C.RESET}
"""
    print(banner)


def print_menu():
    """Print the launcher menu."""
    C = Colors
    menu = f"""
{C.BRIGHT_WHITE}  Select your interface:{C.RESET}

  {C.BRIGHT_GREEN}[1]{C.RESET} 🌐 {C.BRIGHT_WHITE}Web UI{C.RESET}         {C.DIM}Browser-based dashboard with voice support{C.RESET}
                       {C.CYAN}http://localhost:8780{C.RESET}

  {C.BRIGHT_GREEN}[2]{C.RESET} 💻 {C.BRIGHT_WHITE}Terminal UI{C.RESET}    {C.DIM}Premium Textual TUI for terminal lovers{C.RESET}
                       {C.CYAN}Full dashboard, experts panel, chat{C.RESET}

  {C.BRIGHT_GREEN}[3]{C.RESET} 🎤 {C.BRIGHT_WHITE}Voice Mode{C.RESET}     {C.DIM}Real-time voice conversation{C.RESET}
                       {C.CYAN}faster-whisper STT + edge-tts TTS{C.RESET}

  {C.BRIGHT_GREEN}[4]{C.RESET} 🌍 {C.BRIGHT_WHITE}Voice Web{C.RESET}      {C.DIM}Browser-based voice with WebRTC{C.RESET}
                       {C.CYAN}http://localhost:8769{C.RESET}

  {C.BRIGHT_GREEN}[5]{C.RESET} ⚡ {C.BRIGHT_WHITE}Quick Chat{C.RESET}     {C.DIM}Fast CLI for one-off queries{C.RESET}
                       {C.CYAN}Type and get instant responses{C.RESET}

  {C.BRIGHT_RED}[q]{C.RESET} 🚪 {C.BRIGHT_WHITE}Quit{C.RESET}

"""
    print(menu)


def check_roxy_running() -> bool:
    """Check if ROXY server is running."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8766))
        sock.close()
        return result == 0
    except Exception:
        return False


def print_status():
    """Print ROXY status."""
    C = Colors
    is_running = check_roxy_running()
    if is_running:
        print(f"  {C.BRIGHT_GREEN}● ROXY Server: ONLINE{C.RESET} {C.DIM}(127.0.0.1:8766){C.RESET}")
    else:
        print(f"  {C.BRIGHT_RED}● ROXY Server: OFFLINE{C.RESET}")
        print(f"    {C.YELLOW}Start with: roxy_server.py{C.RESET}")


def launch_web_ui():
    """Launch the Web UI."""
    C = Colors
    print(f"\n{C.BRIGHT_CYAN}🌐 Launching Web UI...{C.RESET}")
    print(f"{C.DIM}   Opening http://localhost:8780{C.RESET}\n")
    
    roxy_dir = Path.home() / ".roxy"
    web_ui = roxy_dir / "roxy_web_ui.py"
    
    if not web_ui.exists():
        print(f"{C.BRIGHT_RED}❌ Web UI not found at {web_ui}{C.RESET}")
        return
    
    # Start the web server
    proc = subprocess.Popen(
        [sys.executable, str(web_ui)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(roxy_dir)
    )
    
    # Give it a moment to start
    import time
    time.sleep(2)
    
    # Open browser
    try:
        import webbrowser
        webbrowser.open("http://localhost:8780")
    except Exception:
        pass
    
    print(f"{C.BRIGHT_GREEN}✓ Web UI started! Press Ctrl+C to stop.{C.RESET}\n")
    
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            print(line.decode().rstrip())
    except KeyboardInterrupt:
        proc.terminate()
        print(f"\n{C.BRIGHT_YELLOW}Web UI stopped.{C.RESET}")


def launch_terminal_ui():
    """Launch the Terminal UI."""
    C = Colors
    print(f"\n{C.BRIGHT_CYAN}💻 Launching Terminal UI...{C.RESET}\n")
    
    roxy_dir = Path.home() / ".roxy"
    tui = roxy_dir / "roxy_ui.py"
    
    if not tui.exists():
        print(f"{C.BRIGHT_RED}❌ Terminal UI not found at {tui}{C.RESET}")
        return
    
    try:
        subprocess.run([sys.executable, str(tui)], cwd=str(roxy_dir))
    except KeyboardInterrupt:
        pass


def launch_voice_mode():
    """Launch voice mode."""
    C = Colors
    print(f"\n{C.BRIGHT_CYAN}🎤 Launching Voice Mode...{C.RESET}\n")
    
    roxy_dir = Path.home() / ".roxy"
    voice = roxy_dir / "realtime_talk.py"
    
    if not voice.exists():
        # Try alternative
        voice = roxy_dir / "realtime_voice.py"
    
    if not voice.exists():
        print(f"{C.BRIGHT_RED}❌ Voice mode not found{C.RESET}")
        return
    
    try:
        subprocess.run([sys.executable, str(voice)], cwd=str(roxy_dir))
    except KeyboardInterrupt:
        pass


def launch_voice_web():
    """Launch WebRTC voice mode."""
    C = Colors
    print(f"\n{C.BRIGHT_CYAN}🌍 Launching Voice Web...{C.RESET}")
    print(f"{C.DIM}   Opening http://localhost:8769{C.RESET}\n")
    
    roxy_dir = Path.home() / ".roxy"
    voice_web = roxy_dir / "webrtc_voice_server.py"
    
    if not voice_web.exists():
        print(f"{C.BRIGHT_RED}❌ Voice Web not found at {voice_web}{C.RESET}")
        return
    
    # Start the server
    proc = subprocess.Popen(
        [sys.executable, str(voice_web)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(roxy_dir)
    )
    
    import time
    time.sleep(2)
    
    # Open browser
    try:
        import webbrowser
        webbrowser.open("http://localhost:8769")
    except Exception:
        pass
    
    print(f"{C.BRIGHT_GREEN}✓ Voice Web started! Press Ctrl+C to stop.{C.RESET}\n")
    
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            print(line.decode().rstrip())
    except KeyboardInterrupt:
        proc.terminate()
        print(f"\n{C.BRIGHT_YELLOW}Voice Web stopped.{C.RESET}")


def launch_quick_chat():
    """Launch quick CLI chat."""
    C = Colors
    print(f"\n{C.BRIGHT_CYAN}⚡ Quick Chat Mode{C.RESET}")
    print(f"{C.DIM}Type your message and press Enter. Type 'exit' to quit.{C.RESET}\n")
    
    try:
        import httpx
    except ImportError:
        print(f"{C.BRIGHT_RED}❌ httpx not installed. Run: pip install httpx{C.RESET}")
        return
    
    token_path = Path.home() / ".roxy" / "secret.token"
    token = token_path.read_text().strip() if token_path.exists() else ""
    
    while True:
        try:
            user_input = input(f"{C.BRIGHT_GREEN}You>{C.RESET} ").strip()
            
            if user_input.lower() in ('exit', 'quit', 'q'):
                break
            
            if not user_input:
                continue
            
            print(f"{C.BRIGHT_CYAN}🤖 ROXY>{C.RESET} ", end="", flush=True)
            
            try:
                with httpx.Client(timeout=120) as client:
                    resp = client.post(
                        "http://127.0.0.1:8766/expert",
                        headers={"X-ROXY-Token": token},
                        json={"message": user_input}
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        print(data.get("response", "No response"))
                        expert = data.get("expert")
                        if expert:
                            print(f"{C.DIM}[via {expert}]{C.RESET}")
                    else:
                        print(f"{C.BRIGHT_RED}Error: {resp.text}{C.RESET}")
            except Exception as e:
                print(f"{C.BRIGHT_RED}Connection error: {e}{C.RESET}")
            
            print()
            
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    print(f"\n{C.BRIGHT_YELLOW}Goodbye! 👋{C.RESET}")


def main():
    """Main launcher function."""
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    while True:
        clear_screen()
        print_banner()
        print_status()
        print_menu()
        
        try:
            choice = input(f"  {Colors.BRIGHT_WHITE}Enter choice [1-5/q]:{Colors.RESET} ").strip().lower()
            
            if choice == '1':
                launch_web_ui()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")
            elif choice == '2':
                launch_terminal_ui()
            elif choice == '3':
                launch_voice_mode()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")
            elif choice == '4':
                launch_voice_web()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")
            elif choice == '5':
                launch_quick_chat()
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.RESET}")
            elif choice in ('q', 'quit', 'exit'):
                clear_screen()
                print(f"\n{Colors.BRIGHT_MAGENTA}👋 Thanks for using ROXY!{Colors.RESET}\n")
                break
            else:
                print(f"\n{Colors.BRIGHT_YELLOW}Invalid choice. Please try again.{Colors.RESET}")
                import time
                time.sleep(1)
                
        except (KeyboardInterrupt, EOFError):
            clear_screen()
            print(f"\n{Colors.BRIGHT_MAGENTA}👋 Thanks for using ROXY!{Colors.RESET}\n")
            break


if __name__ == "__main__":
    main()

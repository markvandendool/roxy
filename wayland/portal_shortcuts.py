#!/usr/bin/env python3
"""
Rocky Wayland - Portal API Global Shortcuts
Story: RAF-018
Target: Wayland-safe global hotkeys via xdg-desktop-portal

Replaces blocked X11 keyboard grab with Portal API.
"""

import asyncio
import json
import os
from typing import Callable, Dict, Optional

try:
    from dbus_next.aio import MessageBus
    from dbus_next import Variant, BusType
except ImportError:
    print("ERROR: dbus-next not installed")
    print("Run: pip install dbus-next")
    exit(1)


class PortalShortcuts:
    """
    Wayland-safe global shortcuts using xdg-desktop-portal.

    Requires:
    - xdg-desktop-portal (usually pre-installed on modern Linux)
    - GNOME/KDE/Sway with portal support
    """

    PORTAL_BUS = "org.freedesktop.portal.Desktop"
    PORTAL_PATH = "/org/freedesktop/portal/desktop"
    SHORTCUT_INTERFACE = "org.freedesktop.portal.GlobalShortcuts"

    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.portal = None
        self.session_handle: Optional[str] = None
        self.shortcuts: Dict[str, Callable] = {}
        self.running = False

        print("[ROXY.WAYLAND] Portal Shortcuts initialized")

    async def connect(self):
        """Connect to D-Bus session bus."""
        self.bus = await MessageBus(bus_type=BusType.SESSION).connect()

        # Get portal proxy
        introspection = await self.bus.introspect(
            self.PORTAL_BUS,
            self.PORTAL_PATH
        )

        proxy = self.bus.get_proxy_object(
            self.PORTAL_BUS,
            self.PORTAL_PATH,
            introspection
        )

        self.portal = proxy.get_interface(self.SHORTCUT_INTERFACE)
        print("[ROXY.WAYLAND] Connected to portal")

    async def create_session(self):
        """Create a shortcut session."""
        # Generate session token
        import secrets
        session_token = f"roxy_{secrets.token_hex(8)}"

        options = {
            "handle_token": Variant("s", session_token),
            "session_handle_token": Variant("s", f"session_{session_token}"),
        }

        result = await self.portal.call_create_session(options)
        print(f"[ROXY.WAYLAND] Session created: {result}")

        # The session handle is returned in the response
        self.session_handle = result

    async def register_shortcut(
        self,
        shortcut_id: str,
        description: str,
        trigger: str,  # e.g., "<Super>r" or "<Control><Alt>r"
        callback: Callable,
    ):
        """Register a global shortcut."""
        if not self.session_handle:
            await self.create_session()

        self.shortcuts[shortcut_id] = callback

        shortcuts = {
            shortcut_id: {
                "description": Variant("s", description),
                "preferred_trigger": Variant("s", trigger),
            }
        }

        options = {
            "handle_token": Variant("s", f"bind_{shortcut_id}"),
        }

        try:
            result = await self.portal.call_bind_shortcuts(
                self.session_handle,
                shortcuts,
                "",  # parent window
                options
            )
            print(f"[ROXY.WAYLAND] Shortcut registered: {shortcut_id} -> {trigger}")
            return True
        except Exception as e:
            print(f"[ROXY.WAYLAND] Failed to register shortcut: {e}")
            return False

    async def listen(self):
        """Listen for shortcut activations."""
        if not self.portal:
            await self.connect()

        self.running = True

        # Connect to Activated signal
        def on_activated(session_handle, shortcut_id, timestamp, options):
            print(f"[ROXY.WAYLAND] Shortcut activated: {shortcut_id}")
            if shortcut_id in self.shortcuts:
                self.shortcuts[shortcut_id]()

        self.portal.on_activated(on_activated)

        print("[ROXY.WAYLAND] Listening for shortcuts...")

        while self.running:
            await asyncio.sleep(0.1)

    async def close(self):
        """Close the session."""
        self.running = False
        if self.bus:
            self.bus.disconnect()


class X11Fallback:
    """
    X11 fallback for non-Wayland sessions.

    Uses python-xlib for global hotkey capture.
    """

    def __init__(self):
        self.shortcuts: Dict[str, Callable] = {}
        self.running = False

        try:
            from Xlib import X, XK
            from Xlib.display import Display
            self.X = X
            self.XK = XK
            self.display = Display()
            self.root = self.display.screen().root
            self.x11_available = True
            print("[ROXY.X11] X11 fallback initialized")
        except ImportError:
            self.x11_available = False
            print("[ROXY.X11] python-xlib not available")

    def register_shortcut(
        self,
        shortcut_id: str,
        trigger: str,
        callback: Callable,
    ):
        """Register an X11 global hotkey."""
        if not self.x11_available:
            return False

        # Parse trigger (e.g., "<Super>r")
        modifiers = 0
        key = None

        if "<Super>" in trigger or "<Mod4>" in trigger:
            modifiers |= self.X.Mod4Mask
            trigger = trigger.replace("<Super>", "").replace("<Mod4>", "")
        if "<Control>" in trigger or "<Ctrl>" in trigger:
            modifiers |= self.X.ControlMask
            trigger = trigger.replace("<Control>", "").replace("<Ctrl>", "")
        if "<Alt>" in trigger or "<Mod1>" in trigger:
            modifiers |= self.X.Mod1Mask
            trigger = trigger.replace("<Alt>", "").replace("<Mod1>", "")
        if "<Shift>" in trigger:
            modifiers |= self.X.ShiftMask
            trigger = trigger.replace("<Shift>", "")

        # Get keycode
        keysym = self.XK.string_to_keysym(trigger.strip())
        keycode = self.display.keysym_to_keycode(keysym)

        if keycode:
            self.root.grab_key(
                keycode,
                modifiers,
                True,
                self.X.GrabModeAsync,
                self.X.GrabModeAsync
            )
            self.shortcuts[(keycode, modifiers)] = callback
            print(f"[ROXY.X11] Registered: {shortcut_id}")
            return True
        return False

    def listen(self):
        """Listen for X11 key events."""
        if not self.x11_available:
            return

        self.running = True
        print("[ROXY.X11] Listening for hotkeys...")

        while self.running:
            event = self.display.next_event()
            if event.type == self.X.KeyPress:
                key = (event.detail, event.state & (
                    self.X.Mod4Mask | self.X.ControlMask |
                    self.X.Mod1Mask | self.X.ShiftMask
                ))
                if key in self.shortcuts:
                    self.shortcuts[key]()


class RoxyShortcuts:
    """
    Unified shortcut manager with automatic Wayland/X11 detection.
    """

    def __init__(self):
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "x11")
        print(f"[ROXY.SHORTCUTS] Session type: {self.session_type}")

        if self.session_type == "wayland":
            self.backend = PortalShortcuts()
        else:
            self.backend = X11Fallback()

    async def register(
        self,
        shortcut_id: str,
        description: str,
        trigger: str,
        callback: Callable,
    ):
        """Register a shortcut (auto-detects backend)."""
        if isinstance(self.backend, PortalShortcuts):
            await self.backend.connect()
            return await self.backend.register_shortcut(
                shortcut_id, description, trigger, callback
            )
        else:
            return self.backend.register_shortcut(
                shortcut_id, trigger, callback
            )

    async def listen(self):
        """Start listening for shortcuts."""
        if isinstance(self.backend, PortalShortcuts):
            await self.backend.listen()
        else:
            # Run X11 listener in thread
            import threading
            thread = threading.Thread(target=self.backend.listen, daemon=True)
            thread.start()
            while self.backend.running:
                await asyncio.sleep(0.1)


async def main():
    """Demo the shortcut manager."""
    shortcuts = RoxyShortcuts()

    def on_roxy_activate():
        print("[ROXY] ACTIVATED!")

    def on_roxy_help():
        print("[ROXY] HELP!")

    await shortcuts.register(
        "roxy-activate",
        "Activate ROXY",
        "<Super>r",
        on_roxy_activate,
    )

    await shortcuts.register(
        "roxy-help",
        "ROXY Help",
        "<Super><Shift>r",
        on_roxy_help,
    )

    print("[ROXY.SHORTCUTS] Press Super+R to activate ROXY")
    await shortcuts.listen()


if __name__ == "__main__":
    asyncio.run(main())

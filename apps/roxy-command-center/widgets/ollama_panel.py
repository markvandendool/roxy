#!/usr/bin/env python3
"""
Ollama panel widget with pool tabs.
ROXY-CMD-STORY-015: Pool tabs (W5700X/6900XT), model list, VRAM display.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from typing import Optional, Callable, Dict, List, Any
import json
import subprocess

class ModelCard(Gtk.Box):
    """Individual model card within a pool."""
    
    def __init__(self, model_name: str, vram_gb: float = 0, 
                 on_unload: Optional[Callable[[str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.model_name = model_name
        self.on_unload = on_unload
        
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        # Model info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)
        
        name_label = Gtk.Label(label=model_name)
        name_label.add_css_class("title-4")
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)
        
        vram_label = Gtk.Label(label=f"{vram_gb:.1f} GB VRAM" if vram_gb > 0 else "VRAM: N/A")
        vram_label.add_css_class("dim-label")
        vram_label.set_halign(Gtk.Align.START)
        info_box.append(vram_label)
        
        self.append(info_box)
        
        # Unload button
        unload_btn = Gtk.Button(label="Unload")
        unload_btn.add_css_class("destructive-action")
        unload_btn.connect("clicked", self._on_unload_clicked)
        self.append(unload_btn)
    
    def _on_unload_clicked(self, button):
        """Handle unload button click."""
        if self.on_unload:
            self.on_unload(self.model_name)


class PoolTab(Gtk.Box):
    """Content for a single pool tab."""
    
    def __init__(self, pool_name: str, port: int,
                 on_model_unload: Optional[Callable[[str, str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.pool_name = pool_name
        self.port = port
        self.on_model_unload = on_model_unload
        self.model_cards: Dict[str, ModelCard] = {}
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        
        self.status_icon = Gtk.Image()
        self.status_icon.set_pixel_size(16)
        header.append(self.status_icon)
        
        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_hexpand(True)
        header.append(self.status_label)
        
        self.vram_badge = Gtk.Label()
        self.vram_badge.add_css_class("pill")
        header.append(self.vram_badge)
        
        self.append(header)
        
        # Separator
        self.append(Gtk.Separator())
        
        # Model list (scrollable)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.model_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(self.model_list)
        
        self.append(scrolled)
        
        # Empty state
        self.empty_label = Gtk.Label(label="No models loaded")
        self.empty_label.add_css_class("dim-label")
        self.empty_label.set_margin_top(24)
        self.empty_label.set_margin_bottom(24)
        self.model_list.append(self.empty_label)
        
        # Initial state
        self.set_status("unknown", 0, 0)
    
    def set_status(self, status: str, model_count: int, vram_used_gb: float):
        """Update pool status display."""
        if status == "running" or status == "ok":
            self.status_icon.set_from_icon_name("emblem-ok-symbolic")
            self.status_label.set_text(f"{self.pool_name} • {model_count} models loaded")
        elif status == "stopped" or status == "unhealthy":
            self.status_icon.set_from_icon_name("dialog-error-symbolic")
            self.status_label.set_text(f"{self.pool_name} • Offline")
        else:
            self.status_icon.set_from_icon_name("dialog-question-symbolic")
            self.status_label.set_text(f"{self.pool_name} • Unknown")
        
        self.vram_badge.set_text(f"{vram_used_gb:.1f} GB")
    
    def update_models(self, models: List[Dict[str, Any]]):
        """Update model list."""
        # Clear existing cards
        for card in self.model_cards.values():
            self.model_list.remove(card)
        self.model_cards.clear()
        
        if not models:
            self.empty_label.set_visible(True)
            return
        
        self.empty_label.set_visible(False)
        
        for model in models:
            name = model.get("name", "Unknown")
            vram = model.get("vram_gb", 0)
            
            card = ModelCard(
                model_name=name,
                vram_gb=vram,
                on_unload=lambda n: self._on_model_unload(n)
            )
            self.model_cards[name] = card
            self.model_list.append(card)
    
    def _on_model_unload(self, model_name: str):
        """Handle model unload request."""
        if self.on_model_unload:
            self.on_model_unload(self.pool_name, model_name)


class OllamaPanel(Gtk.Box):
    """
    Ollama management panel with pool tabs.

    Shows:
    - W5700X pool tab (port 11434)
    - 6900XT pool tab (port 11435)
    - Model list per pool
    - Unload actions
    """
    
    def __init__(self, on_model_unload: Optional[Callable[[str, str], None]] = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.on_model_unload = on_model_unload
        
        # Card styling
        self.add_css_class("card")
        self.set_margin_top(6)
        self.set_margin_bottom(6)
        self.set_margin_start(6)
        self.set_margin_end(6)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_end(12)
        
        title = Gtk.Label(label="Ollama Pools")
        title.add_css_class("title-3")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh models")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.append(refresh_btn)
        
        self.append(header)
        
        # Tab view
        self.notebook = Gtk.Notebook()
        self.notebook.set_margin_top(8)
        
        # W5700X pool tab (port 11434, accepts BIG alias)
        self.w5700x_tab = PoolTab("W5700X", 11434, self._on_model_unload_request)
        w5700x_label = Gtk.Label(label="W5700X (:11434)")
        w5700x_label.add_css_class("accent-big")
        self.notebook.append_page(self.w5700x_tab, w5700x_label)

        # 6900XT pool tab (port 11435, accepts FAST alias)
        self.xt6900_tab = PoolTab("6900XT", 11435, self._on_model_unload_request)
        xt6900_label = Gtk.Label(label="6900XT (:11435)")
        xt6900_label.add_css_class("accent-fast")
        self.notebook.append_page(self.xt6900_tab, xt6900_label)
        
        self.append(self.notebook)
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        # Will be called by parent's update cycle
        pass
    
    def _on_model_unload_request(self, pool: str, model: str):
        """Handle model unload request with confirmation."""
        window = self.get_root()
        if not isinstance(window, Gtk.Window):
            return
        
        dialog = Adw.MessageDialog(
            transient_for=window,
            heading="Unload Model?",
            body=f"Are you sure you want to unload {model} from {pool} pool?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("unload", "Unload")
        dialog.set_response_appearance("unload", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        
        def on_response(d, response):
            if response == "unload" and self.on_model_unload:
                self.on_model_unload(pool, model)
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def update_from_daemon(self, data: dict):
        """Update from daemon response."""
        services = data.get("services", {})

        # W5700X pool (systemd: ollama_big, port 11434)
        w5700x_service = services.get("ollama_big", {})
        w5700x_health = w5700x_service.get("health", "unknown")
        w5700x_models = data.get("ollama_big_models", [])
        w5700x_vram = sum(m.get("vram_gb", 0) for m in w5700x_models)

        self.w5700x_tab.set_status(w5700x_health, len(w5700x_models), w5700x_vram)
        self.w5700x_tab.update_models(w5700x_models)

        # 6900XT pool (systemd: ollama_fast, port 11435)
        xt6900_service = services.get("ollama_fast", {})
        xt6900_health = xt6900_service.get("health", "unknown")
        xt6900_models = data.get("ollama_fast_models", [])
        xt6900_vram = sum(m.get("vram_gb", 0) for m in xt6900_models)

        self.xt6900_tab.set_status(xt6900_health, len(xt6900_models), xt6900_vram)
        self.xt6900_tab.update_models(xt6900_models)
    
    def update(self, data: dict):
        """Alias for update_from_daemon - compatibility method."""
        self.update_from_daemon(data)

#!/usr/bin/env python3
"""
ROXY OBS Voice Skill
Complete OBS control via natural language commands

Commands:
  Streaming:
    "start streaming", "go live", "begin stream"
    "stop streaming", "end stream", "go offline"
    
  Recording:
    "start recording", "begin recording", "record"
    "stop recording", "end recording", "save recording"
    "pause recording", "resume recording"
    
  Scenes:
    "switch to <scene>", "show <scene>", "go to <scene>"
    "next scene", "previous scene"
    "list scenes", "what scenes"
    
  Sources:
    "show <source>", "hide <source>"
    "mute <source>", "unmute <source>"
    "toggle <source>"
    
  Quick Actions:
    "brb", "be right back" -> Switch to BRB scene
    "starting soon" -> Switch to Starting scene
    "full screen", "game" -> Switch to Game/Main scene
    "camera", "face cam" -> Toggle camera
    "mute mic", "unmute mic"
    
  Virtual Camera:
    "start virtual camera", "start vcam"
    "stop virtual camera", "stop vcam"
    
  Replay Buffer:
    "start replay buffer"
    "stop replay buffer"
    "save replay", "clip that"
    
  Status:
    "obs status", "streaming status"
    "recording status", "what's recording"

Part of LUNA-000 CITADEL - BROADCAST organ
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import obsws_python as obs

# OBS WebSocket config
OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = os.environ.get("OBS_PASSWORD", "")

logger = logging.getLogger("roxy.obs")
if not logger.handlers:
    log_path = Path.home() / ".roxy" / "logs" / "roxy-core.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# Scene aliases - map natural language to actual scene names
SCENE_ALIASES = {
    # Starting scenes
    "starting": ["Starting Soon", "Starting", "Start", "Pre-Stream"],
    "starting soon": ["Starting Soon", "Starting", "Pre-Stream"],
    
    # Main scenes
    "main": ["Main", "Game", "Gameplay", "Full Screen", "Desktop"],
    "game": ["Game", "Gameplay", "Main", "Full Screen"],
    "gameplay": ["Gameplay", "Game", "Main"],
    "full screen": ["Full Screen", "Game", "Main", "Desktop"],
    "desktop": ["Desktop", "Screen", "Main"],
    
    # Camera scenes
    "camera": ["Camera", "Cam", "Face Cam", "Webcam", "Just Chatting"],
    "face cam": ["Face Cam", "Camera", "Cam", "Webcam"],
    "just chatting": ["Just Chatting", "Camera", "Chat"],
    "chat": ["Just Chatting", "Chat", "Camera"],
    
    # Break scenes
    "brb": ["BRB", "Be Right Back", "Break", "Away"],
    "break": ["BRB", "Break", "Be Right Back", "Away"],
    "be right back": ["Be Right Back", "BRB", "Break"],
    
    # End scenes
    "ending": ["Ending", "End", "Outro", "Goodbye"],
    "end": ["End", "Ending", "Outro"],
    "outro": ["Outro", "End", "Ending"],
    
    # Special
    "nexus": ["NEXUS", "Nexus", "Main"],
    "coding": ["Coding", "Code", "Dev", "Development"],
    "music": ["Music", "Audio", "Jam"],
}

class OBSSkill:
    def __init__(self):
        self.client = None
        self.connected = False
        self.scenes = []
        self.sources = []
        self.request_id = os.environ.get("ROXY_REQUEST_ID", "")

    def _log_command(self, action: str, status: str, detail: Optional[str] = None):
        rid = self.request_id or "n/a"
        message = f"[OBS] command {status} {action} requestId={rid}"
        if detail:
            safe_detail = detail.replace('\n', ' ').strip()
            if safe_detail:
                message = f"{message} detail={safe_detail}"
        log_fn = logger.info if status != "ERROR" else logger.error
        log_fn(message)
        
    def connect(self) -> bool:
        """Connect to OBS WebSocket"""
        try:
            rid = self.request_id or "n/a"
            logger.info(f"[OBS] connect attempt host={OBS_HOST} port={OBS_PORT} requestId={rid}")
            self.client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
            self.connected = True
            self._refresh_scenes()
            try:
                version = self.client.get_version()
                version_info = getattr(version, "obs_version", "unknown")
            except Exception:
                version_info = "unknown"
            logger.info(f"[OBS] connect OK serverVersion={version_info} requestId={rid}")
            return True
        except Exception as e:
            self.connected = False
            logger.error(f"[OBS] connect failed reason={e} requestId={rid}")
            return False
    
    def _refresh_scenes(self):
        """Refresh scene list"""
        try:
            resp = self.client.get_scene_list()
            self.scenes = [s["sceneName"] for s in resp.scenes]
        except:
            self.scenes = []
    
    def _find_scene(self, query: str) -> Optional[str]:
        """Find scene by name or alias"""
        query_lower = query.lower().strip()
        
        # Check aliases first
        if query_lower in SCENE_ALIASES:
            for candidate in SCENE_ALIASES[query_lower]:
                if candidate in self.scenes:
                    return candidate
        
        # Direct match
        for scene in self.scenes:
            if scene.lower() == query_lower:
                return scene
        
        # Partial match
        for scene in self.scenes:
            if query_lower in scene.lower():
                return scene
        
        return None
    
    def _find_source(self, query: str) -> Optional[str]:
        """Find source by name"""
        try:
            # Get current scene's sources
            current = self.client.get_current_program_scene()
            items = self.client.get_scene_item_list(current.current_program_scene_name)
            
            query_lower = query.lower()
            for item in items.scene_items:
                if query_lower in item["sourceName"].lower():
                    return item["sourceName"], item["sceneItemId"]
            return None, None
        except:
            return None, None
    
    # === Streaming ===
    
    def start_stream(self) -> str:
        if not self.connected:
            self._log_command("StartStream", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            status = self.client.get_stream_status()
            if status.output_active:
                self._log_command("StartStream", "NOOP", "already_active")
                return "Already streaming"
            self.client.start_stream()
            self._log_command("StartStream", "OK")
            return "Stream started! You're now live."
        except Exception as e:
            self._log_command("StartStream", "ERROR", str(e))
            return f"Failed to start stream: {e}"
    
    def stop_stream(self) -> str:
        if not self.connected:
            self._log_command("StopStream", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            status = self.client.get_stream_status()
            if not status.output_active:
                self._log_command("StopStream", "NOOP", "already_inactive")
                return "Not currently streaming"
            self.client.stop_stream()
            self._log_command("StopStream", "OK")
            return "Stream stopped. You're now offline."
        except Exception as e:
            self._log_command("StopStream", "ERROR", str(e))
            return f"Failed to stop stream: {e}"
    
    # === Recording ===
    
    def start_recording(self) -> str:
        if not self.connected:
            self._log_command("StartRecording", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            status = self.client.get_record_status()
            if status.output_active:
                self._log_command("StartRecording", "NOOP", "already_active")
                return "Already recording"
            self.client.start_record()
            self._log_command("StartRecording", "OK")
            return "Recording started"
        except Exception as e:
            self._log_command("StartRecording", "ERROR", str(e))
            return f"Failed to start recording: {e}"
    
    def stop_recording(self) -> str:
        if not self.connected:
            self._log_command("StopRecording", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            status = self.client.get_record_status()
            if not status.output_active:
                self._log_command("StopRecording", "NOOP", "already_inactive")
                return "Not currently recording"
            result = self.client.stop_record()
            output_path = getattr(result, "output_path", "unknown")
            self._log_command("StopRecording", "OK", output_path)
            return f"Recording saved: {result.output_path}"
        except Exception as e:
            self._log_command("StopRecording", "ERROR", str(e))
            return f"Failed to stop recording: {e}"
    
    def pause_recording(self) -> str:
        if not self.connected:
            self._log_command("PauseRecording", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.pause_record()
            self._log_command("PauseRecording", "OK")
            return "Recording paused"
        except Exception as e:
            self._log_command("PauseRecording", "ERROR", str(e))
            return f"Failed to pause: {e}"
    
    def resume_recording(self) -> str:
        if not self.connected:
            self._log_command("ResumeRecording", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.resume_record()
            self._log_command("ResumeRecording", "OK")
            return "Recording resumed"
        except Exception as e:
            self._log_command("ResumeRecording", "ERROR", str(e))
            return f"Failed to resume: {e}"
    
    # === Scenes ===
    
    def switch_scene(self, scene_name: str) -> str:
        if not self.connected:
            self._log_command("SwitchScene", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self._refresh_scenes()
            scene = self._find_scene(scene_name)
            if not scene:
                available = ", ".join(self.scenes[:5])
                detail = f"scene_not_found target={scene_name} available={available}"
                self._log_command("SwitchScene", "ERROR", detail)
                return f"Scene '{scene_name}' not found. Available: {', '.join(self.scenes[:5])}"
            self.client.set_current_program_scene(scene)
            self._log_command("SwitchScene", "OK", f"scene={scene}")
            return f"Switched to {scene}"
        except Exception as e:
            self._log_command("SwitchScene", "ERROR", str(e))
            return f"Failed to switch scene: {e}"
    
    def list_scenes(self) -> str:
        if not self.connected:
            self._log_command("ListScenes", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self._refresh_scenes()
            current = self.client.get_current_program_scene()
            scene_list = "\n".join([
                f"  {'>' if s == current.current_program_scene_name else ' '} {s}" 
                for s in self.scenes
            ])
            self._log_command("ListScenes", "OK", f"count={len(self.scenes)}")
            return f"Scenes:\n{scene_list}"
        except Exception as e:
            self._log_command("ListScenes", "ERROR", str(e))
            return f"Failed to list scenes: {e}"
    
    def next_scene(self) -> str:
        if not self.connected:
            self._log_command("NextScene", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self._refresh_scenes()
            current = self.client.get_current_program_scene().current_program_scene_name
            if current in self.scenes:
                idx = self.scenes.index(current)
                next_idx = (idx + 1) % len(self.scenes)
                target = self.scenes[next_idx]
                result = self.switch_scene(target)
                status = "OK" if result.startswith("Switched to") else "ERROR"
                self._log_command("NextScene", status, f"from={current} to={target}")
                return result
            return "Could not determine current scene"
        except Exception as e:
            self._log_command("NextScene", "ERROR", str(e))
            return f"Failed: {e}"
    
    def previous_scene(self) -> str:
        if not self.connected:
            self._log_command("PreviousScene", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self._refresh_scenes()
            current = self.client.get_current_program_scene().current_program_scene_name
            if current in self.scenes:
                idx = self.scenes.index(current)
                prev_idx = (idx - 1) % len(self.scenes)
                target = self.scenes[prev_idx]
                result = self.switch_scene(target)
                status = "OK" if result.startswith("Switched to") else "ERROR"
                self._log_command("PreviousScene", status, f"from={current} to={target}")
                return result
            return "Could not determine current scene"
        except Exception as e:
            self._log_command("PreviousScene", "ERROR", str(e))
            return f"Failed: {e}"
    
    # === Sources ===
    
    def show_source(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("ShowSource", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            current = self.client.get_current_program_scene().current_program_scene_name
            name, item_id = self._find_source(source_name)
            if not name:
                self._log_command("ShowSource", "ERROR", f"source_not_found target={source_name}")
                return f"Source '{source_name}' not found"
            self.client.set_scene_item_enabled(current, item_id, True)
            self._log_command("ShowSource", "OK", f"source={name}")
            return f"Showing {name}"
        except Exception as e:
            self._log_command("ShowSource", "ERROR", str(e))
            return f"Failed: {e}"
    
    def hide_source(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("HideSource", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            current = self.client.get_current_program_scene().current_program_scene_name
            name, item_id = self._find_source(source_name)
            if not name:
                self._log_command("HideSource", "ERROR", f"source_not_found target={source_name}")
                return f"Source '{source_name}' not found"
            self.client.set_scene_item_enabled(current, item_id, False)
            self._log_command("HideSource", "OK", f"source={name}")
            return f"Hiding {name}"
        except Exception as e:
            self._log_command("HideSource", "ERROR", str(e))
            return f"Failed: {e}"
    
    def toggle_source(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("ToggleSource", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            current = self.client.get_current_program_scene().current_program_scene_name
            name, item_id = self._find_source(source_name)
            if not name:
                self._log_command("ToggleSource", "ERROR", f"source_not_found target={source_name}")
                return f"Source '{source_name}' not found"
            # Get current state
            enabled = self.client.get_scene_item_enabled(current, item_id).scene_item_enabled
            self.client.set_scene_item_enabled(current, item_id, not enabled)
            new_state = "hidden" if enabled else "visible"
            self._log_command("ToggleSource", "OK", f"source={name} state={new_state}")
            return f"{name} {'hidden' if enabled else 'visible'}"
        except Exception as e:
            self._log_command("ToggleSource", "ERROR", str(e))
            return f"Failed: {e}"
    
    # === Audio ===
    
    def mute_source(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("MuteSource", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.set_input_mute(source_name, True)
            self._log_command("MuteSource", "OK", f"source={source_name}")
            return f"Muted {source_name}"
        except Exception as e:
            self._log_command("MuteSource", "ERROR", str(e))
            return f"Failed to mute: {e}"
    
    def unmute_source(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("UnmuteSource", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.set_input_mute(source_name, False)
            self._log_command("UnmuteSource", "OK", f"source={source_name}")
            return f"Unmuted {source_name}"
        except Exception as e:
            self._log_command("UnmuteSource", "ERROR", str(e))
            return f"Failed to unmute: {e}"
    
    def toggle_mute(self, source_name: str) -> str:
        if not self.connected:
            self._log_command("ToggleMute", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.toggle_input_mute(source_name)
            self._log_command("ToggleMute", "OK", f"source={source_name}")
            return f"Toggled mute for {source_name}"
        except Exception as e:
            self._log_command("ToggleMute", "ERROR", str(e))
            return f"Failed: {e}"
    
    # === Virtual Camera ===
    
    def start_virtual_camera(self) -> str:
        if not self.connected:
            self._log_command("StartVirtualCamera", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.start_virtual_cam()
            self._log_command("StartVirtualCamera", "OK")
            return "Virtual camera started"
        except Exception as e:
            self._log_command("StartVirtualCamera", "ERROR", str(e))
            return f"Failed: {e}"
    
    def stop_virtual_camera(self) -> str:
        if not self.connected:
            self._log_command("StopVirtualCamera", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.stop_virtual_cam()
            self._log_command("StopVirtualCamera", "OK")
            return "Virtual camera stopped"
        except Exception as e:
            self._log_command("StopVirtualCamera", "ERROR", str(e))
            return f"Failed: {e}"
    
    # === Replay Buffer ===
    
    def start_replay_buffer(self) -> str:
        if not self.connected:
            self._log_command("StartReplayBuffer", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.start_replay_buffer()
            self._log_command("StartReplayBuffer", "OK")
            return "Replay buffer started"
        except Exception as e:
            self._log_command("StartReplayBuffer", "ERROR", str(e))
            return f"Failed: {e}"
    
    def stop_replay_buffer(self) -> str:
        if not self.connected:
            self._log_command("StopReplayBuffer", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.stop_replay_buffer()
            self._log_command("StopReplayBuffer", "OK")
            return "Replay buffer stopped"
        except Exception as e:
            self._log_command("StopReplayBuffer", "ERROR", str(e))
            return f"Failed: {e}"
    
    def save_replay(self) -> str:
        if not self.connected:
            self._log_command("SaveReplay", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            self.client.save_replay_buffer()
            self._log_command("SaveReplay", "OK")
            return "Replay saved!"
        except Exception as e:
            self._log_command("SaveReplay", "ERROR", str(e))
            return f"Failed to save replay: {e}"
    
    # === Status ===
    
    def get_status(self) -> str:
        if not self.connected:
            self._log_command("GetStatus", "ERROR", "not_connected")
            return "Not connected to OBS"
        try:
            stream = self.client.get_stream_status()
            record = self.client.get_record_status()
            vcam = self.client.get_virtual_cam_status()
            current = self.client.get_current_program_scene()
            
            status_lines = [
                f"Current Scene: {current.current_program_scene_name}",
                f"Streaming: {'LIVE' if stream.output_active else 'Offline'}",
            ]
            
            if stream.output_active:
                status_lines.append(f"  Duration: {stream.output_timecode}")
            
            status_lines.append(f"Recording: {'ON' if record.output_active else 'Off'}")
            if record.output_active:
                status_lines.append(f"  Duration: {record.output_timecode}")
            
            status_lines.append(f"Virtual Cam: {'ON' if vcam.output_active else 'Off'}")
            self._log_command(
                "GetStatus",
                "OK",
                f"stream={'live' if stream.output_active else 'offline'} "
                f"record={'on' if record.output_active else 'off'} "
                f"vcam={'on' if vcam.output_active else 'off'}"
            )
            return "\n".join(status_lines)
        except Exception as e:
            self._log_command("GetStatus", "ERROR", str(e))
            return f"Failed to get status: {e}"


def parse_command(text: str) -> Tuple[str, List[str]]:
    """Parse natural language command into action and arguments"""
    text = text.lower().strip()
    
    # Streaming
    if any(p in text for p in ["start stream", "go live", "begin stream", "start broadcasting"]):
        return ("start_stream", [])
    if any(p in text for p in ["stop stream", "end stream", "go offline", "stop broadcasting"]):
        return ("stop_stream", [])
    
    # Recording
    if any(p in text for p in ["start record", "begin record", "start the record"]):
        return ("start_recording", [])
    if any(p in text for p in ["stop record", "end record", "save record", "finish record"]):
        return ("stop_recording", [])
    if "pause record" in text:
        return ("pause_recording", [])
    if "resume record" in text:
        return ("resume_recording", [])
    
    # Scenes - specific aliases
    if any(p in text for p in ["brb", "be right back"]):
        return ("switch_scene", ["brb"])
    if "starting soon" in text:
        return ("switch_scene", ["starting"])
    if any(p in text for p in ["full screen", "fullscreen"]):
        return ("switch_scene", ["full screen"])
    
    # Scene switching with extracted name
    scene_patterns = [
        r"switch to ([\w\s]+)",
        r"go to ([\w\s]+)",
        r"show ([\w\s]+) scene",
        r"([\w\s]+) scene",
    ]
    for pattern in scene_patterns:
        match = re.search(pattern, text)
        if match:
            scene_name = match.group(1).strip()
            if scene_name not in ["the", "my", "our"]:
                return ("switch_scene", [scene_name])
    
    if "next scene" in text:
        return ("next_scene", [])
    if any(p in text for p in ["previous scene", "prev scene", "last scene"]):
        return ("previous_scene", [])
    if any(p in text for p in ["list scene", "what scene", "show scene", "scenes"]):
        return ("list_scenes", [])
    
    # Source visibility
    show_match = re.search(r"show ([\w\s]+)", text)
    if show_match and "scene" not in text:
        return ("show_source", [show_match.group(1).strip()])
    
    hide_match = re.search(r"hide ([\w\s]+)", text)
    if hide_match:
        return ("hide_source", [hide_match.group(1).strip()])
    
    toggle_match = re.search(r"toggle ([\w\s]+)", text)
    if toggle_match:
        return ("toggle_source", [toggle_match.group(1).strip()])
    
    # Audio
    mute_match = re.search(r"mute ([\w\s]+)", text)
    if mute_match and "unmute" not in text:
        source = mute_match.group(1).strip()
        if source == "mic" or source == "microphone":
            source = "Mic/Aux"
        return ("mute_source", [source])
    
    unmute_match = re.search(r"unmute ([\w\s]+)", text)
    if unmute_match:
        source = unmute_match.group(1).strip()
        if source == "mic" or source == "microphone":
            source = "Mic/Aux"
        return ("unmute_source", [source])
    
    # Virtual camera
    if any(p in text for p in ["start virtual", "start vcam", "enable virtual"]):
        return ("start_virtual_camera", [])
    if any(p in text for p in ["stop virtual", "stop vcam", "disable virtual"]):
        return ("stop_virtual_camera", [])
    
    # Replay
    if "start replay" in text:
        return ("start_replay_buffer", [])
    if "stop replay" in text:
        return ("stop_replay_buffer", [])
    if any(p in text for p in ["save replay", "clip that", "save clip", "save that"]):
        return ("save_replay", [])
    
    # Status
    if any(p in text for p in ["status", "what's", "obs info"]):
        return ("get_status", [])
    
    return ("unknown", [text])


def execute(command: str) -> str:
    """Execute OBS command"""
    skill = OBSSkill()
    
    if not skill.connect():
        return "Could not connect to OBS. Is it running with WebSocket enabled?"
    
    action, args = parse_command(command)
    
    method = getattr(skill, action, None)
    if method:
        return method(*args) if args else method()
    
    return f"Unknown OBS command: {command}"


def main():
    if len(sys.argv) < 2:
        print("ROXY OBS Skill")
        print("="*40)
        print("\nUsage: obs_skill.py <command>")
        print("\nExamples:")
        print("  'start streaming'    - Go live")
        print("  'stop streaming'     - Go offline")
        print("  'start recording'    - Begin recording")
        print("  'stop recording'     - Stop and save")
        print("  'switch to game'     - Change scene")
        print("  'brb'                - BRB scene")
        print("  'mute mic'           - Mute microphone")
        print("  'clip that'          - Save replay")
        print("  'status'             - Show OBS status")
        return
    
    command = " ".join(sys.argv[1:])
    print(f"[OBS] {command}")
    result = execute(command)
    print(f"\n{result}")


if __name__ == "__main__":
    main()

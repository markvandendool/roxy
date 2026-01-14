#!/usr/bin/env python3
"""
ROXY Gesture MIDI Controller
Linux-native MIDI output via ALSA/rtmidi for OBS control
"""
import mido
from mido import Message
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OBS Control MIDI Mappings
# Using CC (Control Change) messages for OBS actions
OBS_MIDI_MAPPINGS = {
    # Scene switching (CC 1-8 on channel 0)
    'scene_1': {'type': 'cc', 'channel': 0, 'control': 1, 'value': 127},
    'scene_2': {'type': 'cc', 'channel': 0, 'control': 2, 'value': 127},
    'scene_3': {'type': 'cc', 'channel': 0, 'control': 3, 'value': 127},
    'scene_4': {'type': 'cc', 'channel': 0, 'control': 4, 'value': 127},
    'scene_5': {'type': 'cc', 'channel': 0, 'control': 5, 'value': 127},
    'scene_6': {'type': 'cc', 'channel': 0, 'control': 6, 'value': 127},
    'scene_7': {'type': 'cc', 'channel': 0, 'control': 7, 'value': 127},
    'scene_8': {'type': 'cc', 'channel': 0, 'control': 8, 'value': 127},
    
    # Recording/Streaming controls (CC 10-15)
    'start_recording': {'type': 'cc', 'channel': 0, 'control': 10, 'value': 127},
    'stop_recording': {'type': 'cc', 'channel': 0, 'control': 11, 'value': 127},
    'start_streaming': {'type': 'cc', 'channel': 0, 'control': 12, 'value': 127},
    'stop_streaming': {'type': 'cc', 'channel': 0, 'control': 13, 'value': 127},
    'pause_recording': {'type': 'cc', 'channel': 0, 'control': 14, 'value': 127},
    
    # Source toggles (CC 20-30)
    'toggle_camera': {'type': 'cc', 'channel': 0, 'control': 20, 'value': 127},
    'toggle_screen': {'type': 'cc', 'channel': 0, 'control': 21, 'value': 127},
    'toggle_overlay': {'type': 'cc', 'channel': 0, 'control': 22, 'value': 127},
    'toggle_mute': {'type': 'cc', 'channel': 0, 'control': 23, 'value': 127},
    
    # Filter controls (CC 40-50, continuous)
    'blur_amount': {'type': 'cc', 'channel': 0, 'control': 40, 'value': None},  # 0-127
    'zoom_level': {'type': 'cc', 'channel': 0, 'control': 41, 'value': None},
    'brightness': {'type': 'cc', 'channel': 0, 'control': 42, 'value': None},
    
    # Key transposition (CC 60-72 for each key)
    'key_c': {'type': 'cc', 'channel': 0, 'control': 60, 'value': 127},
    'key_cs': {'type': 'cc', 'channel': 0, 'control': 61, 'value': 127},
    'key_d': {'type': 'cc', 'channel': 0, 'control': 62, 'value': 127},
    'key_ds': {'type': 'cc', 'channel': 0, 'control': 63, 'value': 127},
    'key_e': {'type': 'cc', 'channel': 0, 'control': 64, 'value': 127},
    'key_f': {'type': 'cc', 'channel': 0, 'control': 65, 'value': 127},
    'key_fs': {'type': 'cc', 'channel': 0, 'control': 66, 'value': 127},
    'key_g': {'type': 'cc', 'channel': 0, 'control': 67, 'value': 127},
    'key_gs': {'type': 'cc', 'channel': 0, 'control': 68, 'value': 127},
    'key_a': {'type': 'cc', 'channel': 0, 'control': 69, 'value': 127},
    'key_as': {'type': 'cc', 'channel': 0, 'control': 70, 'value': 127},
    'key_b': {'type': 'cc', 'channel': 0, 'control': 71, 'value': 127},
}


def find_virtual_midi_port():
    """Find an available virtual MIDI port on Linux (ALSA)"""
    outputs = mido.get_output_names()
    logger.info(f"Available MIDI outputs: {outputs}")
    
    # Priority order for Linux virtual MIDI
    priorities = [
        'VirMIDI',
        'Virtual Raw MIDI',
        'Midi Through',
        'FLUID Synth',
    ]
    
    for priority in priorities:
        for port in outputs:
            if priority.lower() in port.lower():
                logger.info(f"Found virtual MIDI port: {port}")
                return port
    
    # Fallback: return first available
    if outputs:
        logger.warning(f"No virtual MIDI found, using: {outputs[0]}")
        return outputs[0]
    
    logger.error("No MIDI output ports available!")
    return None


class OBSMidiController:
    """MIDI controller for OBS with Linux ALSA support"""
    
    def __init__(self, port_name=None):
        if port_name is None:
            port_name = find_virtual_midi_port()
        
        if port_name is None:
            raise RuntimeError("No MIDI output port available. Run: sudo modprobe snd-virmidi")
        
        try:
            self.port = mido.open_output(port_name)
            logger.info(f"Connected to MIDI output: {port_name}")
        except Exception as e:
            logger.error(f"Failed to open MIDI port {port_name}: {e}")
            raise
        
        self.last_action = None
        self.action_cooldown = {}  # Prevent rapid-fire duplicate messages
    
    def close(self):
        """Close MIDI port"""
        if self.port:
            self.port.close()
            logger.info("MIDI port closed")
    
    def send_action(self, action_name: str, value: int = None):
        """Send a predefined OBS action via MIDI"""
        mapping = OBS_MIDI_MAPPINGS.get(action_name)
        if not mapping:
            logger.warning(f"Unknown action: {action_name}")
            return False
        
        msg_type = mapping['type']
        channel = mapping['channel']
        control = mapping['control']
        msg_value = value if mapping['value'] is None else mapping['value']
        
        if msg_type == 'cc':
            msg = Message('control_change', channel=channel, control=control, value=msg_value)
        elif msg_type == 'note':
            msg = Message('note_on', channel=channel, note=control, velocity=msg_value)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return False
        
        self.port.send(msg)
        logger.info(f"Sent MIDI: {action_name} -> {msg}")
        self.last_action = action_name
        return True
    
    def send_scene(self, scene_number: int):
        """Switch to scene 1-8"""
        if 1 <= scene_number <= 8:
            return self.send_action(f'scene_{scene_number}')
        logger.warning(f"Invalid scene number: {scene_number}")
        return False
    
    def send_key_transposition(self, key: str):
        """Send key transposition (C, C#/Db, D, D#/Eb, E, F, F#/Gb, G, G#/Ab, A, A#/Bb, B)"""
        key_map = {
            'C': 'key_c', 'C#': 'key_cs', 'Db': 'key_cs',
            'D': 'key_d', 'D#': 'key_ds', 'Eb': 'key_ds',
            'E': 'key_e',
            'F': 'key_f', 'F#': 'key_fs', 'Gb': 'key_fs',
            'G': 'key_g', 'G#': 'key_gs', 'Ab': 'key_gs',
            'A': 'key_a', 'A#': 'key_as', 'Bb': 'key_as',
            'B': 'key_b',
        }
        action = key_map.get(key.upper())
        if action:
            return self.send_action(action)
        logger.warning(f"Invalid key: {key}")
        return False
    
    def send_continuous(self, control_name: str, value: float):
        """Send a continuous control value (0.0-1.0 -> 0-127)"""
        midi_value = int(max(0, min(127, value * 127)))
        return self.send_action(control_name, midi_value)
    
    def start_recording(self):
        return self.send_action('start_recording')
    
    def stop_recording(self):
        return self.send_action('stop_recording')
    
    def toggle_camera(self):
        return self.send_action('toggle_camera')
    
    def toggle_mute(self):
        return self.send_action('toggle_mute')


# Test code
if __name__ == '__main__':
    print("=== ROXY MIDI Controller Test ===")
    print(f"Available MIDI outputs: {mido.get_output_names()}")
    
    try:
        controller = OBSMidiController()
        
        print("\nSending test scene switch (Scene 1)...")
        controller.send_scene(1)
        
        print("Sending test key transposition (C major)...")
        controller.send_key_transposition('C')
        
        print("Sending continuous zoom (50%)...")
        controller.send_continuous('zoom_level', 0.5)
        
        controller.close()
        print("\n✓ MIDI controller test complete!")
    except Exception as e:
        print(f"✗ Error: {e}")

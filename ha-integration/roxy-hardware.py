#!/usr/bin/env python3
"""
Roxy Hardware Automation Suite
- GPU monitoring (rocm-smi)
- USB hub power control (uhubctl)
- OBS control (websocket)
- Home Assistant integration
"""
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
import time

class GPUMonitor:
    """Monitor AMD GPU via rocm-smi"""
    
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Get GPU power, temp, utilization"""
        try:
            result = subprocess.run(
                ['rocm-smi', '--showtemp', '--showuse', '--showpower', '--showmeminfo', 'vram', '--json'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data
        except:
            pass
        
        # Fallback to text parsing
        try:
            result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=10)
            return {'raw': result.stdout}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_summary() -> Dict[str, Any]:
        """Get simplified GPU summary"""
        status = GPUMonitor.get_status()
        summary = {'gpus': []}
        
        if 'card0' in status:
            for card_id, card_data in status.items():
                if card_id.startswith('card'):
                    gpu = {
                        'id': card_id,
                        'temp': card_data.get('Temperature (Sensor edge) (C)', 'N/A'),
                        'power': card_data.get('Average Graphics Package Power (W)', 'N/A'),
                        'vram_used': card_data.get('VRAM Total Used Memory (B)', 'N/A'),
                        'gpu_use': card_data.get('GPU use (%)', 'N/A'),
                    }
                    summary['gpus'].append(gpu)
        
        return summary


class USBHubControl:
    """Control USB hub power via uhubctl"""
    
    @staticmethod
    def list_hubs() -> str:
        """List controllable USB hubs"""
        try:
            result = subprocess.run(['sudo', 'uhubctl'], capture_output=True, text=True, timeout=10)
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    @staticmethod
    def set_port_power(hub: str, port: int, on: bool) -> bool:
        """Control power to a specific USB port"""
        action = 'on' if on else 'off'
        try:
            result = subprocess.run(
                ['sudo', 'uhubctl', '-l', hub, '-p', str(port), '-a', action],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def cycle_port(hub: str, port: int, delay: float = 2.0) -> bool:
        """Power cycle a USB port"""
        USBHubControl.set_port_power(hub, port, False)
        time.sleep(delay)
        return USBHubControl.set_port_power(hub, port, True)


class OBSController:
    """Control OBS via websocket"""
    
    def __init__(self, host: str = 'localhost', port: int = 4455, password: str = None):
        self.host = host
        self.port = port
        self.password = password
        self._ws = None
    
    def connect(self) -> bool:
        """Connect to OBS websocket"""
        try:
            import websocket
            self._ws = websocket.create_connection(f"ws://{self.host}:{self.port}")
            # Handle auth if needed
            return True
        except ImportError:
            print("Install: pip install websocket-client")
            return False
        except Exception as e:
            print(f"OBS connection failed: {e}")
            return False
    
    def start_streaming(self) -> bool:
        """Start streaming"""
        return self._send_request('StartStream')
    
    def stop_streaming(self) -> bool:
        """Stop streaming"""
        return self._send_request('StopStream')
    
    def start_recording(self) -> bool:
        """Start recording"""
        return self._send_request('StartRecord')
    
    def stop_recording(self) -> bool:
        """Stop recording"""
        return self._send_request('StopRecord')
    
    def get_status(self) -> Dict[str, Any]:
        """Get OBS status"""
        return self._send_request('GetStreamStatus') or {}
    
    def _send_request(self, request_type: str, data: dict = None) -> Any:
        """Send request to OBS websocket"""
        if not self._ws:
            return None
        try:
            import json
            msg = {'op': 6, 'd': {'requestType': request_type, 'requestId': str(time.time())}}
            if data:
                msg['d']['requestData'] = data
            self._ws.send(json.dumps(msg))
            response = json.loads(self._ws.recv())
            return response.get('d', {}).get('responseData')
        except:
            return None


class RoxyHardwareHub:
    """Central hub for all hardware automation"""
    
    def __init__(self):
        self.gpu = GPUMonitor()
        self.usb = USBHubControl()
        self.obs = OBSController()
        
        # Load HA integration if available
        ha_control = Path(__file__).parent / 'ha-control.py'
        if ha_control.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("ha_control", ha_control)
            self.ha_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.ha_module)
            self.ha = self.ha_module.HomeAssistantController()
        else:
            self.ha = None
    
    def go_live(self) -> Dict[str, bool]:
        """
        BROADCAST GO LIVE AUTOMATION
        1. Turn on studio lights (Tuya)
        2. Start OBS streaming
        3. Set GPU to performance mode
        """
        results = {}
        
        # Studio lights (if Tuya working)
        try:
            from pathlib import Path
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            tuya_script = Path(__file__).parent / 'tuya-control.py'
            if tuya_script.exists():
                result = subprocess.run(
                    ['python3', str(tuya_script), 'on', 'Studio Lights'],
                    capture_output=True, text=True, timeout=30
                )
                results['studio_lights'] = 'Success' in result.stdout
        except:
            results['studio_lights'] = False
        
        # OBS streaming
        if self.obs.connect():
            results['obs_stream'] = self.obs.start_streaming()
        else:
            results['obs_stream'] = False
        
        # GPU performance mode
        try:
            subprocess.run(
                ['sudo', 'rocm-smi', '--setperflevel', 'high'],
                capture_output=True, timeout=10
            )
            results['gpu_performance'] = True
        except:
            results['gpu_performance'] = False
        
        return results
    
    def go_offline(self) -> Dict[str, bool]:
        """
        BROADCAST GO OFFLINE
        1. Stop OBS streaming
        2. Turn off studio lights
        3. Set GPU to auto mode
        """
        results = {}
        
        # OBS
        if self.obs.connect():
            results['obs_stream'] = self.obs.stop_streaming()
        
        # Lights
        try:
            tuya_script = Path(__file__).parent / 'tuya-control.py'
            if tuya_script.exists():
                result = subprocess.run(
                    ['python3', str(tuya_script), 'off', 'Studio Lights'],
                    capture_output=True, text=True, timeout=30
                )
                results['studio_lights'] = 'Success' in result.stdout
        except:
            results['studio_lights'] = False
        
        # GPU auto
        try:
            subprocess.run(
                ['sudo', 'rocm-smi', '--setperflevel', 'auto'],
                capture_output=True, timeout=10
            )
            results['gpu_auto'] = True
        except:
            results['gpu_auto'] = False
        
        return results
    
    def status(self) -> Dict[str, Any]:
        """Get full system status"""
        return {
            'gpu': self.gpu.get_summary(),
            'usb_hubs': self.usb.list_hubs(),
            'ha_connected': self.ha is not None,
        }


# CLI
if __name__ == '__main__':
    import sys
    hub = RoxyHardwareHub()
    
    if len(sys.argv) < 2:
        print("Usage: roxy-hardware.py <command>")
        print("Commands: status, gpu, usb, go-live, go-offline")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        print(json.dumps(hub.status(), indent=2, default=str))
    
    elif cmd == 'gpu':
        print(json.dumps(hub.gpu.get_status(), indent=2))
    
    elif cmd == 'usb':
        print(hub.usb.list_hubs())
    
    elif cmd == 'go-live':
        print("🔴 GOING LIVE...")
        results = hub.go_live()
        for k, v in results.items():
            print(f"  {k}: {'✅' if v else '❌'}")
    
    elif cmd == 'go-offline':
        print("⚫ GOING OFFLINE...")
        results = hub.go_offline()
        for k, v in results.items():
            print(f"  {k}: {'✅' if v else '❌'}")
    
    else:
        print(f"Unknown command: {cmd}")

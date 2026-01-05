#!/usr/bin/env python3
"""
Roxy Tuya Cloud Control - using TinyTuya Cloud
"""
import json
import sys
from pathlib import Path
import tinytuya

# Load config
config_file = Path(__file__).parent.parent / 'tinytuya.json'
config = json.loads(config_file.read_text())

# Load devices
devices_file = Path(__file__).parent.parent / 'devices.json'
devices = {d['name']: d for d in json.loads(devices_file.read_text())}

# Create cloud connection
cloud = tinytuya.Cloud(
    apiRegion=config.get('apiRegion', 'us'),
    apiKey=config['apiKey'],
    apiSecret=config['apiSecret'],
    apiDeviceID=config.get('apiDeviceID')
)

def resolve_device(name_or_id: str) -> str:
    """Resolve device name to ID"""
    if name_or_id in devices:
        return devices[name_or_id]['id']
    return name_or_id

def get_status(device_name: str = None):
    """Get device status"""
    if device_name:
        device_id = resolve_device(device_name)
        result = cloud.getstatus(device_id)
        return result
    else:
        results = {}
        for name, d in devices.items():
            status = cloud.getstatus(d['id'])
            if status and 'result' in status:
                switch = next((s['value'] for s in status['result'] if s['code'] == 'switch_1'), None)
                results[name] = 'ON' if switch else 'OFF'
            else:
                results[name] = 'ERROR'
        return results

def send_command(device_name: str, switch_on: bool):
    """Send on/off command"""
    device_id = resolve_device(device_name)
    commands = {'commands': [{'code': 'switch_1', 'value': switch_on}]}
    return cloud.sendcommand(device_id, commands)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: tuya-control.py <command> [args]")
        print("Commands: list, status [device], on <device>, off <device>")
        print(f"\nDevices: {', '.join(devices.keys())}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'list':
        for name, d in devices.items():
            print(f"{name}: {d['id']}")
    
    elif cmd == 'status':
        if len(sys.argv) > 2:
            device = ' '.join(sys.argv[2:])
            result = get_status(device)
            print(json.dumps(result, indent=2))
        else:
            print("All device status:")
            for name, status in get_status().items():
                print(f"  {name}: {status}")
    
    elif cmd in ('on', 'turn_on'):
        device = ' '.join(sys.argv[2:])
        result = send_command(device, True)
        print(f"Turn on {device}: {'✅ Success' if result.get('success') else '❌ ' + str(result)}")
    
    elif cmd in ('off', 'turn_off'):
        device = ' '.join(sys.argv[2:])
        result = send_command(device, False)
        print(f"Turn off {device}: {'✅ Success' if result.get('success') else '❌ ' + str(result)}")
    
    elif cmd == 'studio':
        result = send_command('Studio Lights', True)
        print(f"Studio Lights: {'✅ ON' if result.get('success') else '❌ ' + str(result)}")
    
    else:
        print(f"Unknown command: {cmd}")

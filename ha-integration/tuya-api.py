#!/usr/bin/env python3
"""
Roxy Tuya REST API - Exposes Tuya controls for Home Assistant integration
Runs on port 5050
"""
from flask import Flask, jsonify, request
import json
from pathlib import Path
import tinytuya

app = Flask(__name__)

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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'tuya-api'})

@app.route('/devices', methods=['GET'])
def list_devices():
    return jsonify({name: {'id': d['id'], 'category': d.get('category', 'unknown')}
                   for name, d in devices.items()})

@app.route('/status', methods=['GET'])
def all_status():
    """Get status of all devices"""
    results = {}
    for name, d in devices.items():
        status = cloud.getstatus(d['id'])
        if status and 'result' in status:
            switch = next((s['value'] for s in status['result'] if s['code'] == 'switch_1'), None)
            results[name] = {'state': 'on' if switch else 'off', 'id': d['id']}
        else:
            results[name] = {'state': 'unknown', 'id': d['id']}
    return jsonify(results)

@app.route('/device/<name>/status', methods=['GET'])
def device_status(name):
    """Get status of a specific device"""
    device_id = resolve_device(name)
    result = cloud.getstatus(device_id)
    return jsonify(result)

@app.route('/device/<name>/on', methods=['POST'])
def turn_on(name):
    """Turn device on"""
    device_id = resolve_device(name)
    commands = {'commands': [{'code': 'switch_1', 'value': True}]}
    result = cloud.sendcommand(device_id, commands)
    return jsonify({'success': result.get('success', False), 'result': result})

@app.route('/device/<name>/off', methods=['POST'])
def turn_off(name):
    """Turn device off"""
    device_id = resolve_device(name)
    commands = {'commands': [{'code': 'switch_1', 'value': False}]}
    result = cloud.sendcommand(device_id, commands)
    return jsonify({'success': result.get('success', False), 'result': result})

@app.route('/device/<name>/toggle', methods=['POST'])
def toggle(name):
    """Toggle device"""
    device_id = resolve_device(name)
    # Get current state
    status = cloud.getstatus(device_id)
    current_state = False
    if status and 'result' in status:
        current_state = next((s['value'] for s in status['result'] if s['code'] == 'switch_1'), False)

    # Send opposite command
    commands = {'commands': [{'code': 'switch_1', 'value': not current_state}]}
    result = cloud.sendcommand(device_id, commands)
    return jsonify({'success': result.get('success', False), 'new_state': 'on' if not current_state else 'off'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)

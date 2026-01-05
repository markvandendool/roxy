#!/usr/bin/env python3
"""
Roxy Home Assistant Control Module
Control lights, switches, and smart plugs via HA REST API
"""
import os
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any

class HomeAssistantController:
    def __init__(self, url: str = None, token: str = None):
        env_file = Path(__file__).parent / '.env'
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        
        self.base_url = url or os.environ.get('HA_URL', 'http://localhost:8123')
        self.token = token or os.environ.get('HA_TOKEN')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/{endpoint}"
        try:
            resp = requests.request(method, url, headers=self.headers, json=data, timeout=10)
            resp.raise_for_status()
            return resp.json() if resp.text else {'success': True}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def get_states(self) -> list:
        """Get all entity states"""
        return self._request('GET', 'states')
    
    def get_state(self, entity_id: str) -> dict:
        """Get single entity state"""
        return self._request('GET', f'states/{entity_id}')
    
    def call_service(self, domain: str, service: str, entity_id: str = None, **kwargs) -> dict:
        """Call a service (turn_on, turn_off, toggle, etc.)"""
        data = kwargs
        if entity_id:
            data['entity_id'] = entity_id
        return self._request('POST', f'services/{domain}/{service}', data)
    
    def turn_on(self, entity_id: str, **kwargs) -> dict:
        """Turn on an entity"""
        domain = entity_id.split('.')[0]
        return self.call_service(domain, 'turn_on', entity_id, **kwargs)
    
    def turn_off(self, entity_id: str) -> dict:
        """Turn off an entity"""
        domain = entity_id.split('.')[0]
        return self.call_service(domain, 'turn_off', entity_id)
    
    def toggle(self, entity_id: str) -> dict:
        """Toggle an entity"""
        domain = entity_id.split('.')[0]
        return self.call_service(domain, 'toggle', entity_id)
    
    def list_entities(self, domain_filter: str = None) -> list:
        """List all entities, optionally filtered by domain"""
        states = self.get_states()
        if isinstance(states, dict) and 'error' in states:
            return states
        if domain_filter:
            return [s for s in states if s['entity_id'].startswith(f'{domain_filter}.')]
        return states


# CLI interface
if __name__ == '__main__':
    import sys
    ha = HomeAssistantController()
    
    if len(sys.argv) < 2:
        print("Usage: ha-control.py <command> [args]")
        print("Commands: list, state <entity>, on <entity>, off <entity>, toggle <entity>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'list':
        domain = sys.argv[2] if len(sys.argv) > 2 else None
        entities = ha.list_entities(domain)
        if isinstance(entities, dict) and 'error' in entities:
            print(f"Error: {entities['error']}")
        else:
            for e in entities:
                print(f"{e['entity_id']}: {e['state']}")
    
    elif cmd == 'state':
        if len(sys.argv) < 3:
            print("Usage: ha-control.py state <entity_id>")
            sys.exit(1)
        result = ha.get_state(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd in ('on', 'turn_on'):
        if len(sys.argv) < 3:
            print("Usage: ha-control.py on <entity_id>")
            sys.exit(1)
        result = ha.turn_on(sys.argv[2])
        print(f"Turned on {sys.argv[2]}: {result}")
    
    elif cmd in ('off', 'turn_off'):
        if len(sys.argv) < 3:
            print("Usage: ha-control.py off <entity_id>")
            sys.exit(1)
        result = ha.turn_off(sys.argv[2])
        print(f"Turned off {sys.argv[2]}: {result}")
    
    elif cmd == 'toggle':
        if len(sys.argv) < 3:
            print("Usage: ha-control.py toggle <entity_id>")
            sys.exit(1)
        result = ha.toggle(sys.argv[2])
        print(f"Toggled {sys.argv[2]}: {result}")
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

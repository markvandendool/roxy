#!/usr/bin/env python3
"""
ROXY Security Layer - Authentication, authorization, and audit logging
"""
import logging
import hashlib
import hmac
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.security')

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class SecurityService:
    """Security service for ROXY"""
    
    def __init__(self):
        self.audit_log = Path('/home/mark/.roxy/logs/audit.log')
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self.api_keys = {}
        self.permissions = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from environment"""
        import os
        # Load from environment variables
        for key, value in os.environ.items():
            if key.startswith('ROXY_API_KEY_'):
                key_name = key.replace('ROXY_API_KEY_', '').lower()
                self.api_keys[key_name] = value
    
    def authenticate(self, api_key: str) -> bool:
        """Authenticate API key"""
        for key_name, key_value in self.api_keys.items():
            if hmac.compare_digest(api_key, key_value):
                return True
        return False
    
    def authorize(self, user: str, permission: Permission, resource: str) -> bool:
        """Check if user has permission"""
        user_perms = self.permissions.get(user, [])
        return permission in user_perms or Permission.ADMIN in user_perms
    
    def audit_log_event(self, event_type: str, user: str, action: str, 
                       resource: str, success: bool, details: Dict = None):
        """Log security event"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user': user,
            'action': action,
            'resource': resource,
            'success': success,
            'details': details or {}
        }
        
        import json
        with open(self.audit_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def check_rate_limit(self, identifier: str, limit: int = 100, 
                        window: int = 60) -> bool:
        """Check rate limit (simple implementation)"""
        # In production, would use Redis or similar
        return True  # Placeholder

# Global security service
_security_service: Optional[SecurityService] = None

def get_security_service() -> SecurityService:
    """Get or create global security service"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service











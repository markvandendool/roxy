#!/usr/bin/env python3
"""
Security Hardening - Input sanitization, output filtering, audit logging
"""
import logging
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("roxy.security")

ROXY_DIR = Path.home() / ".roxy"
AUDIT_LOG = ROXY_DIR / "logs" / "audit.log"
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


class SecurityHardening:
    """Security hardening for ROXY"""
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf',  # Dangerous file deletion
        r'sudo\s+',  # Privilege escalation
        r'chmod\s+777',  # Dangerous permissions
        r'>\s+/dev/',  # Device manipulation
        r'curl\s+.*\s+\|\s+sh',  # Pipe to shell
        r'wget\s+.*\s+\|\s+sh',  # Pipe to shell
    ]
    
    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r'ignore\s+previous\s+instructions',
        r'forget\s+everything',
        r'you\s+are\s+now',
        r'act\s+as\s+if',
        r'pretend\s+to\s+be',
        r'system\s*:',
        r'user\s*:',
    ]
    
    # PII patterns (basic)
    PII_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    ]
    
    def __init__(self):
        self.audit_enabled = True
    
    def sanitize_input(self, user_input: str) -> Dict[str, Any]:
        """Sanitize and validate user input"""
        result = {
            "sanitized": user_input,
            "is_safe": True,
            "warnings": [],
            "blocked": False
        }
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                result["is_safe"] = False
                result["blocked"] = True
                result["warnings"].append(f"Dangerous pattern detected: {pattern}")
                self._audit_log("BLOCKED", user_input, f"Dangerous pattern: {pattern}")
                break
        
        # Check for prompt injection
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                result["warnings"].append(f"Potential prompt injection: {pattern}")
                # Don't block, but log
                self._audit_log("WARNING", user_input, f"Injection pattern: {pattern}")
        
        # Check for PII
        pii_found = []
        for pattern in self.PII_PATTERNS:
            matches = re.findall(pattern, user_input)
            if matches:
                pii_found.extend(matches)
        
        if pii_found:
            result["warnings"].append(f"Potential PII detected: {len(pii_found)} matches")
            # Mask PII
            for pii in pii_found:
                masked = self._mask_pii(pii)
                result["sanitized"] = result["sanitized"].replace(pii, masked)
            self._audit_log("PII_DETECTED", user_input, f"PII found: {len(pii_found)} items")
        
        return result
    
    def _mask_pii(self, pii: str) -> str:
        """Mask PII for logging"""
        if '@' in pii:
            # Email
            parts = pii.split('@')
            return f"{parts[0][0]}***@{parts[1]}"
        elif len(pii) > 4:
            # Other PII - mask middle
            return f"{pii[:2]}***{pii[-2:]}"
        else:
            return "***"
    
    def filter_output(self, output: str) -> Dict[str, Any]:
        """Filter output to prevent prompt injection in responses"""
        result = {
            "filtered": output,
            "is_safe": True,
            "warnings": []
        }
        
        # Check for injection patterns in output
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                result["warnings"].append(f"Potential injection in output: {pattern}")
                # Remove suspicious content
                result["filtered"] = re.sub(pattern, "[FILTERED]", result["filtered"], flags=re.IGNORECASE)
        
        # Check for dangerous commands in output
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                result["is_safe"] = False
                result["warnings"].append(f"Dangerous command in output: {pattern}")
                result["filtered"] = re.sub(pattern, "[BLOCKED]", result["filtered"], flags=re.IGNORECASE)
                self._audit_log("OUTPUT_FILTERED", output[:200], f"Dangerous pattern: {pattern}")
        
        return result
    
    def _audit_log(self, event_type: str, data: str, details: Optional[str] = None) -> None:
        """Log security events"""
        if not self.audit_enabled:
            return
        
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data[:500],  # Truncate
                "details": details
            }
            
            with open(AUDIT_LOG, 'a') as f:
                f.write(f"[{log_entry['timestamp']}] {event_type}: {data[:100]} - {details}\n")
            
            logger.warning(f"Security event: {event_type} - {details}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def check_permissions(self, operation: str, resource: str) -> bool:
        """Check if operation is allowed on resource"""
        # Basic permission checks
        dangerous_paths = [
            "/etc/",
            "/root/",
            "/sys/",
            "/proc/",
            "/dev/",
        ]
        
        for dangerous_path in dangerous_paths:
            if resource.startswith(dangerous_path):
                self._audit_log("PERMISSION_DENIED", resource, f"Access to {dangerous_path} blocked")
                return False
        
        return True


# Global security instance
_security_instance = None


def get_security() -> SecurityHardening:
    """Get global security instance"""
    global _security_instance
    if _security_instance is None:
        _security_instance = SecurityHardening()
    return _security_instance








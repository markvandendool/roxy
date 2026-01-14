#!/usr/bin/env python3
"""
ROXY Configuration Manager - Centralized configuration management
"""
import os
import yaml
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.config')

CONFIG_DIR = Path('/home/mark/.roxy/config')
CONFIG_FILE = CONFIG_DIR / 'roxy_config.yaml'
ENV_FILE = Path('/home/mark/.roxy/.env')

class ConfigManager:
    """Centralized configuration management"""
    
    def __init__(self):
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment"""
        # Load from YAML if exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                logger.info(f"✅ Configuration loaded from {CONFIG_FILE}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                self.config = {}
        
        # Override with environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        if ENV_FILE.exists():
            try:
                with open(ENV_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # Convert to nested dict if key has dots
                            keys = key.split('.')
                            d = self.config
                            for k in keys[:-1]:
                                if k not in d:
                                    d[k] = {}
                                d = d[k]
                            d[keys[-1]] = value
            except Exception as e:
                logger.warning(f"Failed to load .env file: {e}")
        
        # Also load from actual environment
        for key, value in os.environ.items():
            if key.startswith('ROXY_') or key.startswith('OLLAMA_') or key.startswith('ANTHROPIC_'):
                keys = key.lower().replace('roxy_', '').split('_')
                d = self.config
                for k in keys[:-1]:
                    if k not in d:
                        d[k] = {}
                    d = d[k]
                d[keys[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        keys = key.split('.')
        d = self.config
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
    
    def save(self):
        """Save configuration to file"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"✅ Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


# Global config instance
_config: Optional[ConfigManager] = None

def get_config() -> ConfigManager:
    """Get or create global config instance"""
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config











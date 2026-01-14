#!/usr/bin/env python3
"""
ROXY Agent State Manager - Persistent agent state
"""
import logging
import os
from typing import Dict, Any, Optional
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.agents.state')

class AgentStateManager:
    """Manage persistent agent state"""
    
    def __init__(self, state_dir: str = None):
        if state_dir is None:
            roxy_root = Path(os.environ.get("ROXY_ROOT", str(Path.home() / ".roxy")))
            state_dir = str(roxy_root / "data" / "agent-states")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, agent_id: str, state: Dict):
        """Save agent state"""
        state_file = self.state_dir / f"{agent_id}.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.debug(f"Saved state for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to save state for {agent_id}: {e}")
    
    def load_state(self, agent_id: str) -> Optional[Dict]:
        """Load agent state"""
        state_file = self.state_dir / f"{agent_id}.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state for {agent_id}: {e}")
        return None
    
    def delete_state(self, agent_id: str):
        """Delete agent state"""
        state_file = self.state_dir / f"{agent_id}.json"
        if state_file.exists():
            state_file.unlink()
            logger.info(f"Deleted state for agent {agent_id}")










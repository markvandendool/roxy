#!/usr/bin/env python3
"""
ROXY Core - Top 1% Upgrade Integration
======================================
Integrates new bleeding-edge capabilities into existing ROXY Core:
- Sandboxed MCP servers (Docker isolation)
- Hybrid RAG (Qdrant + BM25 + reranking)
- Langfuse observability
- vLLM inference (ROCm)

This file provides the bridge between legacy ROXY and upgraded components.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Add upgrade paths to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent / "mcp"))
sys.path.insert(0, str(Path(__file__).parent / "rag"))
sys.path.insert(0, str(Path(__file__).parent / "observability"))

logger = logging.getLogger("roxy.upgrade")


class ROXYUpgradeManager:
    """
    Manages the gradual migration from legacy ROXY to upgraded architecture.
    
    Features:
    - Feature flags for gradual rollout
    - Fallback to legacy implementations
    - Health monitoring for new components
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._initialized = False
        
        # Feature flags
        self.use_sandboxed_mcp = self.config.get("USE_SANDBOXED_MCP", False)
        self.use_hybrid_rag = self.config.get("USE_HYBRID_RAG", False)
        self.use_langfuse = self.config.get("USE_LANGFUSE", False)
        self.use_vllm = self.config.get("USE_VLLM", False)
        
        # Component instances (lazy loaded)
        self._mcp_router = None
        self._rag_engine = None
        self._observability = None
    
    async def initialize(self):
        """Initialize all enabled upgrade components"""
        logger.info("Initializing ROXY upgrade components...")
        
        tasks = []
        
        if self.use_sandboxed_mcp:
            tasks.append(self._init_sandboxed_mcp())
        
        if self.use_hybrid_rag:
            tasks.append(self._init_hybrid_rag())
        
        if self.use_langfuse:
            tasks.append(self._init_langfuse())
        
        # Wait for all initializations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Component {i} failed to initialize: {result}")
        
        self._initialized = True
        logger.info("ROXY upgrade initialization complete")
    
    async def _init_sandboxed_mcp(self):
        """Initialize sandboxed MCP infrastructure"""
        try:
            from mcp_container_router import MCPContainerRouter
            self._mcp_router = MCPContainerRouter()
            logger.info("✅ Sandboxed MCP router initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize sandboxed MCP: {e}")
            self.use_sandboxed_mcp = False
    
    async def _init_hybrid_rag(self):
        """Initialize hybrid RAG engine"""
        try:
            from hybrid_rag_engine import HybridRAGEngine
            self._rag_engine = HybridRAGEngine()
            await self._rag_engine.initialize()
            logger.info("✅ Hybrid RAG engine initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize hybrid RAG: {e}")
            self.use_hybrid_rag = False
    
    async def _init_langfuse(self):
        """Initialize Langfuse observability"""
        try:
            from langfuse_integration import init_observability
            self._observability = init_observability()
            if self._observability.enabled:
                logger.info("✅ Langfuse observability initialized")
            else:
                logger.warning("⚠️ Langfuse disabled (keys not configured)")
                self.use_langfuse = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Langfuse: {e}")
            self.use_langfuse = False
    
    async def get_mcp_client(self):
        """Get appropriate MCP client (sandboxed or legacy)"""
        if self.use_sandboxed_mcp and self._mcp_router:
            return self._mcp_router
        
        # Fallback to legacy mcp_client
        from mcp_client import MCPClient
        return MCPClient()
    
    async def get_rag_engine(self):
        """Get appropriate RAG engine (hybrid or legacy)"""
        if self.use_hybrid_rag and self._rag_engine:
            return self._rag_engine
        
        # Fallback to legacy RAG (from roxy_core)
        return None  # Legacy RAG is integrated in roxy_core
    
    def get_observability(self):
        """Get observability instance"""
        return self._observability
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all upgrade components"""
        health = {
            "sandboxed_mcp": {"enabled": self.use_sandboxed_mcp, "healthy": False},
            "hybrid_rag": {"enabled": self.use_hybrid_rag, "healthy": False},
            "langfuse": {"enabled": self.use_langfuse, "healthy": False},
            "vllm": {"enabled": self.use_vllm, "healthy": False}
        }
        
        # Check MCP containers
        if self.use_sandboxed_mcp:
            try:
                import subprocess
                result = subprocess.run(
                    ["docker", "ps", "--filter", "name=mcp-", "--format", "{{.Names}}"],
                    capture_output=True, text=True
                )
                running = result.stdout.strip().split("\n")
                health["sandboxed_mcp"]["running_containers"] = [c for c in running if c]
                health["sandboxed_mcp"]["healthy"] = len(running) > 0
            except Exception as e:
                health["sandboxed_mcp"]["error"] = str(e)
        
        # Check Qdrant
        if self.use_hybrid_rag:
            try:
                from qdrant_client import QdrantClient
                client = QdrantClient(host="localhost", port=6333)
                client.get_collections()
                health["hybrid_rag"]["healthy"] = True
            except Exception as e:
                health["hybrid_rag"]["error"] = str(e)
        
        # Check Langfuse
        if self.use_langfuse:
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:3000/api/public/health", timeout=5)
                health["langfuse"]["healthy"] = True
            except Exception as e:
                health["langfuse"]["error"] = str(e)
        
        # Check vLLM
        if self.use_vllm:
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:11430/health", timeout=5)
                health["vllm"]["healthy"] = True
            except Exception as e:
                health["vllm"]["error"] = str(e)
        
        return health


# Convenience function for ROXY Core integration
def create_upgrade_manager(config: Optional[Dict] = None) -> ROXYUpgradeManager:
    """Factory function for ROXY Core integration"""
    return ROXYUpgradeManager(config)


# Migration guide as docstring
"""
## Migration Guide: ROXY Core Integration

### Step 1: Deploy Infrastructure

```bash
# Start Langfuse (observability)
cd ~/.roxy/docker/langfuse
docker-compose up -d

# Start Qdrant (for hybrid RAG)
docker run -d -p 6333:6333 qdrant/qdrant

# Build and start sandboxed MCP servers
cd ~/.roxy/docker/mcp-sandbox
docker-compose -f docker-compose.mcp.yml up -d

# Deploy vLLM (optional, requires ROCm)
cd ~/.roxy/docker/vllm-rocm
docker-compose up -d
```

### Step 2: Update ROXY Core Configuration

Add to `~/.roxy/config.json`:
```json
{
  "upgrades": {
    "USE_SANDBOXED_MCP": true,
    "USE_HYBRID_RAG": true,
    "USE_LANGFUSE": true,
    "USE_VLLM": false
  },
  "langfuse": {
    "host": "http://localhost:3000",
    "public_key": "${LANGFUSE_PUBLIC_KEY}",
    "secret_key": "${LANGFUSE_SECRET_KEY}"
  }
}
```

### Step 3: Modify roxy_core.py

Add near initialization:
```python
from ROXY_UPGRADE_INTEGRATION import create_upgrade_manager

# Initialize upgrade manager
upgrade_manager = create_upgrade_manager(config)
await upgrade_manager.initialize()

# Use in expert_router.py
observability = upgrade_manager.get_observability()
if observability:
    with observability.trace_llm_call(model="qwen2.5-coder:14b") as trace:
        response = await generate(...)
        trace.record(response, tokens_in, tokens_out, latency_ms)
```

### Step 4: Verify Deployment

```bash
# Check component health
cd ~/.roxy
python3 ROXY_UPGRADE_INTEGRATION.py

# Test MCP sandboxing
python3 mcp/mcp_container_router.py start filesystem

# Test hybrid RAG
python3 rag/hybrid_rag_engine.py test

# Test observability
curl http://localhost:3000/api/public/health
```

### Rollback Plan

If issues occur, set feature flags to false:
```json
{
  "upgrades": {
    "USE_SANDBOXED_MCP": false,
    "USE_HYBRID_RAG": false,
    "USE_LANGFUSE": false
  }
}
```

ROXY will automatically fall back to legacy implementations.
"""


if __name__ == "__main__":
    import sys
    import json
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "health":
            # Run health check
            async def check():
                manager = create_upgrade_manager({
                    "USE_SANDBOXED_MCP": True,
                    "USE_HYBRID_RAG": True,
                    "USE_LANGFUSE": True,
                    "USE_VLLM": True
                })
                health = await manager.health_check()
                print(json.dumps(health, indent=2))
            
            asyncio.run(check())
        
        elif sys.argv[1] == "init":
            # Initialize all components
            async def init():
                manager = create_upgrade_manager({
                    "USE_SANDBOXED_MCP": True,
                    "USE_HYBRID_RAG": True,
                    "USE_LANGFUSE": True,
                    "USE_VLLM": False  # Requires manual ROCm setup
                })
                await manager.initialize()
                health = await manager.health_check()
                print("\n✅ Initialization complete")
                print(json.dumps(health, indent=2))
            
            asyncio.run(init())
        
        else:
            print("Usage: ROXY_UPGRADE_INTEGRATION.py [health|init]")
    else:
        print(__doc__)

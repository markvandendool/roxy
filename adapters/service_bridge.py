#!/usr/bin/env python3
"""
Service Bridge - Connects ~/.roxy/roxy_core.py to /opt/roxy/services/
Graceful fallback if advanced services unavailable
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("roxy.service_bridge")

# Paths
OPT_ROXY_SERVICES = Path("/opt/roxy/services")
OPT_ROXY_SERVICES_EXISTS = OPT_ROXY_SERVICES.exists() and OPT_ROXY_SERVICES.is_dir()

# Track what's available
_services_available = {}
_services_checked = False


def check_services_availability():
    """Check which advanced services are available"""
    global _services_available, _services_checked
    
    if _services_checked:
        return _services_available
    
    _services_available = {
        "llm_service": False,
        "repository_rag": False,
        "memory": False,
        "orchestrator": False,
        "observability": False,
    }
    
    if not OPT_ROXY_SERVICES_EXISTS:
        logger.debug("Advanced services directory not found, using fallback mode")
        _services_checked = True
        return _services_available
    
    # Check for LLM service
    try:
        llm_path = OPT_ROXY_SERVICES / "llm_service.py"
        if llm_path.exists():
            _services_available["llm_service"] = True
            logger.debug("✓ LLM service available")
    except Exception as e:
        logger.debug(f"LLM service check failed: {e}")
    
    # Check for RAG service
    try:
        rag_path = OPT_ROXY_SERVICES / "repository_rag.py"
        if rag_path.exists():
            _services_available["repository_rag"] = True
            logger.debug("✓ Repository RAG available")
    except Exception as e:
        logger.debug(f"RAG service check failed: {e}")
    
    # Check for memory services
    try:
        memory_dir = OPT_ROXY_SERVICES / "memory"
        if memory_dir.exists() and memory_dir.is_dir():
            _services_available["memory"] = True
            logger.debug("✓ Memory services available")
    except Exception as e:
        logger.debug(f"Memory services check failed: {e}")
    
    # Check for orchestrator
    try:
        orch_path = OPT_ROXY_SERVICES / "orchestrator.py"
        if orch_path.exists():
            _services_available["orchestrator"] = True
            logger.debug("✓ Orchestrator available")
    except Exception as e:
        logger.debug(f"Orchestrator check failed: {e}")
    
    # Check for observability
    try:
        obs_path = OPT_ROXY_SERVICES / "observability.py"
        if obs_path.exists():
            _services_available["observability"] = True
            logger.debug("✓ Observability available")
    except Exception as e:
        logger.debug(f"Observability check failed: {e}")
    
    _services_checked = True
    return _services_available


def get_llm_service():
    """Get LLM service if available, else None"""
    availability = check_services_availability()
    
    if not availability.get("llm_service"):
        return None
    
    try:
        # Add /opt/roxy/services to path temporarily
        if str(OPT_ROXY_SERVICES) not in sys.path:
            sys.path.insert(0, str(OPT_ROXY_SERVICES))
        
        from llm_service import LLMService, get_llm_service
        
        # Try to get the service
        service = get_llm_service()
        if service and service.is_available():
            logger.info("Using advanced LLM service from /opt/roxy/services")
            return service
        
        # Fallback: create new instance
        service = LLMService()
        if service and service.is_available():
            logger.info("Created new LLM service instance")
            return service
        
        return None
    except ImportError as e:
        logger.debug(f"LLM service import failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"LLM service initialization failed: {e}")
        return None


def get_rag_service(repo_path: str = None):
    """Get RAG service if available, else None"""
    availability = check_services_availability()
    
    if not availability.get("repository_rag"):
        return None
    
    try:
        # Add /opt/roxy/services to path temporarily
        if str(OPT_ROXY_SERVICES) not in sys.path:
            sys.path.insert(0, str(OPT_ROXY_SERVICES))
        
        from repository_rag import RepositoryRAG, get_repo_rag
        
        if repo_path:
            # Try to get specific repo RAG
            try:
                rag = get_repo_rag(repo_path)
                if rag:
                    logger.info(f"Using advanced RAG service for {repo_path}")
                    return rag
            except Exception as e:
                logger.debug(f"get_repo_rag failed: {e}")
        
        # Fallback: create new instance if repo_path provided
        if repo_path:
            try:
                rag = RepositoryRAG(repo_path)
                logger.info(f"Created new RAG service instance for {repo_path}")
                return rag
            except Exception as e:
                logger.debug(f"RepositoryRAG creation failed: {e}")
        
        return None
    except ImportError as e:
        logger.debug(f"RAG service import failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"RAG service initialization failed: {e}")
        return None


def get_memory_service():
    """Get memory service if available, else None"""
    availability = check_services_availability()
    
    if not availability.get("memory"):
        return None
    
    try:
        # Add /opt/roxy/services to path temporarily
        if str(OPT_ROXY_SERVICES) not in sys.path:
            sys.path.insert(0, str(OPT_ROXY_SERVICES))
        
        # Try to import memory services
        from memory.episodic_memory import EpisodicMemory
        from memory.semantic_memory import SemanticMemory
        from memory.working_memory import WorkingMemory
        
        memory_services = {
            "episodic": EpisodicMemory(),
            "semantic": SemanticMemory(),
            "working": WorkingMemory(),
        }
        
        logger.info("Using advanced memory services from /opt/roxy/services")
        return memory_services
    except ImportError as e:
        logger.debug(f"Memory services import failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Memory services initialization failed: {e}")
        return None


def get_orchestrator():
    """Get orchestrator if available, else None"""
    availability = check_services_availability()
    
    if not availability.get("orchestrator"):
        return None
    
    try:
        # Add /opt/roxy/services to path temporarily
        if str(OPT_ROXY_SERVICES) not in sys.path:
            sys.path.insert(0, str(OPT_ROXY_SERVICES))
        
        from orchestrator import RoxyOrchestrator
        
        orchestrator = RoxyOrchestrator()
        logger.info("Using advanced orchestrator from /opt/roxy/services")
        return orchestrator
    except ImportError as e:
        logger.debug(f"Orchestrator import failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Orchestrator initialization failed: {e}")
        return None


def get_observability():
    """Get observability service if available, else None"""
    availability = check_services_availability()
    
    if not availability.get("observability"):
        return None
    
    try:
        # Add /opt/roxy/services to path temporarily
        if str(OPT_ROXY_SERVICES) not in sys.path:
            sys.path.insert(0, str(OPT_ROXY_SERVICES))
        
        from observability import RoxyObservability
        
        obs = RoxyObservability()
        logger.info("Using advanced observability from /opt/roxy/services")
        return obs
    except ImportError as e:
        logger.debug(f"Observability import failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Observability initialization failed: {e}")
        return None


def is_advanced_mode() -> bool:
    """Check if any advanced services are available"""
    availability = check_services_availability()
    return any(availability.values())


def get_availability_report() -> Dict[str, bool]:
    """Get report of which services are available"""
    return check_services_availability().copy()














#!/usr/bin/env python3
"""
Expert Router - Intelligent query routing to specialized models
Uses phi-2 for fast classification and routes to domain experts
"""
import logging
import json
import time
import asyncio
import httpx
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger("roxy.expert_router")


class QueryType(Enum):
    """Types of queries for routing decisions."""
    CODE = "code"
    MATH = "math"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    REASONING = "reasoning"
    BROADCAST = "broadcast"
    GENERAL = "general"


@dataclass
class ModelSpec:
    """Specification for a model in the expert pool."""
    name: str
    confidence: float
    size_gb: float
    specialty: str
    keep_alive: str = "0"  # Release VRAM when not in use


class ExpertRouter:
    """
    Mixture-of-Experts router for intelligent query routing.
    
    Features:
    - Ultra-fast classification with phi-2 (~100ms)
    - Domain-specific expert model routing
    - Ensemble queries for critical importance
    - Performance tracking for adaptive routing
    - Graceful fallback to default model
    """
    
    # Expert model matrix: QueryType -> [(model, confidence)]
    # Updated model names to match installed models
    EXPERT_MODELS: Dict[QueryType, List[ModelSpec]] = {
        QueryType.CODE: [
            ModelSpec("qwen2.5-coder:14b", 1.0, 9.0, "Primary coder"),
            ModelSpec("deepseek-coder:6.7b", 0.8, 3.8, "Code backup"),
        ],
        QueryType.MATH: [
            ModelSpec("wizard-math:7b", 1.0, 4.1, "Math specialist"),
            ModelSpec("qwen2.5-coder:14b", 0.7, 9.0, "Can do math"),
        ],
        QueryType.CREATIVE: [
            ModelSpec("llama3:8b", 0.9, 4.7, "Creative writing"),
            ModelSpec("qwen2.5-coder:14b", 0.6, 9.0, "Good backup"),
        ],
        QueryType.REASONING: [
            ModelSpec("qwen2.5:32b", 1.0, 19.0, "Best reasoning"),
            ModelSpec("qwen2.5-coder:14b", 0.8, 9.0, "Also good"),
        ],
        QueryType.TECHNICAL: [
            ModelSpec("qwen2.5-coder:14b", 1.0, 9.0, "Technical docs"),
            ModelSpec("llama3:8b", 0.7, 4.7, "Backup"),
        ],
        QueryType.BROADCAST: [
            ModelSpec("llama3:8b", 0.8, 4.7, "Creative content"),
            ModelSpec("qwen2.5:32b", 0.8, 19.0, "Analysis"),
            ModelSpec("qwen2.5-coder:14b", 0.6, 9.0, "Technical aspects"),
        ],
        QueryType.GENERAL: [
            ModelSpec("llama3:8b", 1.0, 4.7, "Fast general"),
            ModelSpec("qwen2.5-coder:14b", 0.8, 9.0, "Solid backup"),
        ]
    }
    
    # Classification keywords for fast pre-routing
    KEYWORD_PATTERNS = {
        QueryType.CODE: [
            'code', 'function', 'class', 'debug', 'implement', 'program',
            'python', 'javascript', 'typescript', 'rust', 'golang', 'java',
            'api', 'database', 'sql', 'git', 'docker', 'kubernetes',
            'bug', 'error', 'exception', 'syntax', 'compile', 'build'
        ],
        QueryType.MATH: [
            'calculate', 'solve', 'equation', 'formula', 'math', 'algebra',
            'calculus', 'statistics', 'probability', 'geometry', 'prove',
            'sum', 'product', 'integral', 'derivative', 'matrix', 'vector'
        ],
        QueryType.CREATIVE: [
            'write', 'story', 'poem', 'creative', 'imagine', 'fiction',
            'character', 'plot', 'dialogue', 'narrative', 'describe',
            'blog', 'article', 'essay', 'script', 'lyrics'
        ],
        QueryType.TECHNICAL: [
            'explain', 'how does', 'what is', 'documentation', 'tutorial',
            'guide', 'architecture', 'system', 'design', 'protocol'
        ],
        QueryType.REASONING: [
            'analyze', 'compare', 'evaluate', 'logic', 'reason', 'why',
            'pros and cons', 'argument', 'decision', 'strategy', 'plan'
        ],
        QueryType.BROADCAST: [
            'stream', 'broadcast', 'youtube', 'twitch', 'content', 'viral',
            'thumbnail', 'title', 'audience', 'engagement', 'growth',
            'podcast', 'video', 'live', 'obs', 'overlay'
        ]
    }
    
    def __init__(self,
                 ollama_url: str = "http://localhost:11434",
                 classifier_model: str = "phi:2.7b",
                 default_model: str = "qwen2.5-coder:14b"):
        """
        Initialize expert router.
        
        Args:
            ollama_url: Ollama API URL
            classifier_model: Fast model for classification
            default_model: Fallback model
        """
        self.ollama_url = ollama_url
        self.classifier_model = classifier_model
        self.default_model = default_model
        
        # Performance tracking
        self.performance_history: Dict[str, Dict[str, Any]] = {}
        self.classification_cache: Dict[str, QueryType] = {}
        
        # Available models (updated on first use)
        self._available_models: Optional[List[str]] = None
    
    async def _get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if self._available_models is not None:
            return self._available_models
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self._available_models = [m['name'] for m in data.get('models', [])]
                    logger.info(f"Available models: {self._available_models}")
                    return self._available_models
        except Exception as e:
            logger.warning(f"Failed to get models: {e}")
        
        return []
    
    def _keyword_classify(self, query: str) -> Optional[QueryType]:
        """Fast keyword-based classification."""
        query_lower = query.lower()
        
        scores = {}
        for query_type, keywords in self.KEYWORD_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[query_type] = score
        
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] >= 2:  # Confident match
                return best_type
        
        return None
    
    async def classify_query(self, query: str) -> Tuple[QueryType, float]:
        """
        Classify query type using fast LLM classification.
        
        Args:
            query: The query to classify
            
        Returns:
            Tuple of (QueryType, confidence)
        """
        # Check cache first
        cache_key = query[:100]  # Use first 100 chars as key
        if cache_key in self.classification_cache:
            return self.classification_cache[cache_key], 0.9
        
        # Try keyword classification first (instant)
        keyword_result = self._keyword_classify(query)
        if keyword_result:
            self.classification_cache[cache_key] = keyword_result
            return keyword_result, 0.85
        
        # Use LLM classification
        try:
            classification_prompt = f"""Classify this query into ONE category. Reply with ONLY the category name.

Categories:
- code: programming, debugging, algorithms, APIs
- math: calculations, equations, proofs, statistics  
- creative: writing, stories, poems, content creation
- technical: explanations, documentation, how-to guides
- reasoning: logic, analysis, decisions, comparisons
- broadcast: streaming, YouTube, content optimization
- general: everything else

Query: {query[:500]}

Category:"""
            
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.classifier_model,
                        "prompt": classification_prompt,
                        "stream": False,
                        "options": {
                            "num_predict": 10,
                            "temperature": 0.1
                        }
                    },
                    timeout=10
                )
                
                elapsed = time.time() - start_time
                logger.debug(f"Classification took {elapsed:.2f}s")
                
                if response.status_code == 200:
                    result = response.json()
                    category = result.get('response', '').strip().lower()
                    
                    # Map to QueryType
                    for qtype in QueryType:
                        if qtype.value in category:
                            self.classification_cache[cache_key] = qtype
                            return qtype, 0.9
                            
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
        
        # Default to general
        return QueryType.GENERAL, 0.5
    
    async def is_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        available = await self._get_available_models()
        
        # Check exact match or partial match
        for m in available:
            if model in m or m in model:
                return True
        
        return False
    
    async def query_model(self, 
                         model: str, 
                         prompt: str,
                         system: str = None,
                         max_tokens: int = 2048,
                         temperature: float = 0.7) -> str:
        """
        Query a specific model.
        
        Args:
            model: Model name
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Model response text
        """
        start_time = time.time()
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature
                }
            }
            
            if system:
                payload["system"] = system
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=120
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('response', '')
                    
                    # Track performance
                    self._track_performance(model, elapsed, len(response_text))
                    
                    return response_text
                else:
                    logger.error(f"Model query failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Model query error: {e}")
        
        return ""
    
    def _track_performance(self, model: str, elapsed: float, response_length: int):
        """Track model performance metrics."""
        if model not in self.performance_history:
            self.performance_history[model] = {
                'queries': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'total_chars': 0,
                'failures': 0
            }
        
        stats = self.performance_history[model]
        stats['queries'] += 1
        stats['total_time'] += elapsed
        stats['avg_time'] = stats['total_time'] / stats['queries']
        stats['total_chars'] += response_length
    
    async def route(self, 
                   query: str, 
                   context: Dict = None,
                   system: str = None) -> str:
        """
        Route query to appropriate expert model.
        
        Args:
            query: User query
            context: Optional context with importance level
            system: Optional system prompt
            
        Returns:
            Response from selected expert model
        """
        context = context or {}
        importance = context.get('importance', 'normal')
        
        # Step 1: Classify query
        query_type, confidence = await self.classify_query(query)
        logger.info(f"Query classified as {query_type.value} (confidence={confidence:.2f})")
        
        # Step 2: Get expert models
        experts = self.EXPERT_MODELS.get(query_type, self.EXPERT_MODELS[QueryType.GENERAL])
        
        # Step 3: Route based on importance
        if importance == 'critical':
            # Use ensemble for critical queries
            return await self.ensemble_query(query, experts[:3], system)
        elif importance == 'fast':
            # Use fastest available model
            return await self.query_fastest(query, experts, system)
        else:
            # Use best single model
            return await self.query_best(query, experts, system)
    
    async def query_best(self, 
                        query: str, 
                        experts: List[ModelSpec],
                        system: str = None) -> str:
        """Query the best available expert model."""
        for expert in experts:
            if await self.is_model_available(expert.name):
                logger.info(f"Routing to {expert.name} ({expert.specialty})")
                return await self.query_model(expert.name, query, system)
        
        # Fallback to default
        logger.info(f"No experts available, using default: {self.default_model}")
        return await self.query_model(self.default_model, query, system)
    
    async def query_fastest(self,
                           query: str,
                           experts: List[ModelSpec],
                           system: str = None) -> str:
        """Query the fastest available model (smallest size)."""
        # Sort by size
        available_experts = []
        for expert in experts:
            if await self.is_model_available(expert.name):
                available_experts.append(expert)
        
        if available_experts:
            fastest = min(available_experts, key=lambda e: e.size_gb)
            logger.info(f"Fast routing to {fastest.name} ({fastest.size_gb}GB)")
            return await self.query_model(fastest.name, query, system)
        
        return await self.query_model(self.default_model, query, system)
    
    async def ensemble_query(self,
                            query: str,
                            experts: List[ModelSpec],
                            system: str = None) -> str:
        """
        Query multiple experts and synthesize the best response.
        
        Args:
            query: User query
            experts: List of expert models
            system: Optional system prompt
            
        Returns:
            Synthesized response from multiple experts
        """
        # Get available experts
        available = []
        for expert in experts:
            if await self.is_model_available(expert.name):
                available.append(expert)
        
        if len(available) < 2:
            # Not enough for ensemble, use single best
            return await self.query_best(query, experts, system)
        
        logger.info(f"Ensemble query with {len(available)} models")
        
        # Query all experts in parallel
        tasks = [
            self.query_model(expert.name, query, system)
            for expert in available[:3]  # Max 3 for ensemble
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        valid_responses = [r for r in responses if isinstance(r, str) and r]
        
        if not valid_responses:
            return await self.query_model(self.default_model, query, system)
        
        if len(valid_responses) == 1:
            return valid_responses[0]
        
        # Synthesize responses
        synthesis_prompt = f"""Given these {len(valid_responses)} expert responses to the query: "{query[:200]}"

{chr(10).join([f"Expert {i+1}: {r[:500]}" for i, r in enumerate(valid_responses)])}

Synthesize the best comprehensive response, combining the strengths of each expert. 
Be concise and focus on the most accurate and helpful information:"""
        
        logger.info("Synthesizing ensemble response")
        return await self.query_model(self.default_model, synthesis_prompt, system)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            'classifier_model': self.classifier_model,
            'default_model': self.default_model,
            'cached_classifications': len(self.classification_cache),
            'model_performance': self.performance_history
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check router health."""
        status = {
            'healthy': False,
            'classifier_available': False,
            'experts_available': [],
            'details': {}
        }
        
        try:
            # Check classifier
            status['classifier_available'] = await self.is_model_available(self.classifier_model)
            
            # Check experts
            for query_type, experts in self.EXPERT_MODELS.items():
                for expert in experts:
                    if await self.is_model_available(expert.name):
                        if expert.name not in status['experts_available']:
                            status['experts_available'].append(expert.name)
            
            status['healthy'] = len(status['experts_available']) > 0
            status['details']['available_count'] = len(status['experts_available'])
            
        except Exception as e:
            status['details']['error'] = str(e)
        
        return status


# Synchronous wrapper for non-async contexts
class ExpertRouterSync:
    """Synchronous wrapper for ExpertRouter."""
    
    def __init__(self, **kwargs):
        self._async_router = ExpertRouter(**kwargs)
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
    
    def route(self, query: str, context: Dict = None, system: str = None) -> str:
        loop = self._get_loop()
        return loop.run_until_complete(
            self._async_router.route(query, context, system)
        )
    
    def classify_query(self, query: str) -> Tuple[QueryType, float]:
        loop = self._get_loop()
        return loop.run_until_complete(
            self._async_router.classify_query(query)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        return self._async_router.get_stats()
    
    def health_check(self) -> Dict[str, Any]:
        loop = self._get_loop()
        return loop.run_until_complete(
            self._async_router.health_check()
        )


# Singleton instance
_router_instance: Optional[ExpertRouterSync] = None


def get_router() -> ExpertRouterSync:
    """Get global router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ExpertRouterSync()
    return _router_instance

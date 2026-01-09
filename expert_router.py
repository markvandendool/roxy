#!/usr/bin/env python3
"""
Expert Router - Intelligent query routing to specialized models.
Supports dual Ollama pools for BIG (GPU1) and FAST (GPU0) inference lanes.
"""
import logging
import json
import time
import asyncio
import httpx
import os
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

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
    SECRETARY = "secretary"
    TRIAGE = "triage"
    SCHEDULING = "scheduling"
    SUMMARY = "summary"


class GPUPool(Enum):
    """GPU pools for routing."""
    BIG = "big"      # GPU1 / heavy workloads
    FAST = "fast"    # GPU0 / summaries + secretary


@dataclass
class ModelSpec:
    """Specification for a model in the expert pool."""
    name: str
    confidence: float
    size_gb: float
    specialty: str
    keep_alive: str = "0"  # Release VRAM when not in use
    pool: GPUPool = GPUPool.BIG


@dataclass
class RouteDecision:
    """Full trace of a routing decision for observability."""
    model: str
    pool: GPUPool
    url: str
    reason: str
    query_type: QueryType
    confidence: float
    fallback: bool = False


class ExpertRouter:
    """
    Mixture-of-Experts router for intelligent query routing.
    Maintains historical dual-pool architecture with explicit BIG/FAST lanes.
    
    Features:
    - Ultra-fast classification with phi-2 (~100ms)
    - Deterministic pool selection (BIG vs FAST)
    - Performance tracking for adaptive routing
    - Graceful fallback to default model per pool
    - Full trace metadata for observability
    """
    
    # Expert model matrix: QueryType -> models with pool assignment
    EXPERT_MODELS: Dict[QueryType, List[ModelSpec]] = {
        QueryType.CODE: [
            ModelSpec("qwen2.5-coder:14b", 1.0, 9.0, "Primary coder", pool=GPUPool.BIG),
            ModelSpec("deepseek-coder:6.7b", 0.8, 3.8, "Code backup", pool=GPUPool.BIG),
        ],
        QueryType.MATH: [
            ModelSpec("wizard-math:7b", 1.0, 4.1, "Math specialist", pool=GPUPool.BIG),
            ModelSpec("qwen2.5-coder:14b", 0.7, 9.0, "Can do math", pool=GPUPool.BIG),
        ],
        QueryType.CREATIVE: [
            ModelSpec("llama3:8b", 0.9, 4.7, "Creative writing", pool=GPUPool.BIG),
            ModelSpec("qwen2.5-coder:14b", 0.6, 9.0, "Good backup", pool=GPUPool.BIG),
        ],
        QueryType.REASONING: [
            ModelSpec("qwen2.5:32b", 1.0, 19.0, "Best reasoning", pool=GPUPool.BIG),
            ModelSpec("qwen2.5-coder:14b", 0.8, 9.0, "Also good", pool=GPUPool.BIG),
        ],
        QueryType.TECHNICAL: [
            ModelSpec("qwen2.5-coder:14b", 1.0, 9.0, "Technical docs", pool=GPUPool.BIG),
            ModelSpec("llama3:8b", 0.7, 4.7, "Backup", pool=GPUPool.BIG),
        ],
        QueryType.BROADCAST: [
            ModelSpec("llama3:8b", 0.8, 4.7, "Creative content", pool=GPUPool.BIG),
            ModelSpec("qwen2.5:32b", 0.8, 19.0, "Analysis", pool=GPUPool.BIG),
            ModelSpec("qwen2.5-coder:14b", 0.6, 9.0, "Technical aspects", pool=GPUPool.BIG),
        ],
        QueryType.GENERAL: [
            ModelSpec("llama3:8b", 1.0, 4.7, "Fast general", pool=GPUPool.BIG),
            ModelSpec("qwen2.5-coder:14b", 0.8, 9.0, "Solid backup", pool=GPUPool.BIG),
        ],
        QueryType.SECRETARY: [
            ModelSpec("phi:2.7b", 1.0, 1.6, "Secretary default", pool=GPUPool.FAST),
            ModelSpec("llama3:8b", 0.5, 4.7, "Secretary fallback", pool=GPUPool.BIG),
        ],
        QueryType.TRIAGE: [
            ModelSpec("phi:2.7b", 1.0, 1.6, "Inbox triage", pool=GPUPool.FAST),
            ModelSpec("llama3:8b", 0.5, 4.7, "Triage fallback", pool=GPUPool.BIG),
        ],
        QueryType.SCHEDULING: [
            ModelSpec("phi:2.7b", 1.0, 1.6, "Scheduling default", pool=GPUPool.FAST),
            ModelSpec("llama3:8b", 0.5, 4.7, "Scheduling fallback", pool=GPUPool.BIG),
        ],
        QueryType.SUMMARY: [
            ModelSpec("phi:2.7b", 1.0, 1.6, "Summarization", pool=GPUPool.FAST),
            ModelSpec("llama3:8b", 0.6, 4.7, "Summary fallback", pool=GPUPool.BIG),
        ],
    }

    # Task types that should prefer the FAST lane explicitly
    FAST_POOL_TASKS = {
        QueryType.SECRETARY,
        QueryType.TRIAGE,
        QueryType.SCHEDULING,
        QueryType.SUMMARY,
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
        ],
        QueryType.SECRETARY: [
            'email', 'draft', 'reply', 'message', 'reminder', 'notify',
            'quick', 'simple', 'brief', 'short', 'assistant', 'notes'
        ],
        QueryType.TRIAGE: [
            'inbox', 'triage', 'priority', 'urgent', 'important', 'filter',
            'sort', 'categorize', 'classify'
        ],
        QueryType.SCHEDULING: [
            'calendar', 'schedule', 'meeting', 'appointment', 'time',
            'when', 'available', 'free', 'book', 'slot'
        ],
        QueryType.SUMMARY: [
            'summarize', 'summary', 'tl;dr', 'tldr', 'key points', 'highlights',
            'overview', 'gist', 'recap', 'condense', 'bullet points'
        ],
    }
    
    def __init__(self,
                 ollama_url: str = None,
                 classifier_model: str = "phi:2.7b",
                 default_model: str = "qwen2.5-coder:14b"):
        """
        Initialize expert router.
        
        Args:
            ollama_url: Legacy Ollama API URL (defaults to BIG pool)
            classifier_model: Fast model for classification
            default_model: Fallback model for BIG pool
        """
        # Pool endpoints (explicit dual-pool default)
        self.big_pool_url = os.getenv("OLLAMA_BIG_URL", "http://127.0.0.1:11435")
        self.fast_pool_url = os.getenv("OLLAMA_FAST_URL", "http://127.0.0.1:11435")

        # Legacy compatibility
        self.ollama_url = ollama_url or self.big_pool_url
        self.classifier_model = classifier_model
        self.default_model = default_model

        classifier_pool_env = os.getenv("CLASSIFIER_POOL", GPUPool.FAST.value).lower()
        self.classifier_pool = GPUPool.FAST if classifier_pool_env == GPUPool.FAST.value else GPUPool.BIG

        # Pool defaults allow overrides per environment
        self.big_default = os.getenv("OLLAMA_BIG_DEFAULT", default_model)
        self.fast_default = os.getenv("OLLAMA_FAST_DEFAULT", "phi:2.7b")
        self.fast_tiny = os.getenv("OLLAMA_FAST_TINY", "phi:2.7b")

        # Performance tracking
        self.performance_history: Dict[str, Dict[str, Any]] = {}
        self.classification_cache: Dict[str, QueryType] = {}

        # Available models cache per pool (updated lazily)
        self._available_models: Dict[GPUPool, Optional[List[str]]] = {
            GPUPool.BIG: None,
            GPUPool.FAST: None,
        }

        self._last_route: Optional[RouteDecision] = None

        logger.info("ExpertRouter initialized: BIG=%s FAST=%s", self.big_pool_url, self.fast_pool_url)
    
    def _default_for_pool(self, pool: GPUPool) -> str:
        """Return fallback model for a pool."""
        return self.fast_default if pool == GPUPool.FAST else self.big_default

    def _pool_priority_for(self, query_type: QueryType, importance: str = "normal") -> List[GPUPool]:
        """Determine pool priority order for a query."""
        if importance == "fast":
            return [GPUPool.FAST, GPUPool.BIG]

        if query_type in self.FAST_POOL_TASKS:
            return [GPUPool.FAST, GPUPool.BIG]

        if importance == "critical":
            return [GPUPool.BIG, GPUPool.FAST]

        return [GPUPool.BIG, GPUPool.FAST]

    def _record_route(self, decision: RouteDecision):
        """Persist the most recent routing decision for observability."""
        self._last_route = decision
        logger.info(
            "Routing %s query -> %s via %s (pool=%s, fallback=%s)",
            decision.query_type.value,
            decision.model,
            decision.reason,
            decision.pool.value,
            decision.fallback,
        )

    async def _route_to_model(
        self,
        model: str,
        pool: GPUPool,
        query: str,
        query_type: QueryType,
        confidence: float,
        reason: str,
        system: Optional[str] = None,
        fallback: bool = False,
    ) -> str:
        """Record decision then execute the model query."""
        decision = RouteDecision(
            model=model,
            pool=pool,
            url=self.get_pool_url(pool),
            reason=reason,
            query_type=query_type,
            confidence=confidence,
            fallback=fallback,
        )
        self._record_route(decision)
        return await self.query_model(model, query, system=system, pool=pool)
    
    def get_pool_url(self, pool: GPUPool) -> str:
        """Return URL for the requested pool."""
        return self.fast_pool_url if pool == GPUPool.FAST else self.big_pool_url

    async def _get_available_models(self, pool: GPUPool = GPUPool.BIG) -> List[str]:
        """Get list of available Ollama models for a specific pool."""
        if self._available_models[pool] is not None:
            return self._available_models[pool]

        url = self.get_pool_url(pool)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = [m['name'] for m in data.get('models', [])]
                    self._available_models[pool] = models
                    logger.info("Available models on %s pool: %s", pool.value, models)
                    return models
        except Exception as e:
            logger.warning("Failed to get models from %s pool (%s): %s", pool.value, url, e)

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
            
            classifier_url = self.get_pool_url(self.classifier_pool)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{classifier_url}/api/generate",
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
            logger.warning("LLM classification failed via %s pool: %s", self.classifier_pool.value, e)
        
        # Default to general
        return QueryType.GENERAL, 0.5
    
    async def is_model_available(self, model: str, pool: GPUPool = GPUPool.BIG) -> bool:
        """Check if a model is available on a specific pool."""
        available = await self._get_available_models(pool)
        
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
                         temperature: float = 0.7,
                         pool: GPUPool = GPUPool.BIG) -> str:
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
            
            url = self.get_pool_url(pool)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url}/api/generate",
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
                    logger.error(
                        "Model query failed (%s pool %s): %s",
                        pool.value,
                        url,
                        response.status_code,
                    )
                    
        except Exception as e:
            logger.error("Model query error (%s pool): %s", pool.value, e)
        
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
        pool_priority = self._pool_priority_for(query_type, importance)

        # Step 3: Route based on importance
        if importance == 'critical':
            # Use ensemble for critical queries
            return await self.ensemble_query(query, experts[:3], query_type, confidence, pool_priority, system)
        elif importance == 'fast':
            # Use fastest available model
            return await self.query_fastest(query, experts, query_type, confidence, pool_priority, system)
        else:
            # Use best single model
            return await self.query_best(query, experts, query_type, confidence, pool_priority, system)
    
    async def query_best(
        self,
        query: str,
        experts: List[ModelSpec],
        query_type: QueryType,
        confidence: float,
        pool_priority: List[GPUPool],
        system: str = None,
    ) -> str:
        """Query the best available expert model, honoring pool priority."""
        for pool in pool_priority:
            for expert in experts:
                if expert.pool != pool:
                    continue
                if await self.is_model_available(expert.name, pool):
                    reason = expert.specialty or "primary"
                    return await self._route_to_model(
                        expert.name,
                        pool,
                        query,
                        query_type,
                        confidence,
                        reason,
                        system=system,
                    )

        # Fallback to pool defaults in priority order
        for pool in pool_priority:
            fallback_model = self._default_for_pool(pool)
            if fallback_model and await self.is_model_available(fallback_model, pool):
                return await self._route_to_model(
                    fallback_model,
                    pool,
                    query,
                    query_type,
                    confidence,
                    f"default:{pool.value}",
                    system=system,
                    fallback=True,
                )

        # Ultimate fallback to BIG default even if availability check fails
        fallback_model = self._default_for_pool(GPUPool.BIG)
        logger.warning("No pool models available, forcing big default %s", fallback_model)
        return await self._route_to_model(
            fallback_model,
            GPUPool.BIG,
            query,
            query_type,
            confidence,
            "ultimate-default",
            system=system,
            fallback=True,
        )
    
    async def query_fastest(
        self,
        query: str,
        experts: List[ModelSpec],
        query_type: QueryType,
        confidence: float,
        pool_priority: List[GPUPool],
        system: str = None,
    ) -> str:
        """Query the fastest available model (smallest size) within pool priorities."""
        available_experts: List[ModelSpec] = []
        for pool in pool_priority:
            for expert in experts:
                if expert.pool != pool:
                    continue
                if await self.is_model_available(expert.name, pool):
                    available_experts.append(expert)

        if available_experts:
            fastest = min(available_experts, key=lambda e: e.size_gb)
            reason = f"fastest:{fastest.size_gb}GB"
            return await self._route_to_model(
                fastest.name,
                fastest.pool,
                query,
                query_type,
                confidence,
                reason,
                system=system,
            )

        # Fallback mirrors best logic but biases fast pool first
        for pool in pool_priority:
            fallback_model = self._default_for_pool(pool)
            if fallback_model and await self.is_model_available(fallback_model, pool):
                return await self._route_to_model(
                    fallback_model,
                    pool,
                    query,
                    query_type,
                    confidence,
                    f"fast-default:{pool.value}",
                    system=system,
                    fallback=True,
                )

        fallback_model = self._default_for_pool(GPUPool.BIG)
        logger.warning("Fast routing fallback to big default %s", fallback_model)
        return await self._route_to_model(
            fallback_model,
            GPUPool.BIG,
            query,
            query_type,
            confidence,
            "fast-ultimate",
            system=system,
            fallback=True,
        )
    
    async def ensemble_query(
        self,
        query: str,
        experts: List[ModelSpec],
        query_type: QueryType,
        confidence: float,
        pool_priority: List[GPUPool],
        system: str = None,
    ) -> str:
        """Query multiple experts and synthesize the best response."""
        available: List[ModelSpec] = []
        for pool in pool_priority:
            for expert in experts:
                if expert.pool != pool:
                    continue
                if await self.is_model_available(expert.name, pool):
                    available.append(expert)

        if len(available) < 2:
            # Not enough for ensemble, use single best
            return await self.query_best(query, experts, query_type, confidence, pool_priority, system)

        logger.info("Ensemble query with %s experts", len(available))

        tasks = [
            self.query_model(expert.name, query, system, pool=expert.pool)
            for expert in available[:3]
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        valid_responses = [r for r in responses if isinstance(r, str) and r]
        
        if not valid_responses:
            return await self.query_best(query, experts, query_type, confidence, pool_priority, system)
        
        if len(valid_responses) == 1:
            for expert, response in zip(available[:3], responses):
                if isinstance(response, str) and response:
                    decision = RouteDecision(
                        model=expert.name,
                        pool=expert.pool,
                        url=self.get_pool_url(expert.pool),
                        reason="ensemble-single",
                        query_type=query_type,
                        confidence=confidence,
                        fallback=False,
                    )
                    self._record_route(decision)
                    return response
            return valid_responses[0]
        
        # Synthesize responses
        synthesis_prompt = f"""Given these {len(valid_responses)} expert responses to the query: "{query[:200]}"

{chr(10).join([f"Expert {i+1}: {r[:500]}" for i, r in enumerate(valid_responses)])}

Synthesize the best comprehensive response, combining the strengths of each expert. 
Be concise and focus on the most accurate and helpful information:"""
        
        logger.info("Synthesizing ensemble response")
        return await self._route_to_model(
            self._default_for_pool(GPUPool.BIG),
            GPUPool.BIG,
            synthesis_prompt,
            query_type,
            confidence,
            "ensemble-synthesis",
            system=system,
            fallback=True,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        last_route_serialized = None
        if self._last_route:
            last_route_serialized = {
                'model': self._last_route.model,
                'pool': self._last_route.pool.value,
                'url': self._last_route.url,
                'reason': self._last_route.reason,
                'query_type': self._last_route.query_type.value,
                'confidence': self._last_route.confidence,
                'fallback': self._last_route.fallback,
            }
        return {
            'classifier_model': self.classifier_model,
            'default_model': self.default_model,
            'cached_classifications': len(self.classification_cache),
            'model_performance': self.performance_history,
            'big_pool_url': self.big_pool_url,
            'fast_pool_url': self.fast_pool_url,
            'last_route': last_route_serialized,
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
            status['classifier_available'] = await self.is_model_available(self.classifier_model, self.classifier_pool)
            
            # Check experts
            for query_type, experts in self.EXPERT_MODELS.items():
                for expert in experts:
                    if await self.is_model_available(expert.name, expert.pool):
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


# =============================================================================
# SKILLS INTEGRATION (RU-011)
# =============================================================================
# Route queries to dynamically loaded skills before falling back to LLM experts

try:
    from skills_registry import (
        _loaded_skills,
        find_skill_by_capability,
        find_skill_by_keyword
    )
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    _loaded_skills = {}


class SkillsAwareRouter:
    """
    Enhanced router that checks skills before LLM experts.
    
    Priority:
    1. Exact skill capability match
    2. Keyword-based skill match
    3. LLM expert routing (existing logic)
    """
    
    MIN_SKILL_CONFIDENCE = 0.3
    
    def __init__(self):
        self._llm_router = ExpertRouterSync()
    
    def _extract_keywords(self, query: str) -> list:
        """Extract keywords from query"""
        stopwords = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'to', 'of',
            'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'please', 'help', 'want', 'need', 'like', 'how', 'what', 'why',
            'when', 'where', 'which', 'who', 'i', 'me', 'my', 'we', 'you'
        }
        import re
        words = re.findall(r'\b\w+\b', query.lower())
        return [w for w in words if w not in stopwords and len(w) > 2]
    
    def _score_skill(self, skill_name: str, query: str, keywords: list) -> tuple:
        """Score a skill's relevance to query. Returns (score, reason)."""
        if skill_name not in _loaded_skills:
            return 0.0, "not_loaded"
        
        skill = _loaded_skills[skill_name]
        manifest = skill.manifest
        score = 0.0
        reasons = []
        
        query_lower = query.lower()
        
        # Check keywords
        skill_keywords = [k.lower() for k in manifest.keywords]
        for kw in keywords:
            if kw in skill_keywords:
                score += 0.3
                reasons.append(f"kw:{kw}")
        
        # Check capabilities
        for cap in manifest.capabilities:
            if cap.lower() in query_lower:
                score += 0.4
                reasons.append(f"cap:{cap}")
        
        # Check skill name
        if manifest.name.lower() in query_lower:
            score += 0.5
            reasons.append("name")
        
        return min(1.0, score), ", ".join(reasons[:3]) if reasons else "no_match"
    
    def route_to_skill(self, query: str) -> dict:
        """
        Check if query should route to a skill.
        
        Returns:
            {
                "routed": True/False,
                "skill": "skill_name" or None,
                "confidence": float,
                "reason": str
            }
        """
        if not SKILLS_AVAILABLE or not _loaded_skills:
            return {"routed": False, "skill": None, "confidence": 0, "reason": "no_skills"}
        
        keywords = self._extract_keywords(query)
        
        # Score all skills
        scores = []
        for skill_name in _loaded_skills:
            score, reason = self._score_skill(skill_name, query, keywords)
            if score >= self.MIN_SKILL_CONFIDENCE:
                scores.append((skill_name, score, reason))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores:
            best = scores[0]
            return {
                "routed": True,
                "skill": best[0],
                "confidence": best[1],
                "reason": best[2],
                "alternatives": [(s[0], s[1]) for s in scores[1:3]]
            }
        
        return {"routed": False, "skill": None, "confidence": 0, "reason": "below_threshold"}
    
    async def route_async(self, query: str, context: dict = None, system: str = None) -> dict:
        """
        Route query with skills-first priority.
        
        Returns:
            {
                "target": "skill_name" | "llm_expert",
                "target_type": "skill" | "llm",
                "confidence": float,
                "response": str (if LLM) or None (if skill)
            }
        """
        # Check skills first
        skill_routing = self.route_to_skill(query)
        
        if skill_routing["routed"]:
            logger.info(f"Routed to skill: {skill_routing['skill']} ({skill_routing['confidence']:.2f})")
            return {
                "target": skill_routing["skill"],
                "target_type": "skill",
                "confidence": skill_routing["confidence"],
                "reason": skill_routing["reason"],
                "response": None  # Caller should invoke skill
            }
        
        # Fall back to LLM routing
        llm_response = await self._llm_router._async_router.route(query, context, system)
        query_type, conf = await self._llm_router._async_router.classify_query(query)
        
        return {
            "target": query_type.value,
            "target_type": "llm",
            "confidence": conf,
            "reason": f"llm_expert:{query_type.value}",
            "response": llm_response
        }
    
    def route(self, query: str, context: dict = None, system: str = None) -> dict:
        """Synchronous route with skills-first priority."""
        loop = self._llm_router._get_loop()
        return loop.run_until_complete(self.route_async(query, context, system))
    
    def get_skill_stats(self) -> dict:
        """Get skills routing statistics."""
        if not SKILLS_AVAILABLE:
            return {"available": False}
        
        return {
            "available": True,
            "loaded_skills": list(_loaded_skills.keys()),
            "skill_count": len(_loaded_skills)
        }


# Global skills-aware router
_skills_router: Optional[SkillsAwareRouter] = None


def get_skills_router() -> SkillsAwareRouter:
    """Get global skills-aware router instance."""
    global _skills_router
    if _skills_router is None:
        _skills_router = SkillsAwareRouter()
    return _skills_router

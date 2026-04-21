#!/usr/bin/env python3
"""
Prompt Templates - Structured prompts for different task types
Including MindSong/SkyBeam production-specific templates
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("roxy.prompts.templates")

# Import production monitor for real-time state
try:
    from production_monitor import get_production_summary
    PRODUCTION_MONITOR_AVAILABLE = True
except ImportError:
    PRODUCTION_MONITOR_AVAILABLE = False
    def get_production_summary():
        return "Production status unavailable"


class PromptTemplates:
    """Prompt templates for different task types"""
    
    RAG_PROMPT = """You are ROXY, a concise and accurate AI assistant. Answer based on this context from the knowledge base:

{context}

Question: {query}

Instructions:
- Answer based ONLY on the provided context
- If context doesn't contain the answer, say so clearly
- Be concise but comprehensive (2-4 sentences)
- Cite sources when relevant

Answer:"""
    
    RAG_PROMPT_DETAILED = """You are ROXY, an expert AI assistant with deep knowledge of the codebase.

Repository Context:
{context}

User Question: {query}

Provide a detailed, accurate answer based on the repository context. Include:
1. Direct answer to the question
2. Relevant code examples or file references
3. Any important caveats or limitations

If the context doesn't fully answer the question, say so and explain what information is available."""
    
    CODE_ANALYSIS_PROMPT = """You are ROXY, a code analysis expert. Analyze the following code:

{code}

Question: {query}

Provide:
1. Code analysis
2. Potential issues or improvements
3. Best practices recommendations"""
    
    GENERAL_PROMPT = """You are ROXY, a helpful AI assistant.

Question: {query}

Provide a clear, concise answer."""

    # ====== MINESONG/SKYBEAM PRODUCTION TEMPLATES ======

    PRODUCTION_STATUS_PROMPT = """You are ROXY, the MindSong Studios CEO AI. Answer production status questions with precision.

LIVE PRODUCTION STATE:
{production_summary}

MEMORY CONTEXT:
{memory}

User Question: {query}

Answer format:
- Lead with current status (rendering, queued, idle, error)
- Include specific details from LIVE PRODUCTION STATE
- Flag any blockers immediately
- Suggest next actions if relevant

Be decisive - production waits for no one."""

    RENDER_OPTIMIZATION_PROMPT = """You are ROXY, the SkyBeam production optimizer. Your job is to maximize render efficiency.

CURRENT RENDER STATE:
{context}

Question: {query}

Provide:
1. Current bottleneck analysis
2. GPU utilization recommendations
3. Queue optimization suggestions
4. Quality vs speed tradeoffs

Think like a film studio production manager."""

    MONETIZATION_PROMPT = """You are ROXY, the StackKraft monetization strategist. Your job is to maximize MindSong revenue.

CAMPAIGN STATE:
{context}

Question: {query}

Provide:
1. Campaign performance analysis
2. Revenue optimization suggestions
3. Content strategy recommendations
4. Platform-specific tactics

Think like a record label A&R executive."""

    CREATIVE_WORKFLOW_PROMPT = """You are ROXY, the MindSong creative coordinator. Your job is to support world-class music and video production.

CREATIVE CONTEXT:
{context}

MEMORY (previous creative decisions):
{memory}

Question: {query}

Support the creative process by:
1. Drawing from past creative decisions
2. Suggesting workflow optimizations
3. Connecting to technical capabilities (MQQC, Rocky AI, Luno)
4. Maintaining artistic consistency

Your goal: help create the best possible content."""

    ORCHESTRATION_PROMPT = """You are ROXY, orchestrating Luno and the MindSong agent team. Coordinate complex multi-step workflows.

AGENT STATE:
{context}

Question: {query}

Coordinate by:
1. Breaking complex tasks into agent steps
2. Identifying dependencies and parallel opportunities
3. Monitoring cross-agent handoffs
4. Ensuring end-to-end quality (MQQC checkpoints)

Think like a film director coordinating a production crew."""

    MUSIC_QUALITY_PROMPT = """You are ROXY, working with MQQC for audio excellence. Your job is music quality control.

AUDIO CONTEXT:
{context}

Question: {query}

Focus on:
1. Technical audio quality (frequency balance, dynamics, stereo)
2. Genre-appropriate processing
3. Mastering chain optimization
4. Export format for target platform

Consult Rocky AI for musical theory when relevant."""

    @classmethod
    def _get_live_production_summary(cls) -> str:
        """Fetch live production summary with safe fallback."""
        if not PRODUCTION_MONITOR_AVAILABLE:
            return "Production status unavailable"
        try:
            return get_production_summary()
        except Exception as e:
            logger.debug(f"Production summary unavailable: {e}")
            return "Production status unavailable"

    @classmethod
    def get_rag_prompt(cls, context: str, query: str, detailed: bool = False) -> str:
        """Get RAG prompt"""
        template = cls.RAG_PROMPT_DETAILED if detailed else cls.RAG_PROMPT
        return template.format(context=context, query=query)
    
    @classmethod
    def get_code_prompt(cls, code: str, query: str) -> str:
        """Get code analysis prompt"""
        return cls.CODE_ANALYSIS_PROMPT.format(code=code, query=query)
    
    @classmethod
    def get_general_prompt(cls, query: str) -> str:
        """Get general prompt"""
        return cls.GENERAL_PROMPT.format(query=query)
    
    @classmethod
    def select_prompt(cls, query: str, context: str = None, task_type: str = "rag") -> str:
        """Select appropriate prompt based on task type and query content"""
        query_lower = query.lower()

        # Production-specific detection
        if any(word in query_lower for word in [
            "render", "skybeam", "export", "queue", "gpu", "encoding",
            "shotcaller", "schedule", "deadline"
        ]):
            return cls.PRODUCTION_STATUS_PROMPT.format(
                memory=context or "No production memory available",
                production_summary=cls._get_live_production_summary(),
                query=query
            )

        if any(word in query_lower for word in [
            "monetize", "stackkraft", "revenue", "campaign", "publish",
            "distribute", "youtube", "spotify"
        ]):
            return cls.MONETIZATION_PROMPT.format(
                context=context or "No campaign context available",
                query=query
            )

        if any(word in query_lower for word in [
            "creative", "song", "music", "arrangement", "master",
            "mix", "track", "beat", "record", "produce"
        ]):
            return cls.CREATIVE_WORKFLOW_PROMPT.format(
                context=context or "No creative context",
                memory=context or "No creative memory available",
                query=query
            )

        if any(word in query_lower for word in [
            "orchestrat", "luno", "agent", "workflow", "automate",
            "pipeline", "coordinate"
        ]):
            return cls.ORCHESTRATION_PROMPT.format(
                context=context or "No agent state available",
                query=query
            )

        if any(word in query_lower for word in [
            "audio", "mqqc", "frequency", "dynamics", "mastering",
            "compress", "eq", "limiting"
        ]):
            return cls.MUSIC_QUALITY_PROMPT.format(
                context=context or "No audio context",
                query=query
            )
        
        if task_type == "rag" and context:
            is_complex = any(word in query_lower for word in ["how", "why", "explain", "analyze", "compare"])
            return cls.get_rag_prompt(context, query, detailed=is_complex)
        elif task_type == "code" and context:
            return cls.get_code_prompt(context, query)
        else:
            return cls.get_general_prompt(query)


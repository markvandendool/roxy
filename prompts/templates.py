#!/usr/bin/env python3
"""
Prompt Templates - Structured prompts for different task types
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("roxy.prompts.templates")


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
        """Select appropriate prompt based on task type"""
        query_lower = query.lower()
        
        if task_type == "rag" and context:
            # Use detailed prompt for complex queries
            is_complex = any(word in query_lower for word in ["how", "why", "explain", "analyze", "compare"])
            return cls.get_rag_prompt(context, query, detailed=is_complex)
        elif task_type == "code" and context:
            return cls.get_code_prompt(context, query)
        else:
            return cls.get_general_prompt(query)














#!/usr/bin/env python3
"""
ROXY LLM Service - Integration with Ollama and Claude API
Provides intelligent responses using LLM models
"""
import os
import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.llm')

class LLMProvider(Enum):
    OLLAMA = "ollama"
    CLAUDE = "claude"
    OPENAI = "openai"

class LLMService:
    """Unified LLM service supporting multiple providers"""
    
    def __init__(self, provider: LLMProvider = None):
        self.provider = provider or self._detect_provider()
        self.client = None
        self._init_client()
    
    def _detect_provider(self) -> LLMProvider:
        """Auto-detect available LLM provider"""
        # Check for Ollama
        if os.getenv('OLLAMA_HOST'):
            return LLMProvider.OLLAMA
        # Check for Claude
        if os.getenv('ANTHROPIC_API_KEY'):
            return LLMProvider.CLAUDE
        # Default to Ollama
        return LLMProvider.OLLAMA
    
    def _init_client(self):
        """Initialize LLM client based on provider"""
        if self.provider == LLMProvider.OLLAMA:
            try:
                from langchain_ollama import ChatOllama
                ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
                model = os.getenv('OLLAMA_MODEL', 'llama3:8b')
                self.client = ChatOllama(
                    model=model,
                    base_url=ollama_host,
                    temperature=0.7,
                )
                logger.info(f"✅ Ollama LLM initialized: {model} at {ollama_host}")
                # Verify GPU usage (Ollama auto-detects GPU)
                try:
                    import subprocess
                    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        logger.info(f"   Ollama models available (GPU auto-detected by Ollama)")
                except:
                    pass
            except ImportError:
                logger.warning("langchain-ollama not installed, LLM disabled")
                self.client = None
        elif self.provider == LLMProvider.CLAUDE:
            try:
                from anthropic import Anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    self.client = Anthropic(api_key=api_key)
                    logger.info("✅ Claude LLM initialized")
                else:
                    logger.warning("ANTHROPIC_API_KEY not set, Claude disabled")
                    self.client = None
            except ImportError:
                logger.warning("anthropic package not installed, Claude disabled")
                self.client = None
    
    async def generate_response(self, user_input: str, context: Dict = None, 
                               history: List[Dict] = None, facts: List[Dict] = None) -> str:
        """Generate intelligent response using LLM"""
        if not self.client:
            # Fallback response
            return self._fallback_response(user_input, context, history, facts)
        
        # Build prompt with context
        prompt = self._build_prompt(user_input, context, history, facts)
        
        try:
            if self.provider == LLMProvider.OLLAMA:
                return await self._generate_ollama(prompt)
            elif self.provider == LLMProvider.CLAUDE:
                return await self._generate_claude(prompt)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return self._fallback_response(user_input, context, history, facts)
    
    def _build_prompt(self, user_input: str, context: Dict, 
                     history: List[Dict], facts: List[Dict]) -> str:
        """Build prompt with context"""
        prompt_parts = []
        
        # Add system context
        prompt_parts.append("You are ROXY, a permanent, learning, resident AI assistant.")
        prompt_parts.append("You remember everything and learn from every interaction.")
        
        # Add relevant facts
        if facts:
            prompt_parts.append("\nRelevant facts I remember:")
            for fact in facts[:5]:
                prompt_parts.append(f"- {fact.get('fact', fact)}")
        
        # Add conversation history
        if history:
            prompt_parts.append("\nRecent conversation:")
            for conv in history[-3:]:
                prompt_parts.append(f"User: {conv.get('user_input', '')}")
                prompt_parts.append(f"ROXY: {conv.get('response', '')}")
        
        # Add current input
        prompt_parts.append(f"\nUser: {user_input}")
        prompt_parts.append("ROXY:")
        
        return "\n".join(prompt_parts)
    
    async def _generate_ollama(self, prompt: str) -> str:
        """Generate response using Ollama"""
        try:
            response = await self.client.ainvoke(prompt)
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def _generate_claude(self, prompt: str) -> str:
        """Generate response using Claude"""
        try:
            # Claude uses messages format
            messages = [{"role": "user", "content": prompt}]
            response = self.client.messages.create(
                model=os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022'),
                max_tokens=1024,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude error: {e}")
            raise
    
    def _fallback_response(self, user_input: str, context: Dict, 
                          history: List[Dict], facts: List[Dict]) -> str:
        """Fallback response when LLM unavailable"""
        # Simple pattern matching
        if "hello" in user_input.lower() or "hi" in user_input.lower():
            return "Hello! I'm ROXY, your resident AI assistant. How can I help you?"
        if "how are you" in user_input.lower():
            return "I'm doing well, thank you! I'm always learning and ready to help."
        if "what can you do" in user_input.lower():
            return "I can help with many things: answer questions, remember information, control your system, manage tasks, and much more!"
        return f"I understand you said: '{user_input}'. I'm processing your request. (LLM service not fully configured yet)"
    
    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.client is not None


# Global LLM service instance
_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """Get or create global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


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
            # CRITICAL: Remove services from path BEFORE any imports to avoid email conflict
            import sys
            services_path = None
            services_removed = False
            
            if '/home/mark/.roxy/services' in sys.path:
                services_path = '/home/mark/.roxy/services'
                sys.path.remove(services_path)
                services_removed = True
            
            try:
                # Now import langchain_ollama (needs standard library email, not services/email/)
                from langchain_ollama import ChatOllama
                
                ollama_host = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11435')
                model = os.getenv('OLLAMA_MODEL', 'llama3:8b')
                self.client = ChatOllama(
                    model=model,
                    base_url=ollama_host,
                    temperature=0.7,
                )
                logger.info(f"✅ Ollama LLM initialized: {model} at {ollama_host}")
                
                # Verify GPU usage
                try:
                    import subprocess
                    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        logger.info(f"   Ollama models available (GPU auto-detected by Ollama)")
                except:
                    pass
                    
            except ImportError as e:
                logger.warning(f"langchain-ollama import failed: {e}")
                self.client = None
            except Exception as e:
                logger.warning(f"Ollama initialization failed: {e}")
                self.client = None
            finally:
                # Restore services path AFTER initialization
                if services_removed and services_path:
                    sys.path.insert(0, services_path)
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
            logger.warning("LLM client not available")
            return self._fallback_response(user_input, context, history, facts)
        
        # Build prompt with context
        try:
            prompt = self._build_prompt(user_input, context, history or [], facts or [])
            logger.debug(f"Built prompt: type={type(prompt)}, length={len(str(prompt))}")
        except Exception as e:
            logger.error(f"Error building prompt: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_response(user_input, context, history, facts)
        
        try:
            if self.provider == LLMProvider.OLLAMA:
                response = await self._generate_ollama(prompt)
                if response and response.strip() and len(response.strip()) > 5:
                    return response.strip()
                else:
                    logger.warning(f"Ollama returned empty/short response: {response}")
                    return self._fallback_response(user_input, context, history, facts)
            elif self.provider == LLMProvider.CLAUDE:
                response = await self._generate_claude(prompt)
                if response and response.strip():
                    return response.strip()
                else:
                    return self._fallback_response(user_input, context, history, facts)
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_response(user_input, context, history, facts)
    
    def _build_prompt(self, user_input: str, context: Dict, 
                     history: List[Dict], facts: List[Dict]) -> str:
        """Build prompt with context - proper agent architecture"""
        # Use LangChain message format for proper conversation handling
        try:
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
            
            messages = []
            
            # System message with context
            system_content = "You are ROXY, a permanent, learning, resident AI assistant. You remember everything and learn from every interaction. Be helpful, accurate, and conversational."
            
            # Add relevant facts
            if facts:
                fact_list = "\n".join([f"- {fact.get('fact', fact) if isinstance(fact, dict) else fact}" for fact in facts[:5]])
                system_content += f"\n\nRelevant facts I remember:\n{fact_list}"
            
            messages.append(SystemMessage(content=system_content))
            
            # Add conversation history
            if history:
                for conv in history[-5:]:  # Last 5 conversations
                    user_msg = conv.get('user_input', '')
                    roxy_msg = conv.get('response', conv.get('roxy_response', ''))
                    if user_msg and user_msg.strip():
                        messages.append(HumanMessage(content=user_msg.strip()))
                    if roxy_msg and roxy_msg.strip():
                        messages.append(AIMessage(content=roxy_msg.strip()))
            
            # Add current user input
            messages.append(HumanMessage(content=user_input))
            
            # Return messages list for LangChain (Ollama ChatOllama handles this)
            return messages
        except ImportError:
            # Fallback to string format
            prompt_parts = []
            prompt_parts.append("You are ROXY, a permanent, learning, resident AI assistant.")
            
            if facts:
                prompt_parts.append("\nRelevant facts:")
                for fact in facts[:5]:
                    prompt_parts.append(f"- {fact.get('fact', fact) if isinstance(fact, dict) else fact}")
            
            if history:
                prompt_parts.append("\nRecent conversation:")
                for conv in history[-3:]:
                    prompt_parts.append(f"User: {conv.get('user_input', '')}")
                    prompt_parts.append(f"ROXY: {conv.get('response', conv.get('roxy_response', ''))}")
            
            prompt_parts.append(f"\nUser: {user_input}")
            prompt_parts.append("ROXY:")
            
            return "\n".join(prompt_parts)
    
    async def _generate_ollama(self, prompt) -> str:
        """Generate response using Ollama"""
        try:
            # Handle both message list and string prompts
            if isinstance(prompt, list):
                # LangChain messages format - ChatOllama handles this
                logger.debug(f"Calling Ollama with {len(prompt)} messages")
                response = await self.client.ainvoke(prompt)
            else:
                # String prompt - convert to message
                logger.debug(f"Calling Ollama with string prompt: {len(str(prompt))} chars")
                from langchain_core.messages import HumanMessage
                response = await self.client.ainvoke([HumanMessage(content=str(prompt))])
            
            # Handle different response types
            if hasattr(response, 'content'):
                content = response.content
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Handle list of content blocks
                    return "".join([str(item) for item in content])
                else:
                    return str(content)
            
            # Fallback to string conversion
            result = str(response)
            if result and len(result.strip()) > 0:
                return result
            
            logger.warning("Ollama returned empty response")
            raise ValueError("Empty response from Ollama")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            import traceback
            logger.error(traceback.format_exc())
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


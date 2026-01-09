#!/usr/bin/env python3
"""
Model Provider - Unified abstraction layer for seamless model swapping

Like Cursor: swap models freely while retaining all skills, memory, and personality.
The model is just the inference engine - everything else stays constant.

Usage:
    from model_provider import get_provider, set_active_model
    
    # Swap models seamlessly
    set_active_model("qwen2.5-coder:14b")
    response = get_provider().generate("write a function...")
    
    set_active_model("deepseek-coder-v2:16b")
    response = get_provider().generate("write a function...")  # Same interface
"""
import os
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("roxy.model_provider")

ROXY_DIR = Path.home() / ".roxy"
MODEL_CONFIG_FILE = ROXY_DIR / "model_config.json"


@dataclass
class ModelCapabilities:
    """Model capability profile for routing decisions"""
    context_window: int = 8192
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_function_calling: bool = False
    specialized_for: List[str] = field(default_factory=list)  # ["code", "math", "general"]
    cost_tier: str = "local"  # local, api_cheap, api_expensive


# Known model profiles (auto-detected where possible)
MODEL_PROFILES: Dict[str, ModelCapabilities] = {
    # Ollama models
    "qwen2.5-coder:14b": ModelCapabilities(
        context_window=32768,
        specialized_for=["code", "reasoning"],
        supports_json_mode=True
    ),
    "qwen2.5-coder:32b": ModelCapabilities(
        context_window=32768,
        specialized_for=["code", "reasoning"],
        supports_json_mode=True
    ),
    "deepseek-coder-v2:16b": ModelCapabilities(
        context_window=128000,
        specialized_for=["code"],
        supports_json_mode=True
    ),
    "codestral:22b": ModelCapabilities(
        context_window=32768,
        specialized_for=["code"],
        supports_json_mode=True
    ),
    "llama3:8b": ModelCapabilities(
        context_window=8192,
        specialized_for=["general", "chat"]
    ),
    "llama3:70b": ModelCapabilities(
        context_window=8192,
        specialized_for=["general", "reasoning"]
    ),
    "llama3.1:8b": ModelCapabilities(
        context_window=131072,
        specialized_for=["general", "chat"],
        supports_function_calling=True
    ),
    "llama3.2:1b": ModelCapabilities(
        context_window=131072,
        specialized_for=["general"],
    ),
    "llama3.2:3b": ModelCapabilities(
        context_window=131072,
        specialized_for=["general"],
    ),
    "mistral:7b": ModelCapabilities(
        context_window=32768,
        specialized_for=["general"]
    ),
    "mixtral:8x7b": ModelCapabilities(
        context_window=32768,
        specialized_for=["general", "reasoning"]
    ),
    "phi3:14b": ModelCapabilities(
        context_window=128000,
        specialized_for=["code", "reasoning"]
    ),
    "gemma2:9b": ModelCapabilities(
        context_window=8192,
        specialized_for=["general"]
    ),
    # API models (if configured)
    "gpt-4o": ModelCapabilities(
        context_window=128000,
        supports_json_mode=True,
        supports_function_calling=True,
        specialized_for=["code", "reasoning", "general"],
        cost_tier="api_expensive"
    ),
    "gpt-4o-mini": ModelCapabilities(
        context_window=128000,
        supports_json_mode=True,
        supports_function_calling=True,
        specialized_for=["code", "general"],
        cost_tier="api_cheap"
    ),
    "claude-3-5-sonnet": ModelCapabilities(
        context_window=200000,
        supports_json_mode=True,
        specialized_for=["code", "reasoning", "general"],
        cost_tier="api_expensive"
    ),
}


class ModelConfig:
    """Persistent model configuration"""
    
    def __init__(self):
        self.config_file = MODEL_CONFIG_FILE
        self.config = self._load()
    
    def _load(self) -> Dict[str, Any]:
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load model config: {e}")
        return self._defaults()
    
    def _defaults(self) -> Dict[str, Any]:
        return {
            "active_model": "qwen2.5-coder:14b",
            "fallback_model": "llama3:8b",
            "temperature": 0.7,
            "max_tokens": 2048,
            "model_preferences": {
                "code": ["qwen2.5-coder:14b", "deepseek-coder-v2:16b", "codestral:22b"],
                "general": ["llama3:8b", "mistral:7b", "gemma2:9b"],
                "reasoning": ["qwen2.5-coder:32b", "llama3:70b", "mixtral:8x7b"]
            },
            "ollama_url": "http://127.0.0.1:11435",
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        }
    
    def save(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save model config: {e}")
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()


class ModelProvider:
    """
    Unified model interface - swap models while keeping everything else constant.
    
    All models get the same:
    - System prompt (ROXY personality)
    - Tool access
    - RAG context injection
    - Memory/history handling
    """
    
    # ROXY's core identity - constant across all models
    SYSTEM_PROMPT = """You are ROXY, a capable AI assistant integrated into a local development environment.

CRITICAL RULES:
1. You have access to specific tools (RAG search, file operations, git, OBS control). Use them when relevant.
2. NEVER claim to have done something you haven't actually done.
3. If you don't know something, say so clearly.
4. Cite sources when using RAG context.
5. Be concise and helpful.

Your capabilities are defined by your tools, not your imagination. If a user asks you to do something you can't do, explain what you CAN do instead."""
    
    def __init__(self):
        self.config = ModelConfig()
        self._available_models: List[str] = []
        self._last_discovery = None
        self._refresh_models()
    
    def _refresh_models(self, force: bool = False):
        """Discover available models from all providers"""
        now = datetime.now()
        if not force and self._last_discovery and (now - self._last_discovery).seconds < 60:
            return
        
        self._available_models = []
        
        # Discover Ollama models
        try:
            resp = requests.get(
                f"{self.config.get('ollama_url')}/api/tags",
                timeout=5
            )
            if resp.status_code == 200:
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
                self._available_models.extend(ollama_models)
                logger.debug(f"Discovered {len(ollama_models)} Ollama models")
        except Exception as e:
            logger.debug(f"Ollama discovery failed: {e}")
        
        # Check API availability
        if self.config.get("openai_api_key"):
            self._available_models.extend(["gpt-4o", "gpt-4o-mini"])
        if self.config.get("anthropic_api_key"):
            self._available_models.extend(["claude-3-5-sonnet"])
        
        self._last_discovery = now
        logger.info(f"Available models: {self._available_models}")
    
    @property
    def active_model(self) -> str:
        return self.config.get("active_model", "llama3:8b")
    
    @active_model.setter
    def active_model(self, model: str):
        if model not in self._available_models:
            self._refresh_models(force=True)
            if model not in self._available_models:
                raise ValueError(f"Model '{model}' not available. Available: {self._available_models}")
        self.config.set("active_model", model)
        logger.info(f"Active model set to: {model}")
    
    def get_capabilities(self, model: str = None) -> ModelCapabilities:
        """Get capabilities for a model"""
        model = model or self.active_model
        # Try exact match first
        if model in MODEL_PROFILES:
            return MODEL_PROFILES[model]
        # Try base name (without tag)
        base_name = model.split(":")[0]
        for profile_name, caps in MODEL_PROFILES.items():
            if profile_name.startswith(base_name):
                return caps
        # Return defaults
        return ModelCapabilities()
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with their capabilities"""
        self._refresh_models()
        result = []
        for model in self._available_models:
            caps = self.get_capabilities(model)
            result.append({
                "name": model,
                "active": model == self.active_model,
                "context_window": caps.context_window,
                "specialized_for": caps.specialized_for,
                "cost_tier": caps.cost_tier
            })
        return result
    
    def generate(self,
                 prompt: str,
                 system: str = None,
                 context: str = None,
                 model: str = None,
                 temperature: float = None,
                 max_tokens: int = None,
                 stream: bool = False,
                 request_id: str = None) -> str | Iterator[str]:
        """
        Generate response - model-agnostic interface.
        
        Args:
            prompt: User prompt
            system: System prompt override (defaults to ROXY identity)
            context: RAG context to inject
            model: Override active model for this request
            temperature: Generation temperature
            max_tokens: Max tokens to generate
            stream: Return streaming iterator
            request_id: Request ID for logging
        
        Returns:
            Generated text or streaming iterator
        """
        model = model or self.active_model
        system = system or self.SYSTEM_PROMPT
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)
        max_tokens = max_tokens or self.config.get("max_tokens", 2048)
        
        # Build full prompt with context
        full_prompt = self._build_prompt(prompt, system, context)
        
        # Route to appropriate backend
        if model.startswith("gpt-"):
            return self._generate_openai(model, full_prompt, system, temperature, max_tokens, stream)
        elif model.startswith("claude-"):
            return self._generate_anthropic(model, full_prompt, system, temperature, max_tokens, stream)
        else:
            return self._generate_ollama(model, full_prompt, temperature, max_tokens, stream, request_id)
    
    def _build_prompt(self, prompt: str, system: str, context: str = None) -> str:
        """Build unified prompt format"""
        parts = []
        if system:
            parts.append(f"<system>\n{system}\n</system>\n")
        if context:
            parts.append(f"<context>\n{context}\n</context>\n")
        parts.append(f"<user>\n{prompt}\n</user>\n")
        parts.append("<assistant>")
        return "".join(parts)
    
    def _generate_ollama(self,
                         model: str,
                         prompt: str,
                         temperature: float,
                         max_tokens: int,
                         stream: bool,
                         request_id: str = None) -> str | Iterator[str]:
        """Generate via Ollama"""
        url = f"{self.config.get('ollama_url')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            if stream:
                return self._stream_ollama(url, payload, request_id)
            else:
                resp = requests.post(url, json=payload, timeout=120)
                if resp.status_code == 200:
                    return resp.json().get("response", "").strip()
                else:
                    raise Exception(f"Ollama error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    def _stream_ollama(self, url: str, payload: dict, request_id: str = None) -> Iterator[str]:
        """Stream from Ollama"""
        try:
            resp = requests.post(url, json=payload, stream=True, timeout=120)
            for line in resp.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise
    
    def _generate_openai(self,
                         model: str,
                         prompt: str,
                         system: str,
                         temperature: float,
                         max_tokens: int,
                         stream: bool) -> str | Iterator[str]:
        """Generate via OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.config.get("openai_api_key"))
            
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            
            if stream:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except ImportError:
            raise Exception("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def _generate_anthropic(self,
                            model: str,
                            prompt: str,
                            system: str,
                            temperature: float,
                            max_tokens: int,
                            stream: bool) -> str | Iterator[str]:
        """Generate via Anthropic API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.config.get("anthropic_api_key"))
            
            if stream:
                with client.messages.stream(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        yield text
            else:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
        except ImportError:
            raise Exception("Anthropic package not installed. Run: pip install anthropic")
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
    
    def select_best_model(self, task_type: str = "general") -> str:
        """Auto-select best available model for task type"""
        preferences = self.config.get("model_preferences", {})
        preferred = preferences.get(task_type, [])
        
        for model in preferred:
            if model in self._available_models:
                return model
        
        # Fallback
        if self._available_models:
            return self._available_models[0]
        return self.config.get("fallback_model", "llama3:8b")


# Global provider instance
_provider: Optional[ModelProvider] = None


def get_provider() -> ModelProvider:
    """Get global model provider instance"""
    global _provider
    if _provider is None:
        _provider = ModelProvider()
    return _provider


def set_active_model(model: str):
    """Convenience function to swap active model"""
    get_provider().active_model = model


def list_models() -> List[Dict[str, Any]]:
    """Convenience function to list available models"""
    return get_provider().list_models()


def generate(prompt: str, **kwargs) -> str:
    """Convenience function to generate with active model"""
    return get_provider().generate(prompt, **kwargs)

#!/usr/bin/env python3
"""
LLM Router - Routes tasks to appropriate models based on task type
Code tasks → code-specialized models
General tasks → general models
"""
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("roxy.llm_router")

# Model configuration
CODE_MODELS = ["llama3:8b", "codellama:7b", "deepseek-coder:6.7b"]
GENERAL_MODELS = ["llama3:8b", "mistral:7b", "llama2:7b"]
FALLBACK_MODEL = "llama3:8b"


class LLMRouter:
    """Routes LLM requests to appropriate models"""
    
    def __init__(self):
        self.available_models = self._discover_models()
        self.code_model = self._select_model(CODE_MODELS)
        self.general_model = self._select_model(GENERAL_MODELS)
        logger.info(f"LLM Router initialized - Code: {self.code_model}, General: {self.general_model}")
    
    def _discover_models(self) -> list:
        """Discover available Ollama models"""
        try:
            resp = requests.get("http://127.0.0.1:11435/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                logger.debug(f"Discovered {len(models)} models: {models}")
                return models
        except Exception as e:
            logger.debug(f"Model discovery failed: {e}")
        
        return []
    
    def _select_model(self, preferred_models: list) -> str:
        """Select first available model from preferred list"""
        for model in preferred_models:
            if model in self.available_models:
                return model
        
        # Fallback to first available or default
        if self.available_models:
            return self.available_models[0]
        
        return FALLBACK_MODEL
    
    def _classify_task(self, query: str, context: str = None) -> str:
        """Classify task as code or general"""
        query_lower = query.lower()
        context_lower = (context or "").lower()
        
        # Code task indicators
        code_indicators = [
            "code", "function", "class", "method", "variable",
            "import", "def ", "const ", "let ", "var ",
            "python", "javascript", "typescript", "react",
            "component", "api", "endpoint", "route",
            "bug", "error", "fix", "debug", "refactor"
        ]
        
        # Check query
        if any(indicator in query_lower for indicator in code_indicators):
            return "code"
        
        # Check context
        if context and any(indicator in context_lower for indicator in code_indicators):
            return "code"
        
        return "general"
    
    def route_and_generate(self,
                          prompt: str,
                          query: str = None,
                          context: str = None,
                          task_type: str = None,
                          **kwargs) -> str:
        """Route to appropriate model and generate response"""
        # Determine task type
        if not task_type:
            task_type = self._classify_task(query or prompt, context)
        
        # Select model
        if task_type == "code":
            model = self.code_model
            logger.debug(f"Routing to code model: {model}")
        else:
            model = self.general_model
            logger.debug(f"Routing to general model: {model}")
        
        # Generate with selected model
        try:
            return self._generate_with_model(model, prompt, **kwargs)
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}, trying fallback")
            # Fallback to default model
            return self._generate_with_model(FALLBACK_MODEL, prompt, **kwargs)
    
    def _generate_with_model(self, model: str, prompt: str, **kwargs) -> str:
        """Generate response with specific model"""
        try:
            resp = requests.post(
                "http://127.0.0.1:11435/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": kwargs.get("stream", False),
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "num_predict": kwargs.get("num_predict", 300)
                    }
                },
                timeout=kwargs.get("timeout", 60)
            )
            
            if resp.status_code == 200:
                if kwargs.get("stream", False):
                    # Handle streaming
                    return resp.text
                else:
                    return resp.json().get("response", "").strip()
            else:
                raise Exception(f"Model {model} returned status {resp.status_code}")
        except Exception as e:
            logger.error(f"Generation with {model} failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        return {
            "code_model": self.code_model,
            "general_model": self.general_model,
            "available_models": self.available_models,
            "fallback_model": FALLBACK_MODEL
        }


# Global router instance
_router_instance = None


def get_llm_router() -> LLMRouter:
    """Get global LLM router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance













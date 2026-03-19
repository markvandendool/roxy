#!/usr/bin/env python3
"""
Reflection and Verifier Module for ROXY
Implements Self-Refine pattern for hallucination prevention and confidence boosting

Based on: Self-Refine (Madaan et al., 2023) + Reflexion (Shinn et al., 2023)
"""
import re
import logging
import os
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("roxy.reflection")

REFLECTION_PROMPT = """You are a fact-checker for ROXY, the MindSong AI assistant. Your job is to verify the response below.

Check ONLY these aspects:
1. FACTUAL ACCURACY: Are the claims verifiable? Mark [VERIFIED] or [UNVERIFIED]
2. SYSTEM STATE: Any claims about files, services, processes must be marked [UNVERIFIED] unless from TruthPacket
3. USER PREFERENCES: Any claims about user preferences must be marked [UNVERIFIED] unless from memory
4. PRODUCTION STATE: Any claims about SkyBeam renders, StackKraft campaigns must be marked [UNVERIFIED] unless confirmed

Original question: {query}
Response to verify: {response}

Provide a confidence score 0.0-1.0 and flag any uncertain claims.
Format: CONFIDENCE:{score} | FLAGS:{comma-separated flags or NONE}"""

VERIFIER_MODEL = os.getenv("ROXY_VERIFIER_MODEL", "qwen2.5-coder:14b-instruct")
VERIFIER_URL = os.getenv("ROXY_VERIFIER_URL", "http://127.0.0.1:11435")


class ReflectionVerifier:
    """
    Implements reflection loop for low-confidence responses.
    Uses a lightweight verifier to check responses before returning to user.
    """
    
    def __init__(self, enabled: bool = True, confidence_threshold: float = 0.7):
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self._verifier_url = VERIFIER_URL
    
    def verify_response(
        self, 
        query: str, 
        response: str,
        memory_context: str = "",
        truth_packet: str = ""
    ) -> Dict[str, Any]:
        """
        Verify a response and return confidence metrics.
        
        Returns:
            {
                "confidence": float,
                "flags": List[str],
                "needs_reflection": bool,
                "verified_claims": List[str],
                "unverified_claims": List[str]
            }
        """
        if not self.enabled or not response:
            return {
                "confidence": 1.0,
                "flags": [],
                "needs_reflection": False,
                "verified_claims": [],
                "unverified_claims": []
            }
        
        # Quick heuristics for obvious low-confidence responses
        quick_check = self._quick_confidence_check(query, response, memory_context, truth_packet)
        if quick_check["confidence"] >= self.confidence_threshold:
            return quick_check
        
        # Full LLM-based verification for uncertain responses
        return self._llm_verify(query, response, memory_context, truth_packet)
    
    def _quick_confidence_check(self, query: str, response: str, memory_context: str = "", truth_packet: str = "") -> Dict[str, Any]:
        """Fast heuristics-based confidence check."""
        flags = []
        confidence = 1.0
        
        response_lower = response.lower()
        query_lower = query.lower()
        
        # Check for hedging language (slight confidence boost - honest)
        hedging = ["i think", "probably", "maybe", "might be", "could be", "not sure"]
        if any(h in response_lower for h in hedging):
            confidence -= 0.1
        
        # Check for hallucination indicators
        hallucination_indicators = [
            "i remember", "in the past", "previously", "last time"
        ]
        if any(hi in response_lower for hi in hallucination_indicators):
            if not memory_context:
                flags.append("MEMORY_CLAIM_WITHOUT_CONTEXT")
                confidence -= 0.3
        
        # Check for file/service claims without verification
        system_claims = [
            "file exists", "directory exists", "service is running",
            "process is", "the render is", "the queue shows"
        ]
        if any(sc in response_lower for sc in system_claims):
            if not truth_packet:
                flags.append("SYSTEM_CLAIM_WITHOUT_VERIFICATION")
                confidence -= 0.2
        
        # Check for production claims
        production_claims = [
            "skybeam is", "stackkraft shows", "shotcaller indicates",
            "the render is", "monetization is", "mqqc detected"
        ]
        if any(pc in response_lower for pc in production_claims):
            flags.append("PRODUCTION_CLAIM")
            confidence -= 0.15
        
        # Check for "I don't know" responses (high confidence in uncertainty)
        if "i don't know" in response_lower or "i'm not sure" in response_lower:
            return {
                "confidence": 0.95,  # High confidence in not knowing
                "flags": [],
                "needs_reflection": False,
                "verified_claims": [],
                "unverified_claims": []
            }
        
        # Check for "based on memory" responses
        if "memory" in response_lower or "remember" in response_lower:
            if memory_context:
                confidence += 0.1  # Boost when memory is available
        
        return {
            "confidence": max(0.0, min(confidence, 1.0)),
            "flags": flags,
            "needs_reflection": confidence < self.confidence_threshold,
            "verified_claims": [],
            "unverified_claims": []
        }
    
    def _llm_verify(
        self, 
        query: str, 
        response: str,
        memory_context: str = "",
        truth_packet: str = ""
    ) -> Dict[str, Any]:
        """Use LLM to verify response claims."""
        try:
            import requests
            
            prompt = REFLECTION_PROMPT.format(
                query=query[:500],
                response=response[:1000]
            )
            
            resp = requests.post(
                f"{self._verifier_url}/api/generate",
                json={
                    "model": VERIFIER_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 200}
                },
                timeout=15
            )
            
            if resp.status_code == 200:
                result = resp.json().get("response", "")
                return self._parse_verification(result, response)
            
        except Exception as e:
            logger.debug(f"LLM verification failed: {e}")
        
        # Fallback to quick check
        return self._quick_confidence_check(query, response)
    
    def _parse_verification(self, verifier_output: str, original_response: str) -> Dict[str, Any]:
        """Parse LLM verification output."""
        confidence = 0.8  # Default
        flags = []
        
        # Parse confidence
        conf_match = re.search(r"CONFIDENCE:\s*([0-9.]+)", verifier_output, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
            except ValueError:
                pass
        
        # Parse flags
        flags_match = re.search(r"FLAGS:\s*([^\n]+)", verifier_output, re.IGNORECASE)
        if flags_match:
            flags_str = flags_match.group(1).strip()
            if flags_str.upper() != "NONE":
                flags = [f.strip() for f in flags_str.split(",") if f.strip()]
        
        # Check for unverified claims
        unverified = []
        if "[UNVERIFIED]" in verifier_output.upper():
            unverified_pattern = r"\[UNVERIFIED\]\s*([^\[\]]+)"
            for match in re.finditer(unverified_pattern, verifier_output):
                claim = match.group(1).strip()
                if claim:
                    unverified.append(claim)
        
        return {
            "confidence": max(0.0, min(confidence, 1.0)),
            "flags": flags,
            "needs_reflection": confidence < self.confidence_threshold,
            "verified_claims": [],
            "unverified_claims": unverified
        }
    
    def add_confidence_warning(self, verification: Dict[str, Any], response: str) -> str:
        """Add confidence warning to response if needed."""
        if verification["confidence"] >= self.confidence_threshold:
            return response
        
        warning_parts = []
        
        if verification["unverified_claims"]:
            warning_parts.append(
                f"⚠️ Note: The following claims could not be verified: {', '.join(verification['unverified_claims'][:2])}"
            )
        
        if verification["flags"]:
            flag_labels = {
                "MEMORY_CLAIM_WITHOUT_CONTEXT": "Memory references unverified",
                "SYSTEM_CLAIM_WITHOUT_VERIFICATION": "System state unverified",
                "PRODUCTION_CLAIM": "Production status unconfirmed"
            }
            flagged = [flag_labels.get(f, f) for f in verification["flags"]]
            warning_parts.append(f"⚠️ Confidence: {verification['confidence']:.0%} - {', '.join(flagged)}")
        
        if warning_parts:
            return response + "\n\n" + "\n".join(warning_parts)
        
        return response


# Global verifier instance
_verifier = None


def get_reflection_verifier() -> ReflectionVerifier:
    """Get or create global reflection verifier instance."""
    global _verifier
    if _verifier is None:
        enabled = os.getenv("ROXY_ENABLE_REFLECTION", "1").lower() in ("1", "true", "yes")
        threshold = float(os.getenv("ROXY_REFLECTION_THRESHOLD", "0.7"))
        _verifier = ReflectionVerifier(enabled=enabled, confidence_threshold=threshold)
    return _verifier

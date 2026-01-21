#!/usr/bin/env python3
"""
Confidence Scorer - Calculates confidence scores for responses
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("roxy.validation.confidence_scorer")


class ConfidenceScorer:
    """Calculates confidence scores for responses"""
    
    def calculate_confidence(self, 
                           fact_check_result: Dict[str, Any],
                           source_verify_result: Dict[str, Any],
                           response_length: int = 0,
                           has_source: bool = False) -> float:
        """Calculate overall confidence score (0.0 to 1.0)"""
        confidence = 1.0
        
        # Fact check confidence
        if "confidence" in fact_check_result:
            confidence *= fact_check_result["confidence"]
        elif not fact_check_result.get("overall_valid", True):
            confidence *= 0.5
        
        # Source verification confidence
        if not source_verify_result.get("verified", True):
            confidence *= 0.7
        
        # Response quality indicators
        if response_length < 10:
            confidence *= 0.6  # Very short responses are less reliable
        elif response_length > 1000:
            confidence *= 0.9  # Long responses might be verbose
        
        # Source attribution
        if has_source:
            confidence *= 1.1  # Boost for source attribution
            confidence = min(confidence, 1.0)  # Cap at 1.0
        else:
            confidence *= 0.9  # Penalty for no source
        
        return round(confidence, 2)
    
    def get_confidence_level(self, score: float) -> str:
        """Get human-readable confidence level"""
        if score >= 0.9:
            return "high"
        elif score >= 0.7:
            return "medium"
        elif score >= 0.5:
            return "low"
        else:
            return "very_low"
    
    def should_retry(self, score: float) -> bool:
        """Determine if response should be retried due to low confidence"""
        return score < 0.7
















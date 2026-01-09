#!/usr/bin/env python3
"""
ROXY Quality Checker - Validates response quality and adds confidence scores
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.quality')

class QualityChecker:
    """Checks response quality and assigns confidence scores"""
    
    def __init__(self):
        self.min_length = 20
        self.max_length = 10000
        self.quality_threshold = 0.7
    
    def check_quality(self, response: str, source: str = "unknown", 
                     context: Dict = None) -> Dict[str, Any]:
        """
        Check response quality and assign confidence score
        
        Returns:
            {
                'quality_score': float (0-1),
                'confidence': str ('high'|'medium'|'low'),
                'issues': List[str],
                'recommendations': List[str]
            }
        """
        issues = []
        quality_score = 1.0
        
        # Check 1: Length validation
        if len(response.strip()) < self.min_length:
            issues.append(f"Response too short ({len(response)} chars)")
            quality_score -= 0.3
        elif len(response.strip()) > self.max_length:
            issues.append(f"Response too long ({len(response)} chars)")
            quality_score -= 0.1
        
        # Check 2: Source quality
        source_scores = {
            'filesystem': 1.0,  # Real file operations - highest confidence
            'rag': 0.9,  # RAG with indexed data - high confidence
            'llm': 0.7,  # LLM generation - medium confidence
            'pattern': 0.5,  # Pattern matching - low confidence
            'fallback': 0.3,  # Fallback - very low confidence
            'unknown': 0.5
        }
        
        source_quality = source_scores.get(source.lower(), 0.5)
        if source_quality < 0.7:
            issues.append(f"Low confidence source: {source}")
        
        quality_score = (quality_score + source_quality) / 2
        
        # Check 3: Content quality indicators
        quality_indicators = {
            'has_source_attribution': 0.1,
            'has_timestamp': 0.05,
            'has_file_paths': 0.1 if 'filesystem' in source.lower() else 0,
            'has_context': 0.05,
            'not_generic': 0.1
        }
        
        if '📌 Source:' in response or 'Source:' in response:
            quality_score += quality_indicators['has_source_attribution']
        else:
            issues.append("Missing source attribution")
        
        if any(char.isdigit() for char in response.split()[0] if response.split()):
            # Might have timestamp
            pass
        
        if any(ext in response for ext in ['.tsx', '.ts', '.jsx', '.js', '.py', '.md']):
            quality_score += quality_indicators['has_file_paths']
        
        # Check for generic responses
        generic_phrases = [
            "I understand you said",
            "I'm processing your request",
            "Tool A", "Tool B", "Tool C"
        ]
        
        if any(phrase in response for phrase in generic_phrases):
            issues.append("Response contains generic phrases")
            quality_score -= 0.2
        
        # Determine confidence level
        if quality_score >= 0.8:
            confidence = 'high'
        elif quality_score >= 0.6:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Generate recommendations
        recommendations = []
        if quality_score < self.quality_threshold:
            if 'filesystem' not in source.lower() and 'list' in str(context or {}).lower():
                recommendations.append("Use filesystem operations for file listings")
            if not any('Source:' in response for _ in [1]):
                recommendations.append("Add source attribution")
            if len(response.strip()) < 50:
                recommendations.append("Provide more detailed response")
        
        return {
            'quality_score': min(1.0, max(0.0, quality_score)),
            'confidence': confidence,
            'issues': issues,
            'recommendations': recommendations,
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
    
    def enhance_response(self, response: str, quality_check: Dict[str, Any]) -> str:
        """Enhance response with quality metadata"""
        enhanced = response
        
        # Add confidence indicator
        confidence_emoji = {
            'high': '✅',
            'medium': '⚠️',
            'low': '❌'
        }
        
        emoji = confidence_emoji.get(quality_check['confidence'], '⚠️')
        confidence_text = f"{emoji} Confidence: {quality_check['confidence'].upper()}"
        
        # Add quality score if low
        if quality_check['quality_score'] < self.quality_threshold:
            enhanced += f"\n\n{confidence_text} (Quality: {quality_check['quality_score']:.1%})"
        
        # Add recommendations if any
        if quality_check['recommendations']:
            enhanced += f"\n💡 Recommendations: {', '.join(quality_check['recommendations'])}"
        
        return enhanced

# Global quality checker instance
_quality_checker: Optional[QualityChecker] = None

def get_quality_checker() -> QualityChecker:
    """Get or create quality checker instance"""
    global _quality_checker
    if _quality_checker is None:
        _quality_checker = QualityChecker()
    return _quality_checker














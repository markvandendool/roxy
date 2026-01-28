#!/usr/bin/env python3
"""
User Feedback Loop - Collects and learns from user feedback
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("roxy.feedback")

ROXY_DIR = Path.home() / ".roxy"
FEEDBACK_DIR = ROXY_DIR / "data" / "feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


class FeedbackCollector:
    """Collects and stores user feedback"""
    
    def __init__(self):
        self.feedback_file = FEEDBACK_DIR / f"feedback_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.feedback_history: List[Dict[str, Any]] = []
        self._load_feedback()
    
    def _load_feedback(self):
        """Load existing feedback"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file) as f:
                    for line in f:
                        if line.strip():
                            self.feedback_history.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to load feedback: {e}")
    
    def record_feedback(self,
                       query: str,
                       response: str,
                       feedback_type: str,  # "thumbs_up", "thumbs_down", "correction"
                       correction: str = None,
                       metadata: Dict[str, Any] = None):
        """Record user feedback"""
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],
            "response": response[:500],
            "feedback_type": feedback_type,
            "correction": correction,
            "metadata": metadata or {}
        }
        
        self.feedback_history.append(feedback_entry)
        
        # Save to file
        try:
            with open(self.feedback_file, 'a') as f:
                f.write(json.dumps(feedback_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
        
        logger.info(f"Feedback recorded: {feedback_type} for query '{query[:50]}'")
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        if not self.feedback_history:
            return {
                "total": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "corrections": 0
            }
        
        stats = {
            "total": len(self.feedback_history),
            "thumbs_up": sum(1 for f in self.feedback_history if f.get("feedback_type") == "thumbs_up"),
            "thumbs_down": sum(1 for f in self.feedback_history if f.get("feedback_type") == "thumbs_down"),
            "corrections": sum(1 for f in self.feedback_history if f.get("feedback_type") == "correction")
        }
        
        stats["satisfaction_rate"] = (
            stats["thumbs_up"] / stats["total"] if stats["total"] > 0 else 0.0
        )
        
        return stats
    
    def get_recent_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent feedback entries"""
        return self.feedback_history[-limit:]
    
    def learn_from_feedback(self) -> Dict[str, Any]:
        """Analyze feedback to identify patterns"""
        if not self.feedback_history:
            return {"patterns": [], "recommendations": []}
        
        # Simple pattern analysis
        negative_feedback = [f for f in self.feedback_history if f.get("feedback_type") == "thumbs_down"]
        corrections = [f for f in self.feedback_history if f.get("feedback_type") == "correction"]
        
        patterns = []
        if negative_feedback:
            patterns.append({
                "type": "negative_feedback",
                "count": len(negative_feedback),
                "sample_queries": [f["query"][:50] for f in negative_feedback[:3]]
            })
        
        if corrections:
            patterns.append({
                "type": "corrections",
                "count": len(corrections),
                "sample_corrections": [f["correction"][:100] for f in corrections[:3] if f.get("correction")]
            })
        
        recommendations = []
        if len(negative_feedback) > len(self.feedback_history) * 0.3:
            recommendations.append("High negative feedback rate - consider improving response quality")
        
        return {
            "patterns": patterns,
            "recommendations": recommendations
        }


# Global feedback collector
_feedback_collector = None


def get_feedback_collector() -> FeedbackCollector:
    """Get global feedback collector"""
    global _feedback_collector
    if _feedback_collector is None:
        _feedback_collector = FeedbackCollector()
    return _feedback_collector















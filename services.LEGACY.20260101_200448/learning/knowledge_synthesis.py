#!/usr/bin/env python3
"""
ROXY Knowledge Synthesis - Combine knowledge from multiple sources
"""
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.learning.knowledge_synthesis')

class KnowledgeSynthesizer:
    """Synthesize knowledge from multiple sources"""
    
    def synthesize(self, knowledge_sources: List[Dict]) -> Dict:
        """Combine knowledge from multiple sources"""
        synthesized = {
            'facts': [],
            'patterns': [],
            'insights': []
        }
        
        for source in knowledge_sources:
            if 'facts' in source:
                synthesized['facts'].extend(source['facts'])
            if 'patterns' in source:
                synthesized['patterns'].extend(source['patterns'])
            if 'insights' in source:
                synthesized['insights'].extend(source['insights'])
        
        # Deduplicate
        synthesized['facts'] = list(set(synthesized['facts']))
        
        return synthesized

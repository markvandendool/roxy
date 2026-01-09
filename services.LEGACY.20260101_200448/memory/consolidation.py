#!/usr/bin/env python3
"""
ROXY Memory Consolidation - Automatic memory optimization and deduplication
"""
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.memory.consolidation')

class MemoryConsolidator:
    """Consolidate and optimize memories"""
    
    def __init__(self):
        self.consolidation_interval = timedelta(hours=24)
        self.last_consolidation = None
    
    def consolidate_facts(self, facts: List[Dict]) -> List[Dict]:
        """Deduplicate and merge similar facts"""
        # Group by category
        by_category = {}
        for fact in facts:
            category = fact.get('category', 'general')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(fact)
        
        # Deduplicate within categories
        consolidated = []
        for category, category_facts in by_category.items():
            # Simple deduplication by fact text
            seen = set()
            for fact in category_facts:
                fact_text = fact.get('fact', '').lower().strip()
                if fact_text not in seen:
                    seen.add(fact_text)
                    consolidated.append(fact)
        
        logger.info(f"Consolidated {len(facts)} facts to {len(consolidated)}")
        return consolidated
    
    def should_consolidate(self) -> bool:
        """Check if consolidation is needed"""
        if self.last_consolidation is None:
            return True
        
        return datetime.now() - self.last_consolidation > self.consolidation_interval
    
    def consolidate(self, memory):
        """Perform full memory consolidation"""
        if not self.should_consolidate():
            return
        
        logger.info("Starting memory consolidation...")
        
        # Get all facts
        all_facts = memory.recall_facts(limit=10000)
        
        # Consolidate
        consolidated = self.consolidate_facts(all_facts)
        
        # Update memory (would need to implement update method)
        self.last_consolidation = datetime.now()
        logger.info("Memory consolidation complete")











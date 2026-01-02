#!/usr/bin/env python3
"""
JARVIS Core - Permanent, Learning, Resident AI
The brain that grows, learns, and remembers everything
"""
import asyncio
import json
import logging
import signal
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import sqlite3

sys.path.insert(0, '/opt/roxy/services')
sys.path.insert(0, '/opt/roxy/voice')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [JARVIS] %(levelname)s: %(message)s'
)
logger = logging.getLogger('jarvis.core')

# Persistent memory database
MEMORY_DB = Path('/opt/roxy/data/jarvis_memory.db')
MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)

class JarvisMemory:
    """Persistent memory that grows over time"""
    
    def __init__(self, db_path: str = str(MEMORY_DB)):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize memory database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                jarvis_response TEXT NOT NULL,
                context TEXT,
                learned_facts TEXT,
                embedding_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                fact TEXT NOT NULL,
                category TEXT,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                verified INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Memory database initialized: {self.db_path}")
    
    def remember_conversation(self, user_input: str, response: str, 
                             context: Dict = None, learned: List[str] = None):
        """Store a conversation for learning"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO conversations (timestamp, user_input, jarvis_response, context, learned_facts)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            user_input,
            response,
            json.dumps(context or {}),
            json.dumps(learned or [])
        ))
        conn.commit()
        conn.close()
    
    def learn_fact(self, fact: str, category: str = "general", 
                   source: str = "conversation", confidence: float = 1.0):
        """Learn and store a new fact"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO learned_facts (timestamp, fact, category, source, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            fact,
            category,
            source,
            confidence
        ))
        conn.commit()
        conn.close()
        logger.info(f"Learned: {fact[:50]}...")
    
    def recall_facts(self, category: str = None, limit: int = 10) -> List[Dict]:
        """Recall learned facts"""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM learned_facts"
        params = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(query, params)
        facts = []
        for row in cursor.fetchall():
            facts.append({
                'id': row[0],
                'timestamp': row[1],
                'fact': row[2],
                'category': row[3],
                'source': row[4],
                'confidence': row[5],
                'verified': row[6]
            })
        conn.close()
        return facts
    
    def get_conversation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT timestamp, user_input, jarvis_response, context
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'timestamp': row[0],
                'user_input': row[1],
                'response': row[2],
                'context': json.loads(row[3] or '{}')
            })
        conn.close()
        return list(reversed(history))  # Oldest first
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        conn = sqlite3.connect(self.db_path)
        
        conversations = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        facts = conn.execute("SELECT COUNT(*) FROM learned_facts").fetchone()[0]
        preferences = conn.execute("SELECT COUNT(*) FROM user_preferences").fetchone()[0]
        
        conn.close()
        
        return {
            'conversations': conversations,
            'learned_facts': facts,
            'preferences': preferences,
            'memory_db_size': MEMORY_DB.stat().st_size if MEMORY_DB.exists() else 0
        }


class JarvisCore:
    """The permanent, learning, resident AI brain"""
    
    def __init__(self):
        self.running = False
        self.start_time = None
        self.memory = JarvisMemory()
        self.services = {}
        self.learning_enabled = True
        self.interaction_count = 0
        
    async def start(self):
        """Start JARVIS - the permanent resident AI"""
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("=" * 70)
        logger.info("🤖 JARVIS - PERMANENT RESIDENT AI STARTING")
        logger.info("=" * 70)
        
        # Initialize core services
        await self._init_event_bus()
        await self._init_knowledge_index()
        await self._init_learning_loop()
        
        # Load previous state
        await self._load_state()
        
        # Start learning from past conversations
        await self._review_past_learning()
        
        # Publish startup (non-blocking)
        if self.services.get('eventbus'):
            try:
                await self.services['eventbus'].publish(
                    'jarvis.started',
                    {
                        'version': '1.0.0',
                        'start_time': self.start_time.isoformat(),
                        'memory_stats': self.memory.get_stats()
                    }
                )
            except Exception as e:
                logger.warning(f"Could not publish startup event: {e}")
        
        logger.info("-" * 70)
        logger.info("✅ JARVIS IS ALIVE AND LEARNING")
        logger.info(f"   Memory: {self.memory.get_stats()['conversations']} conversations")
        logger.info(f"   Learned: {self.memory.get_stats()['learned_facts']} facts")
        logger.info(f"   Uptime: {self.start_time.isoformat()}")
        logger.info("-" * 70)
        
        # Main loop - JARVIS never sleeps
        last_learning_check = 0
        while self.running:
            await asyncio.sleep(1)
            # Periodic learning and maintenance (every 100 interactions or every hour)
            if self.interaction_count > 0 and self.interaction_count % 100 == 0 and self.interaction_count != last_learning_check:
                await self._periodic_learning()
                last_learning_check = self.interaction_count
    
    async def stop(self):
        """Graceful shutdown - save everything"""
        logger.info("JARVIS SHUTTING DOWN (saving all memories)...")
        self.running = False
        
        # Save current state
        await self._save_state()
        
        # Publish shutdown (non-blocking)
        if self.services.get('eventbus'):
            try:
                await self.services['eventbus'].publish(
                    'jarvis.stopped',
                    {
                        'timestamp': datetime.now().isoformat(),
                        'final_stats': self.memory.get_stats()
                    }
                )
            except Exception as e:
                logger.warning(f"Could not publish shutdown event: {e}")
            try:
                await self.services['eventbus'].disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting event bus: {e}")
        
        logger.info("✅ JARVIS SHUTDOWN COMPLETE (all memories saved)")
    
    async def process_interaction(self, user_input: str, context: Dict = None) -> str:
        """Process a user interaction and learn from it"""
        self.interaction_count += 1
        
        # Search memory for relevant past conversations
        history = self.memory.get_conversation_history(limit=5)
        relevant_facts = self.memory.recall_facts(limit=10)
        
        # Generate response (this would integrate with LLM)
        response = await self._generate_response(user_input, history, relevant_facts, context)
        
        # Learn from this interaction
        if self.learning_enabled:
            learned = await self._extract_learning(user_input, response, context)
            for fact in learned:
                self.memory.learn_fact(fact, category="conversation")
        
        # Remember this conversation
        self.memory.remember_conversation(
            user_input, response, context, 
            learned if self.learning_enabled else []
        )
        
        return response
    
    async def _generate_response(self, user_input: str, history: List[Dict], 
                                facts: List[Dict], context: Dict) -> str:
        """Generate response using LLM with memory context"""
        try:
            # Import LLM service
            from llm_service import get_llm_service
            
            llm_service = get_llm_service()
            
            if llm_service.is_available():
                # Use LLM for intelligent response
                response = await llm_service.generate_response(
                    user_input=user_input,
                    context=context,
                    history=history,
                    facts=facts
                )
                return response
            else:
                # Fallback to simple response
                stats = self.memory.get_stats()
                return f"I understand. I've had {stats['conversations']} conversations and learned {stats['learned_facts']} facts. How can I help? (LLM service not available)"
        except Exception as e:
            logger.warning(f"LLM service error: {e}, using fallback")
            # Fallback response
            stats = self.memory.get_stats()
            return f"I understand. I've had {stats['conversations']} conversations and learned {stats['learned_facts']} facts. How can I help?"
    
    async def _extract_learning(self, user_input: str, response: str, 
                                context: Dict) -> List[str]:
        """Extract learnable facts from interaction"""
        learned = []
        # Simple extraction - would use NLP/LLM in production
        if "my name is" in user_input.lower():
            name = user_input.lower().split("my name is")[-1].strip()
            learned.append(f"User's name is {name}")
        if "i like" in user_input.lower() or "i prefer" in user_input.lower():
            preference = user_input.lower().split("i like")[-1].split("i prefer")[-1].strip()
            learned.append(f"User preference: {preference}")
        return learned
    
    async def _init_event_bus(self):
        """Initialize NATS event bus"""
        try:
            from eventbus import RoxyEventBus
            bus = RoxyEventBus()
            await bus.connect()
            self.services['eventbus'] = bus
            
            # Subscribe to all events for learning
            await bus.subscribe("roxy.>", self._learn_from_event)
            logger.info("✅ Event bus connected (learning from events")
        except Exception as e:
            logger.warning(f"⚠️ Event bus unavailable: {e}")
    
    async def _init_knowledge_index(self):
        """Initialize ChromaDB for semantic search"""
        try:
            from knowledge import KnowledgeIndex
            index = KnowledgeIndex()
            self.services['knowledge'] = index
            stats = index.get_stats()
            total_docs = sum(s['count'] for s in stats.values())
            logger.info(f"✅ Knowledge index connected ({total_docs} documents)")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge index unavailable: {e}")
    
    async def _init_learning_loop(self):
        """Initialize continuous learning processes"""
        logger.info("✅ Learning loop initialized")
    
    async def _learn_from_event(self, event: Dict):
        """Learn from system events"""
        if self.learning_enabled:
            # Extract patterns from events
            subject = event.get('subject', '')
            data = event.get('data', {})
            # Learn system patterns, user behavior, etc.
            pass
    
    async def _review_past_learning(self):
        """Review and consolidate past learning on startup"""
        stats = self.memory.get_stats()
        logger.info(f"📚 Reviewing {stats['learned_facts']} learned facts...")
        # Could use LLM to consolidate and verify facts
    
    async def _periodic_learning(self):
        """Periodic learning and memory consolidation"""
        logger.info("🧠 Periodic learning cycle...")
        # Consolidate memories, verify facts, update knowledge
    
    async def _load_state(self):
        """Load previous state"""
        # Load preferences, settings, etc.
        pass
    
    async def _save_state(self):
        """Save current state"""
        # Save preferences, settings, etc.
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get JARVIS status"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            'running': self.running,
            'uptime_seconds': uptime,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'interaction_count': self.interaction_count,
            'memory_stats': self.memory.get_stats(),
            'services': {name: 'active' for name in self.services.keys()}
        }


async def main():
    jarvis = JarvisCore()
    
    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(jarvis.stop()))
    
    try:
        await jarvis.start()
    except KeyboardInterrupt:
        await jarvis.stop()


if __name__ == "__main__":
    asyncio.run(main())


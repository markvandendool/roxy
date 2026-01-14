#!/usr/bin/env python3
"""
JARVIS Interface - Multiple ways to interact with the resident AI
Terminal, Voice, Web, API - all connected to the same learning brain
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, '/home/mark/.roxy/services')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('jarvis.interface')

class JarvisInterface:
    """Unified interface to JARVIS - the resident AI"""
    
    def __init__(self):
        self.jarvis_core = None
        self._connect_to_jarvis()
    
    def _connect_to_jarvis(self):
        """Connect to JARVIS core via event bus or direct"""
        # JARVIS runs as a service - we'll communicate via NATS or direct DB access
        try:
            # Check if service is running
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'jarvis.service'], 
                                  capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                logger.info("JARVIS service is running")
                self.jarvis_running = True
            else:
                logger.warning("JARVIS service not running")
                self.jarvis_running = False
        except Exception as e:
            logger.warning(f"Could not check JARVIS status: {e}")
            self.jarvis_running = False
    
    async def chat_terminal(self, user_input: str) -> str:
        """Terminal chat interface"""
        # For now, process directly and store in memory
        # In future, would send to running JARVIS service via NATS
        return await self._process_with_memory(user_input)
    
    async def chat_voice(self, transcript: str) -> str:
        """Voice interface"""
        return await self.chat_terminal(transcript)
    
    async def chat_web(self, user_input: str, session_id: str) -> Dict:
        """Web interface"""
        response = await self.chat_terminal(user_input)
        return {
            'response': response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
    
    async def chat_api(self, request: Dict) -> Dict:
        """REST API interface"""
        user_input = request.get('message', '')
        context = request.get('context', {})
        response = await self.chat_terminal(user_input)
        return {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _process_with_memory(self, user_input: str) -> str:
        """Process with memory access"""
        try:
            from jarvis_core import JarvisMemory
            memory = JarvisMemory()
            
            # Store this conversation
            response = await self._generate_response(user_input, memory)
            memory.remember_conversation(user_input, response)
            
            # Extract and learn facts
            learned = await self._extract_facts(user_input, response)
            for fact in learned:
                memory.learn_fact(fact, category="conversation")
            
            return response
        except Exception as e:
            logger.error(f"Error processing: {e}")
            return f"JARVIS: I heard '{user_input}'. (Processing with memory...)"
    
    async def _generate_response(self, user_input: str, memory) -> str:
        """Generate response using memory context"""
        # Get recent history
        history = memory.get_conversation_history(limit=3)
        facts = memory.recall_facts(limit=5)
        
        # Simple response generation (would use LLM in production)
        stats = memory.get_stats()
        
        # Check for specific queries
        if "remember" in user_input.lower() or "what do you know" in user_input.lower():
            if facts:
                return f"I remember {len(facts)} things. For example: {facts[0]['fact']}"
            else:
                return "I'm still learning! Tell me something about yourself."
        
        if "my name is" in user_input.lower():
            name = user_input.lower().split("my name is")[-1].strip()
            return f"Nice to meet you, {name}! I'll remember that."
        
        if "i like" in user_input.lower() or "i prefer" in user_input.lower():
            preference = user_input.lower().split("i like")[-1].split("i prefer")[-1].strip()
            return f"Got it! I'll remember you like {preference}."
        
        # Default response
        return f"I understand. I've had {stats['conversations']} conversations and learned {stats['learned_facts']} facts. How can I help you?"
    
    async def _extract_facts(self, user_input: str, response: str) -> List[str]:
        """Extract learnable facts"""
        facts = []
        if "my name is" in user_input.lower():
            name = user_input.lower().split("my name is")[-1].strip()
            facts.append(f"User's name is {name}")
        if "i like" in user_input.lower():
            preference = user_input.lower().split("i like")[-1].strip()
            facts.append(f"User likes {preference}")
        if "i prefer" in user_input.lower():
            preference = user_input.lower().split("i prefer")[-1].strip()
            facts.append(f"User prefers {preference}")
        return facts


# Terminal interface
async def terminal_chat():
    """Interactive terminal chat with JARVIS"""
    interface = JarvisInterface()
    
    print("=" * 70)
    print("🤖 JARVIS - Resident AI Assistant")
    print("=" * 70)
    print("Type 'exit' or 'quit' to end conversation")
    print("Type 'status' to see JARVIS status")
    print("Type 'memory' to see what JARVIS remembers")
    print("=" * 70)
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("JARVIS: Goodbye! I'll remember our conversation.")
                break
            
            if user_input.lower() == 'status':
                try:
                    import subprocess
                    result = subprocess.run(['systemctl', 'is-active', 'jarvis.service'], 
                                          capture_output=True, text=True)
                    status = result.stdout.strip()
                    print(f"JARVIS: Service status: {status}")
                    print(f"JARVIS: I'm running and learning!")
                except:
                    print("JARVIS: Status check unavailable")
                continue
            
            if user_input.lower() == 'memory':
                try:
                    from jarvis_core import JarvisMemory
                    memory = JarvisMemory()
                    stats = memory.get_stats()
                    facts = memory.recall_facts(limit=5)
                    print(f"JARVIS: Memory Statistics:")
                    print(f"  • Conversations: {stats['conversations']}")
                    print(f"  • Learned Facts: {stats['learned_facts']}")
                    print(f"  • Preferences: {stats['preferences']}")
                    if facts:
                        print(f"\nJARVIS: Recent things I've learned:")
                        for fact in facts[:3]:
                            print(f"  • {fact['fact']}")
                except Exception as e:
                    print(f"JARVIS: Error accessing memory: {e}")
                continue
            
            response = await interface.chat_terminal(user_input)
            print(f"JARVIS: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\nJARVIS: Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(terminal_chat())


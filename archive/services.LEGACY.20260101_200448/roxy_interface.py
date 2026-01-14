#!/usr/bin/env python3
"""
ROXY Interface - Multiple ways to interact with the resident AI
Terminal, Voice, Web, API - all connected to the same learning brain
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

sys.path.insert(0, '/home/mark/.roxy/services')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.interface')

class RoxyInterface:
    """Unified interface to ROXY - the resident AI"""
    
    def __init__(self):
        self.roxy_core = None
        self.memory = None
        self.llm_service = None
        self._connect_to_roxy()
        self._init_services()
    
    def _connect_to_roxy(self):
        """Connect to ROXY core via event bus or direct"""
        # ROXY runs as a service - we'll communicate via NATS or direct DB access
        try:
            # Check if service is running
            import subprocess
            result = subprocess.run(['systemctl', 'is-active', 'roxy.service'], 
                                  capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                logger.info("ROXY service is running")
                self.roxy_running = True
            else:
                logger.warning("ROXY service not running")
                self.roxy_running = False
        except Exception as e:
            logger.warning(f"Could not check ROXY status: {e}")
            self.roxy_running = False
    
    def _init_services(self):
        """Initialize memory and LLM services once"""
        try:
            from roxy_core import RoxyMemory
            self.memory = RoxyMemory()
            logger.info("Memory service initialized")
        except Exception as e:
            logger.warning(f"Memory service unavailable: {e}")
            self.memory = None
        
        try:
            # Use wrapper to avoid email module conflict
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
            if self.llm_service.is_available():
                logger.info("✅ LLM service available")
            else:
                logger.warning("⚠️ LLM service not available (install langchain-ollama or set ANTHROPIC_API_KEY)")
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.llm_service = None
    
    async def chat_terminal(self, user_input: str) -> str:
        """Terminal chat interface"""
        # For now, process directly and store in memory
        # In future, would send to running ROXY service via NATS
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
            # Use initialized memory (don't create new instance each time)
            if not self.memory:
                from roxy_core import RoxyMemory
                self.memory = RoxyMemory()
            
            # Store this conversation
            response = await self._generate_response(user_input, self.memory)
            self.memory.remember_conversation(user_input, response)
            
            # Extract and learn facts
            learned = await self._extract_facts(user_input, response)
            for fact in learned:
                self.memory.learn_fact(fact, category="conversation")
            
            return response
        except Exception as e:
            logger.error(f"Error processing: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"ROXY: I encountered an error processing your request: {e}"
    
    async def _generate_response(self, user_input: str, memory) -> str:
        """Generate response using LLM with memory context and RAG - PROPER AGENT ARCHITECTURE"""
        # PRIORITY 0: Check semantic cache
        try:
            from semantic_cache import get_semantic_cache
            cache = get_semantic_cache()
            cached_response = await cache.get(user_input)
            if cached_response:
                logger.info("✅ Cache hit - returning cached response")
                return cached_response
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")
        
        # Get recent history and facts - ALWAYS use LLM for intelligent responses
        history = memory.get_conversation_history(limit=10)  # Get more history
        facts = memory.recall_facts(limit=10)
        
        logger.debug(f"Retrieved {len(history)} conversations, {len(facts)} facts")
        
        user_lower = user_input.lower()
        
        # PRIORITY 0: Check for file operation requests FIRST (before LLM hallucination)
        repo_path = "/home/mark/mindsong-juke-hub"
        repo_path_nested = "/home/mark/mindsong-juke-hub/mindsong-juke-hub"
        
        # Detect repository questions - CHECK BEFORE LLM
        is_repo_question = (
            "mindsong" in user_lower or "juke" in user_lower or "repo" in user_lower or
            "project" in user_lower or ("list" in user_lower and "page" in user_lower) or
            ("list" in user_lower and "file" in user_lower) or
            "codebase" in user_lower or "repository" in user_lower
        )
        
        # Check which repo path exists
        actual_repo_path = None
        if os.path.exists(repo_path):
            actual_repo_path = repo_path
        elif os.path.exists(repo_path_nested):
            actual_repo_path = repo_path_nested
        
        # PRIORITY 0: Tool Calling Framework (BEFORE LLM)
        # Check if this is a tool operation request
        try:
            from tool_caller import ToolCaller
            tool_caller = ToolCaller()
            tool_response = await tool_caller.process_with_tools(user_input)
            if tool_response:
                logger.info(f"🔧 Tool execution successful: {len(tool_response)} chars")
                return tool_response
        except Exception as e:
            logger.debug(f"Tool calling not applicable or failed: {e}")
        
        # PRIORITY 0.5: File operations for "list" queries (BEFORE LLM)
        # Check for file operation requests FIRST - this prevents LLM hallucination
        if "list" in user_lower and ("page" in user_lower or "file" in user_lower or "component" in user_lower):
            # Try to find repository path - check multiple locations
            if not actual_repo_path:
                # Try /home/mark/.roxy as fallback
                if os.path.exists("/home/mark/.roxy"):
                    actual_repo_path = "/home/mark/.roxy"
            
            if actual_repo_path:
                logger.info(f"📁 File operation requested: listing files from {actual_repo_path}")
                try:
                    file_list = await self._list_repository_files(actual_repo_path, user_input)
                    if file_list and len(file_list) > 50:  # Real file list should be substantial
                        logger.info(f"✅ File listing successful: {len(file_list)} chars")
                        # Add source attribution for transparency
                        return f"{file_list}\n\n📌 Source: Real filesystem scan of {actual_repo_path}"
                    else:
                        logger.warning(f"⚠️ File listing returned short result: {len(file_list) if file_list else 0} chars")
                except Exception as e:
                    logger.error(f"File listing error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Continue to try other methods, but log the error
            else:
                logger.warning("⚠️ Repository path not found, cannot perform file operations")
        
        # PRIORITY 1: Try LLM for general queries (ONLY if NOT a file operation request)
        # Skip LLM if this is clearly a file operation request to prevent hallucination
        is_file_operation_request = "list" in user_lower and ("page" in user_lower or "file" in user_lower or "component" in user_lower)
        if not is_file_operation_request:
            try:
                if not self.llm_service:
                    from llm_wrapper import get_llm_service_safe
                    self.llm_service = get_llm_service_safe()
                
                if self.llm_service and self.llm_service.is_available():
                    # Use LLM for intelligent response with proper context
                    logger.info(f"🤖 Using LLM for: {user_input[:50]}...")
                    logger.debug(f"   History: {len(history)} items, Facts: {len(facts)} items")
                    
                    response = await self.llm_service.generate_response(
                        user_input=user_input,
                        context={'session_id': 'roxy_terminal'},
                        history=history,
                        facts=facts
                    )
                    
                    if response and response.strip() and len(response.strip()) > 10:
                        logger.info(f"✅ LLM response received: {len(response)} chars")
                        
                        # PRIORITY 1.5: Validate response
                        try:
                            from validation_loop import get_validator
                            validator = get_validator()
                            validation = await validator.validate_response(
                                user_input, response.strip(), 
                                context={'session_id': 'roxy_terminal', 'source': 'llm'}
                            )
                            
                            # Self-correct if needed
                            if not validation['valid']:
                                try:
                                    from self_correction import get_self_correction
                                    self_correction = get_self_correction()
                                    corrected = await self_correction.detect_and_correct(
                                        user_input, response.strip(), validation
                                    )
                                    if corrected:
                                        response = corrected
                                        validation = await validator.validate_response(
                                            user_input, corrected, {'source': 'corrected'}
                                        )
                                        logger.info("✅ Response self-corrected")
                                except Exception as e:
                                    logger.debug(f"Self-correction failed: {e}")
                            
                            if not validation['valid'] and validation.get('corrected_response'):
                                response = validation['corrected_response']
                                logger.info("✅ Response corrected via validation loop")
                            elif not validation['valid']:
                                logger.warning(f"⚠️ Response validation failed: {validation.get('issues', [])}")
                            
                            # Quality check
                            try:
                                from quality_checker import get_quality_checker
                                quality_checker = get_quality_checker()
                                quality = quality_checker.check_quality(
                                    response, 'llm', {'user_input': user_input}
                                )
                                if quality['quality_score'] < 0.7:
                                    response = quality_checker.enhance_response(response, quality)
                                    logger.info(f"✅ Response quality enhanced (score: {quality['quality_score']:.2f})")
                            except Exception as e:
                                logger.debug(f"Quality check failed: {e}")
                        except Exception as e:
                            logger.debug(f"Validation/quality check failed: {e}")
                        
                        # Add source attribution for transparency
                        if '📌 Source:' not in response:
                            response_with_source = f"{response.strip()}\n\n📌 Source: LLM (Ollama llama3:8b)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        else:
                            response_with_source = response.strip()
                        
                        # Cache the response
                        try:
                            from semantic_cache import get_semantic_cache
                            cache = get_semantic_cache()
                            await cache.set(user_input, response_with_source)
                        except Exception as e:
                            logger.debug(f"Cache storage failed: {e}")
                        
                        return response_with_source
                    else:
                        logger.warning(f"⚠️ LLM returned empty/short response: {response}")
            except Exception as e:
                logger.error(f"❌ LLM service error: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # PRIORITY 2: Check if question is about mindsong-juke-hub repository (RAG + FILE OPERATIONS)
        repo_path = "/home/mark/mindsong-juke-hub"
        repo_path_nested = "/home/mark/mindsong-juke-hub/mindsong-juke-hub"
        
        # Detect repository questions
        is_repo_question = (
            "mindsong" in user_lower or "juke" in user_lower or "repo" in user_lower or
            "project" in user_lower or "list" in user_lower and "page" in user_lower or
            "file" in user_lower or "codebase" in user_lower
        )
        
        # Check which repo path exists
        actual_repo_path = None
        if os.path.exists(repo_path):
            actual_repo_path = repo_path
        elif os.path.exists(repo_path_nested):
            actual_repo_path = repo_path_nested
        
        if is_repo_question and actual_repo_path:
            logger.info(f"🔍 Repository question detected, using RAG + file operations for: {actual_repo_path}")
            
            # FIRST: Try direct file operations for specific queries
            if "list" in user_lower and ("page" in user_lower or "file" in user_lower):
                try:
                    file_list = await self._list_repository_files(actual_repo_path, user_input)
                    if file_list:
                        return file_list
                except Exception as e:
                    logger.warning(f"File listing error: {e}")
            
            # SECOND: Use Hybrid RAG for intelligent retrieval
            try:
                from hybrid_rag import HybridRAG
                hybrid_rag = HybridRAG(actual_repo_path)
                
                # Check if indexed
                stats = hybrid_rag.indexer.get_stats()
                if stats.get('total_chunks', 0) > 0:
                    # Use Hybrid RAG for repository questions
                    logger.info(f"📚 Using Hybrid RAG with {stats.get('total_chunks', 0)} chunks")
                    response = await hybrid_rag.answer_question(user_input, context_limit=15)
                    if response and response.strip():
                        # Validate hybrid RAG response
                        try:
                            from validation_loop import get_validator
                            validator = get_validator()
                            validation = await validator.validate_response(
                                user_input, response.strip(),
                                context={'repo': actual_repo_path, 'source': 'rag'}
                            )
                            if not validation['valid'] and validation.get('corrected_response'):
                                response = validation['corrected_response']
                            
                            # Self-correct if needed
                            try:
                                from self_correction import get_self_correction
                                self_correction = get_self_correction()
                                corrected = await self_correction.detect_and_correct(
                                    user_input, response.strip(), validation, {'repo': actual_repo_path}
                                )
                                if corrected:
                                    response = corrected
                            except:
                                pass
                            
                            # Quality check
                            try:
                                from quality_checker import get_quality_checker
                                quality_checker = get_quality_checker()
                                quality = quality_checker.check_quality(
                                    response, 'rag', {'user_input': user_input, 'repo': actual_repo_path}
                                )
                                if quality['quality_score'] < 0.7:
                                    response = quality_checker.enhance_response(response, quality)
                            except:
                                pass
                        except Exception as e:
                            logger.debug(f"Validation/quality check failed: {e}")
                        
                        # Ensure source attribution
                        if '📌 Source:' not in response:
                            response = f"{response}\n\n📌 Source: RAG (Retrieval Augmented Generation)\n📍 Repository: {actual_repo_path}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        
                        # Cache response
                        try:
                            from semantic_cache import get_semantic_cache
                            cache = get_semantic_cache()
                            await cache.set(user_input, response)
                        except:
                            pass
                        
                        return response.strip()
                else:
                    # Not indexed - trigger indexing and use file operations
                    logger.warning("Repository not indexed, using direct file operations")
                    return await self._list_repository_files(actual_repo_path, user_input)
            except Exception as e:
                logger.error(f"Hybrid RAG error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback to file operations
                return await self._list_repository_files(actual_repo_path, user_input)
        
        # PRIORITY 3: Fallback pattern matching (only if LLM fails)
        stats = memory.get_stats()
        
        if "remember" in user_lower or "what do you know" in user_lower:
            if facts:
                # Filter out stress test facts and show real knowledge
                real_facts = [f for f in facts if 'stress_test' not in str(f.get('fact', '')).lower()]
                if real_facts:
                    fact_list = "\n".join([f"- {f.get('fact', f)}" for f in real_facts[:5]])
                    response = f"I remember {len(real_facts)} things. Here are some examples:\n{fact_list}"
                    return f"{response}\n\n📌 Source: Pattern Matching (Memory Recall)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    # Only stress test facts, show a helpful message
                    response = "I'm still learning! I have some system test data, but I'd love to learn more about you and your work. Tell me something about yourself or the mindsong-juke-hub project!"
                    return f"{response}\n\n📌 Source: Pattern Matching (Memory Check)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                response = "I'm still learning! Tell me something about yourself."
                return f"{response}\n\n📌 Source: Pattern Matching (Memory Check)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if "my name is" in user_lower:
            name = user_lower.split("my name is")[-1].strip()
            response = f"Nice to meet you, {name}! I'll remember that."
            return f"{response}\n\n📌 Source: Pattern Matching (Name Extraction)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if "i like" in user_lower or "i prefer" in user_lower:
            preference = user_lower.split("i like")[-1].split("i prefer")[-1].strip()
            response = f"Got it! I'll remember you like {preference}."
            return f"{response}\n\n📌 Source: Pattern Matching (Preference Extraction)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if "how are you" in user_lower:
            response = "I'm doing well, thank you! I'm always learning and ready to help. How can I assist you today?"
            return f"{response}\n\n📌 Source: Pattern Matching (Greeting)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if "hello" in user_lower or "hi" in user_lower:
            response = "Hello! I'm ROXY, your resident AI assistant. I remember everything we discuss. How can I help you today?"
            return f"{response}\n\n📌 Source: Pattern Matching (Greeting)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Check for repository audit/analysis requests
        if "audit" in user_lower and ("repo" in user_lower or "repository" in user_lower or "mindsong" in user_lower or "juke" in user_lower or "entire" in user_lower):
            return await self._handle_repo_audit(user_input, user_lower)
        
        # Check for questions about mindsong-juke-hub
        if ("mindsong" in user_lower or "juke" in user_lower) and ("what" in user_lower or "know" in user_lower or "about" in user_lower):
            return await self._handle_repo_info(user_lower)
        
        # Check for work/tasks requests
        if "what work" in user_lower or "what has been done" in user_lower:
            return await self._handle_work_summary()
        
        # Last resort fallback - but try LLM one more time with better error handling
        logger.warning("All fallbacks exhausted, trying LLM with minimal context")
        try:
            if self.llm_service and self.llm_service.is_available():
                # Try with just the user input
                simple_response = await self.llm_service.generate_response(
                    user_input=user_input,
                    context={},
                    history=[],
                    facts=[]
                )
                if simple_response and simple_response.strip() and len(simple_response.strip()) > 10:
                    response = simple_response.strip()
                    # Add source attribution
                    if '📌 Source:' not in response:
                        response = f"{response}\n\n📌 Source: LLM (Ollama llama3:8b - Minimal Context)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    return response
        except Exception as e:
            logger.error(f"Final LLM attempt failed: {e}")
        
        # Absolute last resort
        fallback_response = f"I understand you said: '{user_input}'. I'm processing your request. (LLM service may need attention - check logs)"
        return f"{fallback_response}\n\n📌 Source: Fallback Response (All Methods Exhausted)\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    async def _handle_repo_audit(self, user_input: str, user_lower: str) -> str:
        """Handle repository audit requests"""
        try:
            # Extract repo path from request
            repo_path = None
            
            # Common repo locations to check
            possible_paths = [
                "/home/mark/mindsong-juke-hub",
                "/opt/mindsong-juke-hub",
                "~/mindsong-juke-hub",
                os.path.expanduser("~/mindsong-juke-hub"),
            ]
            
            # Check if mindsong-juke-hub is mentioned OR if "entire repo" or just "repo" is mentioned
            if "mindsong" in user_lower or "juke" in user_lower or ("entire" in user_lower and "repo" in user_lower):
                # Try common paths
                for path in possible_paths:
                    if os.path.exists(path) and os.path.isdir(path):
                        repo_path = path
                        break
                
                # If not found, search for it
                if not repo_path:
                    import subprocess
                    try:
                        result = subprocess.run(
                            ['find', '/home/mark/.roxy', '-maxdepth', '2', '-type', 'd', '-name', '*mindsong*'],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            for line in result.stdout.strip().split('\n'):
                                if line and os.path.exists(line) and os.path.isdir(line):
                                    repo_path = line
                                    break
                    except:
                        pass
            
            # Try to find repo path in input (absolute paths)
            if not repo_path:
                import re
                # Look for absolute paths
                paths = re.findall(r'[/~][\w/-]+', user_input)
                for path in paths:
                    expanded = os.path.expanduser(path)
                    if os.path.exists(expanded) and os.path.isdir(expanded):
                        repo_path = expanded
                        break
            
            # Default to /home/mark/.roxy if no specific repo mentioned
            if not repo_path:
                if os.path.exists("/home/mark/.roxy") and os.path.isdir("/home/mark/.roxy"):
                    # Check if it's a git repo
                    if os.path.exists("/home/mark/.roxy/.git"):
                        repo_path = "/home/mark/.roxy"
            
            # Default to /home/mark/mindsong-juke-hub if it exists
            if not repo_path:
                default_path = "/home/mark/mindsong-juke-hub"
                if os.path.exists(default_path) and os.path.isdir(default_path):
                    repo_path = default_path
            
            if not repo_path or not os.path.exists(repo_path):
                return f"I couldn't find the repository. I checked:\n" + \
                       "\n".join([f"  - {p}" for p in possible_paths[:3]]) + \
                       f"\n\nPlease specify the full path, or make sure the repository exists at /home/mark/mindsong-juke-hub"
            
            # Check if metrics requested
            metrics_count = 50
            if "metric" in user_lower:
                import re
                metric_match = re.search(r'(\d+)\s*metric', user_lower)
                if metric_match:
                    metrics_count = int(metric_match.group(1))
            
            return f"I'll audit the repository at {repo_path} and produce a {metrics_count}-metric evaluation. This will take a moment...\n\n" + \
                   await self._run_repo_audit(repo_path, metrics_count)
        except Exception as e:
            logger.error(f"Error handling repo audit: {e}")
            return f"Sorry, I encountered an error processing the repository audit request: {e}"
    
    async def _run_repo_audit(self, repo_path: str, metrics_count: int) -> str:
        """Run repository audit using agents"""
        try:
            from agents.framework.agent_orchestrator import AgentOrchestrator
            from agents.repo.code_analysis_agent import CodeAnalysisAgent
            from agents.repo.metrics_agent import MetricsAgent
            
            orchestrator = AgentOrchestrator()
            analysis_agent = CodeAnalysisAgent()
            metrics_agent = MetricsAgent()
            
            # Get all Python files in repo
            python_files = []
            for root, dirs, files in os.walk(repo_path):
                # Skip hidden dirs and common exclusions
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
            
            results = []
            results.append(f"📊 Repository Audit: {repo_path}")
            results.append(f"📁 Found {len(python_files)} Python files")
            results.append("")
            
            # Analyze first 10 files as sample
            sample_files = python_files[:10]
            for file_path in sample_files:
                task = {'file_path': file_path}
                analysis = await analysis_agent.execute(task)
                if 'error' not in analysis:
                    results.append(f"  • {os.path.basename(file_path)}: {analysis.get('lines', 0)} lines, {len(analysis.get('issues', []))} issues")
            
            # Get metrics
            metrics_task = {'repo_path': repo_path, 'metrics_count': metrics_count}
            metrics = await metrics_agent.execute(metrics_task)
            
            if 'error' not in metrics:
                results.append("")
                results.append("📈 Key Metrics:")
                for i, metric in enumerate(list(metrics.get('metrics', {}).items())[:metrics_count], 1):
                    key, value = metric
                    results.append(f"  {i}. {key}: {value}")
            
            return "\n".join(results)
        except Exception as e:
            logger.error(f"Error running repo audit: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error running audit: {e}. Make sure the repository agents are properly configured."
    
    async def _handle_work_summary(self) -> str:
        """Handle work summary requests"""
        try:
            if not self.memory:
                from roxy_core import RoxyMemory
                self.memory = RoxyMemory()
            
            # Get recent conversations
            history = self.memory.get_conversation_history(limit=10)
            
            if not history:
                return "I don't have any recent work history yet. Let's get started!"
            
            summary = ["📋 Recent Work Summary:"]
            summary.append("")
            
            for i, conv in enumerate(history[:5], 1):
                user_msg = conv.get('user_input', '')[:50]
                summary.append(f"{i}. {user_msg}...")
            
            summary.append("")
            summary.append(f"Total conversations: {len(history)}")
            
            return "\n".join(summary)
        except Exception as e:
            return f"Error retrieving work summary: {e}"
    
    async def _handle_repo_info(self, user_lower: str) -> str:
        """Handle questions about the mindsong-juke-hub repository using RAG"""
        try:
            repo_path = "/home/mark/mindsong-juke-hub"
            
            if not os.path.exists(repo_path):
                return "I don't have information about the mindsong-juke-hub repository. It doesn't appear to exist at /home/mark/mindsong-juke-hub"
            
            # Use RAG for intelligent retrieval
            try:
                from repository_rag import get_repo_rag
                rag = get_repo_rag(repo_path)
                
                # Check if indexed
                stats = rag.indexer.get_stats()
                if stats.get('total_chunks', 0) == 0:
                    # Not indexed yet - trigger indexing
                    return await self._index_and_respond(repo_path, user_lower)
                
                # Use RAG to answer
                question = "What is this repository about? What are its main features and structure?"
                response = await rag.answer_question(question, context_limit=10)
                
                # Add summary
                summary = await rag.get_repository_summary()
                
                return f"{summary}\n\n{response}\n\n💡 I have full knowledge of this repository indexed. Ask me anything about it!"
            except ImportError:
                # Fallback to basic info
                return await self._get_basic_repo_info(repo_path)
        except Exception as e:
            logger.error(f"Error getting repo info: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error retrieving repository information: {e}"
    
    async def _list_repository_files(self, repo_path: str, user_input: str) -> str:
        """List actual files from repository - REAL FILE OPERATIONS"""
        from pathlib import Path
        
        try:
            repo = Path(repo_path)
            if not repo.exists():
                return f"Repository not found at {repo_path}"
            
            user_lower = user_input.lower()
            
            # Detect what to list
            list_pages = "page" in user_lower or "route" in user_lower
            list_components = "component" in user_lower
            list_all = "list" in user_lower and ("all" in user_lower or "file" in user_lower)
            
            files_found = []
            
            if list_pages:
                # Find page files (React/Next.js patterns) - REAL FILE SEARCH
                # Search in common locations
                search_paths = [
                    repo / "src" / "pages",
                    repo / "app",
                    repo / "pages",
                    repo / "src" / "app",
                    repo / "routes",
                ]
                
                # Also search for files with "page" in name
                for search_path in search_paths:
                    if search_path.exists():
                        for file in search_path.rglob("*.{tsx,ts,jsx,js}"):
                            if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git', 'dist', 'build', '__pycache__']):
                                rel_path = file.relative_to(repo)
                                if str(rel_path) not in files_found:
                                    files_found.append(str(rel_path))
                
                # Also search for files with "page" in name anywhere
                for file in repo.rglob("*page*.{tsx,ts,jsx,js}"):
                    if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git', 'dist', 'build', '__pycache__', 'test']):
                        rel_path = file.relative_to(repo)
                        if str(rel_path) not in files_found:
                            files_found.append(str(rel_path))
            
            elif list_components:
                # Find component files
                for file in repo.rglob("**/*.{tsx,ts,jsx,js}"):
                    if 'component' in file.name.lower() or 'Component' in file.name:
                        if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git']):
                            rel_path = file.relative_to(repo)
                            files_found.append(str(rel_path))
            
            else:
                # List key files
                key_files = [
                    "README.md", "package.json", "tsconfig.json",
                    "next.config.js", "vite.config.ts", "tailwind.config.js"
                ]
                for key_file in key_files:
                    for file in repo.rglob(key_file):
                        if file.is_file():
                            rel_path = file.relative_to(repo)
                            files_found.append(str(rel_path))
                            break
                
                # Also find main source files
                for pattern in ["src/**/*.{tsx,ts}", "app/**/*.{tsx,ts}", "pages/**/*.{tsx,ts}"]:
                    for file in list(repo.rglob(pattern.split('/')[-1].replace('*', '*')))[:20]:
                        if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git']):
                            rel_path = file.relative_to(repo)
                            if str(rel_path) not in files_found:
                                files_found.append(str(rel_path))
            
            if not files_found:
                # Fallback: list all relevant files
                for ext in ['.tsx', '.ts', '.jsx', '.js', '.md']:
                    for file in list(repo.rglob(f"**/*{ext}"))[:50]:
                        if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git', 'dist', 'build', '__pycache__']):
                            rel_path = file.relative_to(repo)
                            if str(rel_path) not in files_found:
                                files_found.append(str(rel_path))
                        if len(files_found) >= 50:
                            break
                    if len(files_found) >= 50:
                        break
            
            # Format response
            if files_found:
                response_parts = [
                    f"📁 Found {len(files_found)} files in {repo.name}:",
                    ""
                ]
                
                # Group by directory
                by_dir = {}
                for file in sorted(files_found)[:100]:  # Limit to 100
                    dir_name = str(Path(file).parent)
                    if dir_name not in by_dir:
                        by_dir[dir_name] = []
                    by_dir[dir_name].append(Path(file).name)
                
                for i, (dir_name, files) in enumerate(sorted(by_dir.items())[:20], 1):  # Limit to 20 dirs
                    response_parts.append(f"{i}. {dir_name}/")
                    for file in files[:10]:  # Limit to 10 files per dir
                        response_parts.append(f"   • {file}")
                    if len(files) > 10:
                        response_parts.append(f"   ... and {len(files) - 10} more")
                    response_parts.append("")
                
                if len(files_found) > 100:
                    response_parts.append(f"\n... and {len(files_found) - 100} more files")
                
                response_parts.append(f"\n✅ Verified: This is a REAL file listing from the repository filesystem.")
                response_parts.append(f"📊 Total files found: {len(files_found)}")
                
                return "\n".join(response_parts)
            else:
                return f"I searched {repo_path} but couldn't find relevant files. The repository may be empty or use a different structure."
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error listing repository files: {e}"
    
    async def _index_and_respond(self, repo_path: str, user_lower: str) -> str:
        """Index repository and respond"""
        try:
            from repository_indexer import get_repo_indexer
            import asyncio
            
            indexer = get_repo_indexer(repo_path)
            
            # Start indexing in background
            async def index_background():
                try:
                    stats = indexer.index_repository()
                    logger.info(f"✅ Repository indexed: {stats.get('indexed_files', 0)} files, {stats.get('total_chunks', 0)} chunks")
                except Exception as e:
                    logger.error(f"Indexing error: {e}")
            
            # Start background task
            asyncio.create_task(index_background())
            
            return f"🔍 Indexing {repo_path} repository for full knowledge... This will take a moment.\n\n" + \
                   "I'm building a complete semantic index of the entire codebase. Once complete, I'll have instant access to everything.\n\n" + \
                   "You can continue asking questions - I'll index in the background and use what's available."
        except Exception as e:
            logger.error(f"Error starting repository indexing: {e}")
            return f"Error starting repository indexing: {e}. You can manually index with: python3 /home/mark/.roxy/scripts/index_mindsong_repo.py"
    
    async def _get_basic_repo_info(self, repo_path: str) -> str:
        """Get basic repository info (fallback)"""
        info = []
        info.append("📚 Mindsong Juke Hub Repository Information:")
        info.append("")
        
        # Get basic stats
        import subprocess
        try:
            # Get git info
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=repo_path,
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                commit = result.stdout.strip()
                info.append(f"📍 Location: {repo_path}")
                info.append(f"🔖 Latest commit: {commit}")
        except:
            pass
        
        # Get package info
        package_json = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json):
            try:
                import json
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                    info.append(f"📦 Project: {pkg.get('name', 'unknown')}")
                    info.append(f"📝 Description: {pkg.get('description', 'N/A')[:100]}")
            except:
                pass
        
        info.append("")
        info.append("💡 I can audit this repository for you! Just say 'audit the entire repo' or 'audit mindsong-juke-hub'")
        
        return "\n".join(info)
    
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
    """Interactive terminal chat with ROXY"""
    interface = RoxyInterface()
    
    print("=" * 70)
    print("🤖 ROXY - Resident AI Assistant")
    print("=" * 70)
    print("Type 'exit' or 'quit' to end conversation")
    print("Type 'status' to see ROXY status")
    print("Type 'memory' to see what ROXY remembers")
    print("=" * 70)
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("ROXY: Goodbye! I'll remember our conversation.")
                break
            
            if user_input.lower() == 'status':
                try:
                    import subprocess
                    result = subprocess.run(['systemctl', 'is-active', 'roxy.service'], 
                                          capture_output=True, text=True)
                    status = result.stdout.strip()
                    print(f"ROXY: Service status: {status}")
                    print(f"ROXY: I'm running and learning!")
                except:
                    print("ROXY: Status check unavailable")
                continue
            
            if user_input.lower() == 'memory':
                try:
                    from roxy_core import RoxyMemory
                    memory = RoxyMemory()
                    stats = memory.get_stats()
                    facts = memory.recall_facts(limit=5)
                    print(f"ROXY: Memory Statistics:")
                    print(f"  • Conversations: {stats['conversations']}")
                    print(f"  • Learned Facts: {stats['learned_facts']}")
                    print(f"  • Preferences: {stats['preferences']}")
                    if facts:
                        print(f"\nROXY: Recent things I've learned:")
                        for fact in facts[:3]:
                            print(f"  • {fact['fact']}")
                except Exception as e:
                    print(f"ROXY: Error accessing memory: {e}")
                continue
            
            response = await interface.chat_terminal(user_input)
            print(f"ROXY: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\nROXY: Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(terminal_chat())











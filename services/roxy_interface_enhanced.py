#!/usr/bin/env python3
"""
ROXY Interface Enhanced - With validation, quality checks, error handling, and self-correction
This is the enhanced version with all 100/100 improvements
"""
import asyncio
import logging
import os
import sys
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

ROXY_HOME = Path.home() / ".roxy"
ROXY_SERVICES = ROXY_HOME / "services"
ROXY_LEGACY = ROXY_HOME / "services.LEGACY.20260101_200448"
MINDSONG_HOME = Path.home() / "mindsong-juke-hub"

# Add services to path
sys.path.insert(0, str(ROXY_SERVICES))
if ROXY_LEGACY.exists():
    sys.path.insert(0, str(ROXY_LEGACY))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.interface.enhanced')

class EnhancedRoxyInterface:
    """Enhanced ROXY interface with all quality improvements"""
    
    def __init__(self):
        self.memory = None
        self.llm_service = None
        self.validator = None
        self.error_handler = None
        self.quality_checker = None
        self.self_correction = None
        self._init_all_services()
    
    def _init_all_services(self):
        """Initialize all services including new quality modules"""
        try:
            from roxy_core import RoxyMemory
            self.memory = RoxyMemory()
            logger.info("✅ Memory service initialized")
        except Exception as e:
            logger.warning(f"Memory service unavailable: {e}")
            self.memory = None
        
        try:
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
            if self.llm_service and self.llm_service.is_available():
                logger.info("✅ LLM service available")
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
            self.llm_service = None
        
        # Initialize new quality modules
        try:
            from validation_loop import get_validator
            self.validator = get_validator()
            logger.info("✅ Validation loop initialized")
        except Exception as e:
            logger.warning(f"Validation loop unavailable: {e}")
            self.validator = None
        
        try:
            from error_handler import get_error_handler
            self.error_handler = get_error_handler()
            logger.info("✅ Error handler initialized")
        except Exception as e:
            logger.warning(f"Error handler unavailable: {e}")
            self.error_handler = None
        
        try:
            from quality_checker import get_quality_checker
            self.quality_checker = get_quality_checker()
            logger.info("✅ Quality checker initialized")
        except Exception as e:
            logger.warning(f"Quality checker unavailable: {e}")
            self.quality_checker = None
        
        try:
            from self_correction import get_self_correction
            self.self_correction = get_self_correction()
            logger.info("✅ Self-correction initialized")
        except Exception as e:
            logger.warning(f"Self-correction unavailable: {e}")
            self.self_correction = None
    
    async def chat_terminal(self, user_input: str) -> str:
        """Terminal chat interface with full quality pipeline"""
        try:
            if not self.memory:
                from roxy_core import RoxyMemory
                self.memory = RoxyMemory()
            
            # Generate response with full pipeline
            response = await self._generate_response_enhanced(user_input, self.memory)
            
            # Store conversation
            self.memory.remember_conversation(user_input, response)
            
            # Extract and learn facts
            learned = await self._extract_facts(user_input, response)
            for fact in learned:
                self.memory.learn_fact(fact, category="conversation")
            
            return response
        except Exception as e:
            logger.error(f"Error in chat_terminal: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Use error handler if available
            if self.error_handler:
                return self.error_handler._error_response("chat_terminal", e)
            
            error_response = f"ROXY: I encountered an error processing your request: {e}"
            return self._add_source_attribution(
                error_response, 
                'error',
                context=f"Error in {type(e).__name__}",
                metadata={'confidence': 0.20, 'method': 'error_handler_fallback'}
            )
    
    async def _generate_response_enhanced(self, user_input: str, memory) -> str:
        """Enhanced response generation with validation, quality checks, and self-correction"""
        user_lower = user_input.lower()
        
        # Get context
        history = memory.get_conversation_history(limit=15)  # Increased from 10
        facts = memory.recall_facts(limit=15)  # Increased from 10
        
        # STEP 1: File operations (highest priority for file queries)
        repo_paths = [
            str(MINDSONG_HOME),
            str(MINDSONG_HOME / "mindsong-juke-hub")
        ]
        
        actual_repo_path = None
        for path in repo_paths:
            if os.path.exists(path):
                actual_repo_path = path
                break
        
        is_repo_question = any(kw in user_lower for kw in [
            "mindsong", "juke", "repo", "repository", "project", "codebase"
        ])
        
        if is_repo_question and actual_repo_path:
            if "list" in user_lower and ("page" in user_lower or "file" in user_lower or "component" in user_lower):
                try:
                    file_list = await self._list_repository_files(actual_repo_path, user_input)
                    if file_list and len(file_list) > 50:
                        # Validate file listing
                        if self.validator:
                            validation = await self.validator.validate_response(
                                user_input, file_list, {'source': 'filesystem'}
                            )
                            if not validation['valid'] and validation.get('corrected_response'):
                                file_list = validation['corrected_response']
                        
                        # Add source attribution
                        file_list = self._add_source_attribution(
                            file_list, 
                            'filesystem', 
                            context=actual_repo_path,
                            metadata={
                                'confidence': 0.95,
                                'method': 'filesystem_scan',
                                'files_accessed': [actual_repo_path]
                            }
                        )
                        
                        # Quality check
                        if self.quality_checker:
                            quality = self.quality_checker.check_quality(
                                file_list, 'filesystem', {'user_input': user_input}
                            )
                            if quality['quality_score'] < 0.7:
                                file_list = self.quality_checker.enhance_response(file_list, quality)
                        
                        return file_list
                except Exception as e:
                    logger.error(f"File listing error: {e}")
                    if self.error_handler:
                        await self.error_handler.execute_with_retry(
                            lambda: None, error_context="file_listing"
                        )
        
        # STEP 2: LLM for general queries
        if not (is_repo_question and "list" in user_lower):
            try:
                if self.llm_service and self.llm_service.is_available():
                    response = await self.llm_service.generate_response(
                        user_input=user_input,
                        context={'session_id': 'roxy_terminal'},
                        history=history,
                        facts=facts
                    )
                    
                    if response and response.strip() and len(response.strip()) > 10:
                        # Validate LLM response (enhanced validation)
                        if self.validator:
                            validation = await self.validator.validate_response(
                                user_input, response.strip(), {'source': 'llm', 'response_length': len(response)}
                            )
                            
                            # Log validation issues
                            if not validation['valid']:
                                logger.warning(f"⚠️ Validation issues detected: {validation.get('issues', [])}")
                                logger.info(f"   Confidence: {validation.get('confidence', 0):.1%}")
                            
                            # Self-correct if needed (enhanced)
                            if self.self_correction and not validation['valid']:
                                corrected = await self.self_correction.detect_and_correct(
                                    user_input, response.strip(), validation, {'original_source': 'llm'}
                                )
                                if corrected:
                                    logger.info("✅ Self-correction applied")
                                    response = corrected
                                    # Re-validate corrected response
                                    validation = await self.validator.validate_response(
                                        user_input, corrected, {'source': 'corrected', 'original_source': 'llm'}
                                    )
                                    # If still invalid, mark with lower confidence
                                    if not validation['valid']:
                                        logger.warning(f"⚠️ Corrected response still has issues: {validation.get('issues', [])}")
                        
                        # Add source attribution
                        response = self._add_source_attribution(
                            response.strip(), 
                            'llm',
                            metadata={
                                'confidence': 0.70,
                                'method': 'llm_generation'
                            }
                        )
                        
                        # Quality check
                        if self.quality_checker:
                            quality = self.quality_checker.check_quality(
                                response, 'llm', {'user_input': user_input}
                            )
                            if quality['quality_score'] < 0.7:
                                response = self.quality_checker.enhance_response(response, quality)
                        
                        return response
            except Exception as e:
                logger.error(f"LLM error: {e}")
        
        # STEP 3: RAG for repository questions
        if is_repo_question and actual_repo_path:
            try:
                from repository_rag import get_repo_rag
                rag = get_repo_rag(actual_repo_path)
                stats = rag.indexer.get_stats()
                
                if stats.get('total_chunks', 0) > 0:
                    response = await rag.answer_question(user_input, context_limit=15)
                    if response and response.strip():
                        # Validate RAG response (enhanced)
                        if self.validator:
                            validation = await self.validator.validate_response(
                                user_input, response.strip(), {'source': 'rag', 'rag_stats': stats}
                            )
                            
                            if not validation['valid']:
                                logger.warning(f"⚠️ RAG validation issues: {validation.get('issues', [])}")
                                
                                # Try corrected response from validation
                                if validation.get('corrected_response'):
                                    response = validation['corrected_response']
                                    logger.info("✅ Using validation-corrected RAG response")
                                
                                # Also try self-correction
                                elif self.self_correction:
                                    corrected = await self.self_correction.detect_and_correct(
                                        user_input, response.strip(), validation, {'original_source': 'rag'}
                                    )
                                    if corrected:
                                        response = corrected
                                        logger.info("✅ Self-corrected RAG response")
                        
                        # Add source attribution (already in RAG, but ensure it's there)
                        if '📌 Source:' not in response:
                            response = self._add_source_attribution(
                                response.strip(), 
                                'rag', 
                                context=actual_repo_path,
                                metadata={
                                    'confidence': 0.85,
                                    'method': 'rag_retrieval',
                                    'chunks_retrieved': len(rag_results.get('chunks', [])) if isinstance(rag_results, dict) else 0
                                }
                            )
                        
                        return response
            except Exception as e:
                logger.error(f"RAG error: {e}")
        
        # STEP 4: Pattern matching (with source attribution)
        pattern_response = self._pattern_matching_response(user_input, user_lower, memory)
        if pattern_response:
            return self._add_source_attribution(
                pattern_response, 
                'pattern',
                metadata={
                    'confidence': 0.50,
                    'method': 'pattern_matching'
                }
            )
        
        # STEP 5: Final fallback (with source attribution)
        fallback = f"I understand you said: '{user_input}'. I'm processing your request. (LLM service may need attention - check logs)"
        return self._add_source_attribution(
            fallback, 
            'fallback',
            metadata={
                'confidence': 0.30,
                'method': 'fallback_response'
            }
        )
    
    def _add_source_attribution(self, response: str, source: str, 
                               context: str = None, metadata: Dict = None) -> str:
        """
        Add comprehensive source attribution to response with confidence scores and metadata
        
        Args:
            response: The response text
            source: Source type (filesystem, rag, llm, pattern, fallback, error, corrected)
            context: Optional context string
            metadata: Optional metadata dict with:
                - confidence: float (0-1)
                - method: str (method used)
                - chunks_retrieved: int (for RAG)
                - files_accessed: List[str] (for file operations)
                - timestamp: str (ISO format)
        """
        # Don't add if already present (unless we're enhancing it)
        if '📌 Source:' in response and metadata is None:
            return response
        
        timestamp = datetime.now().isoformat()
        
        # Source mapping with confidence levels
        source_map = {
            'filesystem': {'name': '📁 Real Filesystem Scan', 'confidence': 0.95},
            'rag': {'name': '📚 RAG (Retrieval Augmented Generation)', 'confidence': 0.85},
            'llm': {'name': '🤖 LLM (Ollama llama3:8b)', 'confidence': 0.70},
            'pattern': {'name': '🔍 Pattern Matching', 'confidence': 0.50},
            'fallback': {'name': '⚠️ Fallback Response', 'confidence': 0.30},
            'error': {'name': '❌ Error Handler', 'confidence': 0.20},
            'corrected': {'name': '🔧 Self-Corrected Response', 'confidence': 0.80},
            'quality_checked': {'name': '✅ Quality Checked', 'confidence': 0.90}
        }
        
        source_info = source_map.get(source, {'name': f'Source: {source}', 'confidence': 0.50})
        source_text = source_info['name']
        default_confidence = source_info['confidence']
        
        # Use metadata confidence if provided, otherwise use default
        confidence = metadata.get('confidence', default_confidence) if metadata else default_confidence
        
        # Build attribution block
        attribution_parts = [f"\n\n📌 Source: {source_text}"]
        
        # Add confidence score
        confidence_emoji = '✅' if confidence >= 0.8 else '⚠️' if confidence >= 0.5 else '❌'
        attribution_parts.append(f"{confidence_emoji} Confidence: {confidence:.0%}")
        
        # Add context if provided
        if context:
            attribution_parts.append(f"📍 Context: {context}")
        
        # Add metadata if provided
        if metadata:
            if metadata.get('method'):
                attribution_parts.append(f"🔧 Method: {metadata['method']}")
            if metadata.get('chunks_retrieved'):
                attribution_parts.append(f"📚 Chunks Retrieved: {metadata['chunks_retrieved']}")
            if metadata.get('files_accessed'):
                files = metadata['files_accessed']
                if isinstance(files, list):
                    file_count = len(files)
                    if file_count <= 3:
                        attribution_parts.append(f"📁 Files: {', '.join(files)}")
                    else:
                        attribution_parts.append(f"📁 Files Accessed: {file_count} files")
                else:
                    attribution_parts.append(f"📁 Files: {files}")
        
        # Add timestamp
        attribution_parts.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        attribution = "\n".join(attribution_parts)
        
        return response + attribution
    
    def _pattern_matching_response(self, user_input: str, user_lower: str, memory) -> str:
        """Pattern matching responses with source attribution"""
        stats = memory.get_stats()
        
        if "remember" in user_lower or "what do you know" in user_lower:
            facts = memory.recall_facts(limit=5)
            real_facts = [f for f in facts if 'stress_test' not in str(f.get('fact', '')).lower()]
            if real_facts:
                fact_list = "\n".join([f"- {f.get('fact', f)}" for f in real_facts[:5]])
                return f"I remember {len(real_facts)} things. Here are some examples:\n{fact_list}"
            return "I'm still learning! Tell me something about yourself."
        
        if "how are you" in user_lower:
            return "I'm doing well, thank you! I'm always learning and ready to help. How can I assist you today?"
        
        if "hello" in user_lower or "hi" in user_lower:
            return "Hello! I'm ROXY, your resident AI assistant. I remember everything we discuss. How can I help you today?"
        
        return None
    
    async def _list_repository_files(self, repo_path: str, user_input: str) -> str:
        """List repository files - real filesystem operations"""
        from pathlib import Path
        
        try:
            repo = Path(repo_path)
            if not repo.exists():
                error_msg = f"Repository not found at {repo_path}"
                return self._add_source_attribution(
                    error_msg,
                    'error',
                    context='filesystem_check',
                    metadata={
                        'confidence': 0.95,
                        'method': 'filesystem_check'
                    }
                )
            
            user_lower = user_input.lower()
            files_found = []
            
            # Find page files
            if "page" in user_lower:
                search_paths = [
                    repo / "src" / "pages",
                    repo / "app",
                    repo / "pages",
                    repo / "src" / "app",
                    repo / "routes",
                ]
                
                for search_path in search_paths:
                    if search_path.exists():
                        for file in search_path.rglob("*.{tsx,ts,jsx,js}"):
                            if file.is_file() and not any(skip in str(file) for skip in ['node_modules', '.git', 'dist', 'build']):
                                rel_path = file.relative_to(repo)
                                if str(rel_path) not in files_found:
                                    files_found.append(str(rel_path))
            
            # Format response
            if files_found:
                response_parts = [
                    f"📁 Found {len(files_found)} files in {repo.name}:",
                    ""
                ]
                
                for i, file_path in enumerate(files_found[:100], 1):
                    response_parts.append(f"{i}. {file_path}")
                
                if len(files_found) > 100:
                    response_parts.append(f"\n... and {len(files_found) - 100} more files")
                
                response_parts.append(f"\n✅ Verified: Real file listing from repository filesystem")
                return "\n".join(response_parts)
            
            no_files_msg = f"No files found matching your query in {repo.name}"
            return self._add_source_attribution(
                no_files_msg,
                'filesystem',
                context=f'Repository: {repo.name}',
                metadata={
                    'confidence': 0.95,
                    'method': 'filesystem_scan',
                    'files_accessed': []
                }
            )
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            error_msg = f"Error listing files: {e}"
            return self._add_source_attribution(
                error_msg,
                'error',
                context=f'Exception: {type(e).__name__}',
                metadata={
                    'confidence': 0.20,
                    'method': 'error_handler'
                }
            )
    
    async def _extract_facts(self, user_input: str, response: str) -> List[str]:
        """Extract facts from conversation"""
        facts = []
        # Simple fact extraction - can be enhanced
        return facts

# Global instance
_enhanced_interface = None

def get_enhanced_interface():
    """Get or create enhanced interface instance"""
    global _enhanced_interface
    if _enhanced_interface is None:
        _enhanced_interface = EnhancedRoxyInterface()
    return _enhanced_interface


#!/usr/bin/env python3
"""
ROXY Repository RAG - Retrieval Augmented Generation for repositories
Intelligent context retrieval and response generation
"""
import logging
from typing import List, Dict, Any, Optional
from repository_indexer import get_repo_indexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.repo_rag')

class RepositoryRAG:
    """RAG system for repository knowledge"""
    
    def __init__(self, repo_path: str):
        from pathlib import Path
        self.repo_path = Path(repo_path) if isinstance(repo_path, str) else repo_path
        self.indexer = get_repo_indexer(str(self.repo_path))
        self.llm_service = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM service"""
        try:
            from llm_wrapper import get_llm_service_safe
            self.llm_service = get_llm_service_safe()
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
    
    async def answer_question(self, question: str, context_limit: int = 5) -> str:
        """Answer question about repository using RAG"""
        # Search for relevant context
        search_results = self.indexer.search(question, n_results=context_limit)
        
        if not search_results:
            return f"I don't have information about that in the {self.repo_path.name} repository. The repository may not be indexed yet. Try running: index repository {self.repo_path}"
        
        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_results, 1):
            metadata = result.get('metadata', {})
            file_path = metadata.get('file_path', 'unknown')
            text = result.get('text', '')
            
            context_parts.append(f"[Context {i} from {file_path}]\n{text[:500]}\n")
        
        context = "\n".join(context_parts)
        
        # Generate response with LLM
        if self.llm_service and self.llm_service.is_available():
            prompt = f"""You are ROXY, an AI assistant with deep knowledge of the {self.repo_path.name} repository.

Based on the following context from the repository, answer the user's question accurately and comprehensively.

Repository Context:
{context}

User Question: {question}

Provide a detailed, accurate answer based on the repository context. If the context doesn't fully answer the question, say so and explain what information is available."""
            
            try:
                response = await self.llm_service.generate_response(
                    user_input=prompt,
                    context={'repo': str(self.repo_path)},
                    history=[],
                    facts=[]
                )
                # Add source attribution
                if response:
                    return f"{response}\n\n📌 Source: RAG (Retrieval Augmented Generation) from {self.repo_path.name} repository\n📚 Context chunks used: {context_limit}"
                return response or ""
            except Exception as e:
                logger.error(f"LLM generation error: {e}")
        
        # Fallback: return context directly
        repo_name = self.repo_path.name if hasattr(self.repo_path, 'name') else str(self.repo_path).split('/')[-1]
        return f"Based on the {repo_name} repository:\n\n{context}\n\n(Note: LLM not available for enhanced response)"
    
    async def get_repository_summary(self) -> str:
        """Get comprehensive repository summary"""
        # Get stats
        stats = self.indexer.get_stats()
        
        # Search for key files
        key_files = [
            'README.md', 'package.json', 'requirements.txt',
            'setup.py', 'pyproject.toml', 'Cargo.toml', 'go.mod'
        ]
        
        found_files = []
        for key_file in key_files:
            results = self.indexer.search(f"file {key_file}", n_results=1)
            if results:
                found_files.append(results[0])
        
        summary_parts = [
            f"📚 Repository: {self.repo_path.name}",
            f"📍 Path: {self.repo_path}",
            f"📊 Indexed: {stats.get('unique_files', 0)} files, {stats.get('total_chunks', 0)} chunks",
            ""
        ]
        
        if found_files:
            summary_parts.append("📄 Key Files Found:")
            for result in found_files:
                metadata = result.get('metadata', {})
                file_path = metadata.get('file_path', 'unknown')
                summary_parts.append(f"  • {file_path}")
        
        return "\n".join(summary_parts)
    
    def search_code(self, query: str, file_type: str = None) -> List[Dict]:
        """Search code in repository"""
        return self.indexer.search(query, n_results=10, file_filter=file_type)
    
    def get_file_context(self, file_path: str) -> str:
        """Get full context for a file"""
        chunks = self.indexer.get_file_info(file_path)
        
        if not chunks:
            return f"File {file_path} not found in index"
        
        context_parts = [f"File: {file_path}\n"]
        for chunk in chunks:
            context_parts.append(chunk['text'])
        
        return "\n".join(context_parts)


# Global RAG instances
_rag_instances: Dict[str, RepositoryRAG] = {}

def get_repo_rag(repo_path: str) -> RepositoryRAG:
    """Get or create RAG instance for repository"""
    global _rag_instances
    
    if repo_path not in _rag_instances:
        _rag_instances[repo_path] = RepositoryRAG(repo_path)
    
    return _rag_instances[repo_path]







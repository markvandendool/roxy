#!/usr/bin/env python3
"""
ROXY Repository Indexer - Full RAG indexing of repositories
Indexes entire codebases for instant semantic retrieval
"""
import os
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.repo_indexer')

class RepositoryIndexer:
    """Index entire repositories for semantic search and RAG"""
    
    def __init__(self, repo_path: str, collection_name: str = None):
        self.repo_path = Path(repo_path)
        self.collection_name = collection_name or f"repo_{self.repo_path.name}"
        self.client = None
        self.collection = None
        self._init_chromadb()
        
        # File extensions to index
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.clj',
            '.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.sql', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat',
            '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte',
            '.xml', '.rss', '.atom', '.svg'
        }
        
        # Directories to skip
        self.skip_dirs = {
            '.git', 'node_modules', 'venv', '__pycache__', '.next', 'dist',
            'build', '.cache', 'coverage', '.nyc_output', 'target',
            '.idea', '.vscode', '.vs', 'bin', 'obj', '.pytest_cache'
        }
    
    def _init_chromadb(self):
        """Initialize ChromaDB connection"""
        try:
            from chromadb.utils import embedding_functions
            
            # Use consistent embedding function (384 dimensions)
            # This matches the default ChromaDB embedding function
            embedding_function = embedding_functions.DefaultEmbeddingFunction()
            
            self.client = chromadb.HttpClient(host='localhost', port=8000)
            
            # Try to get existing collection first
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function
                )
                logger.info(f"✅ Using existing collection: {self.collection_name}")
            except:
                # Collection doesn't exist or has wrong embedding, create new one
                try:
                    # Delete old collection if it exists with wrong embedding
                    try:
                        self.client.delete_collection(name=self.collection_name)
                        logger.warning(f"⚠️ Deleted old collection with mismatched embedding")
                    except:
                        pass
                    
                    # Create new collection with correct embedding function
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=embedding_function,
                        metadata={
                            'description': f'Full index of {self.repo_path}',
                            'repo_path': str(self.repo_path),
                            'indexed_at': datetime.now().isoformat()
                        }
                    )
                    logger.info(f"✅ Created new collection: {self.collection_name}")
                except Exception as e2:
                    logger.error(f"❌ Failed to create collection: {e2}")
                    self.client = None
                    return
            
            logger.info(f"✅ Repository indexer initialized: {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ ChromaDB unavailable: {e}")
            self.client = None
    
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed"""
        # Check extension
        if file_path.suffix.lower() not in self.code_extensions:
            return False
        
        # Check if in skip directory
        for part in file_path.parts:
            if part in self.skip_dirs:
                return False
        
        # Check file size (skip very large files)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:  # 10MB
                return False
        except:
            return False
        
        return True
    
    def _get_file_id(self, file_path: Path) -> str:
        """Generate unique ID for file"""
        rel_path = file_path.relative_to(self.repo_path)
        return hashlib.md5(str(rel_path).encode()).hexdigest()
    
    def _chunk_file(self, content: str, file_path: Path, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """Chunk file content for better retrieval"""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_size = 0
        
        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'start_line': i - len(current_chunk) + 1,
                    'end_line': i
                })
                
                # Start new chunk with overlap
                overlap_lines = current_chunk[-overlap//50:] if len(current_chunk) > overlap//50 else current_chunk
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l) + 1 for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'start_line': len(lines) - len(current_chunk) + 1,
                'end_line': len(lines)
            })
        
        return chunks
    
    def index_file(self, file_path: Path) -> Dict:
        """Index a single file"""
        if not self._should_index_file(file_path):
            return {'indexed': False, 'reason': 'skipped'}
        
        try:
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content.strip():
                return {'indexed': False, 'reason': 'empty'}
            
            rel_path = file_path.relative_to(self.repo_path)
            file_id_base = self._get_file_id(file_path)
            
            # Chunk large files
            chunks = self._chunk_file(content, file_path) if len(content) > 5000 else [{'text': content, 'start_line': 1, 'end_line': len(content.split('\n'))}]
            
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_id_base}_chunk_{i}"
                
                # Create enhanced document with context
                doc_text = f"File: {rel_path}\n\n{chunk['text']}"
                
                documents.append(doc_text)
                metadatas.append({
                    'file_path': str(rel_path),
                    'file_name': file_path.name,
                    'file_extension': file_path.suffix,
                    'start_line': chunk['start_line'],
                    'end_line': chunk['end_line'],
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'repo_name': self.repo_path.name,
                    'indexed_at': datetime.now().isoformat()
                })
                ids.append(chunk_id)
            
            # Add to collection
            if documents:
                self.collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            return {
                'indexed': True,
                'file_path': str(rel_path),
                'chunks': len(chunks),
                'size': len(content)
            }
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}")
            return {'indexed': False, 'error': str(e)}
    
    def index_repository(self, force_reindex: bool = False) -> Dict:
        """Index entire repository"""
        if not self.client:
            return {'error': 'ChromaDB not available'}
        
        logger.info(f"🔍 Indexing repository: {self.repo_path}")
        
        stats = {
            'total_files': 0,
            'indexed_files': 0,
            'skipped_files': 0,
            'total_chunks': 0,
            'errors': []
        }
        
        # Get all files
        for root, dirs, files in os.walk(self.repo_path):
            # Filter skip directories
            dirs[:] = [d for d in dirs if d not in self.skip_dirs]
            
            for file in files:
                file_path = Path(root) / file
                stats['total_files'] += 1
                
                result = self.index_file(file_path)
                if result.get('indexed'):
                    stats['indexed_files'] += 1
                    stats['total_chunks'] += result.get('chunks', 1)
                else:
                    stats['skipped_files'] += 1
                    if 'error' in result:
                        stats['errors'].append(str(file_path))
                
                if stats['total_files'] % 100 == 0:
                    logger.info(f"  Processed {stats['total_files']} files, indexed {stats['indexed_files']}")
        
        logger.info(f"✅ Indexing complete: {stats['indexed_files']}/{stats['total_files']} files indexed, {stats['total_chunks']} chunks")
        return stats
    
    def search(self, query: str, n_results: int = 10, file_filter: str = None) -> List[Dict]:
        """Search repository with semantic search"""
        if not self.client:
            return []
        
        where = None
        if file_filter:
            where = {'file_path': {'$contains': file_filter}}
        
        try:
            # Ensure we use the same embedding function as the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            formatted = []
            for i in range(len(results['documents'][0])):
                formatted.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_file_info(self, file_path: str) -> List[Dict]:
        """Get all chunks for a specific file"""
        if not self.client:
            return []
        
        try:
            results = self.collection.get(
                where={'file_path': file_path}
            )
            
            chunks = []
            for i, doc in enumerate(results['documents']):
                chunks.append({
                    'id': results['ids'][i],
                    'text': doc,
                    'metadata': results['metadatas'][i] if results['metadatas'] else {}
                })
            
            return sorted(chunks, key=lambda x: x['metadata'].get('start_line', 0))
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get indexing statistics"""
        if not self.client:
            return {'error': 'ChromaDB not available'}
        
        try:
            count = self.collection.count()
            
            # Get unique files
            results = self.collection.get()
            unique_files = set()
            for meta in results.get('metadatas', []):
                if meta and 'file_path' in meta:
                    unique_files.add(meta['file_path'])
            
            return {
                'total_chunks': count,
                'unique_files': len(unique_files),
                'collection_name': self.collection_name,
                'repo_path': str(self.repo_path)
            }
        except Exception as e:
            return {'error': str(e)}


# Global indexers cache
_repo_indexers: Dict[str, RepositoryIndexer] = {}

def get_repo_indexer(repo_path: str, collection_name: str = None) -> RepositoryIndexer:
    """Get or create repository indexer"""
    global _repo_indexers
    
    key = f"{repo_path}_{collection_name or 'default'}"
    if key not in _repo_indexers:
        _repo_indexers[key] = RepositoryIndexer(repo_path, collection_name)
    
    return _repo_indexers[key]







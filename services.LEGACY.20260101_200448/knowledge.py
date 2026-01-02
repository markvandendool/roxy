#!/usr/bin/env python3
"""
ROXY Knowledge Index - ChromaDB Integration
Indexes transcripts, commands, and knowledge for semantic search
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROMA_HOST = "localhost"
CHROMA_PORT = 8000

# Collection definitions
COLLECTIONS = {
    "transcripts": {
        "description": "Video transcripts with timestamps",
        "metadata": ["video_name", "duration", "language"]
    },
    "clips": {
        "description": "Viral clip metadata and descriptions",
        "metadata": ["video_name", "viral_score", "category", "start_time", "end_time"]
    },
    "commands": {
        "description": "Voice commands and their handlers",
        "metadata": ["category", "handler", "examples"]
    },
    "knowledge": {
        "description": "General knowledge base entries",
        "metadata": ["source", "category", "date_added"]
    }
}

class KnowledgeIndex:
    def __init__(self, host: str = CHROMA_HOST, port: int = CHROMA_PORT):
        logger.info(f"Connecting to ChromaDB: {host}:{port}")
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collections = {}
        self._init_collections()
    
    def _init_collections(self):
        """Initialize all collections"""
        for name, config in COLLECTIONS.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata={"description": config["description"]}
                )
                self.collections[name] = collection
                logger.info(f"Collection ready: {name} ({collection.count()} docs)")
            except Exception as e:
                logger.error(f"Failed to create collection {name}: {e}")
    
    def index_transcript(self, video_name: str, transcript_data: Dict) -> int:
        """Index a video transcript for semantic search"""
        collection = self.collections.get("transcripts")
        if not collection:
            raise RuntimeError("Transcripts collection not available")
        
        documents = []
        metadatas = []
        ids = []
        
        # Index each segment
        for seg in transcript_data.get("segments", []):
            doc_id = f"{video_name}_{seg['id']}"
            documents.append(seg["text"])
            metadatas.append({
                "video_name": video_name,
                "segment_id": seg["id"],
                "start_time": seg["start"],
                "end_time": seg["end"],
                "duration": transcript_data.get("duration", 0),
                "language": transcript_data.get("language", "en")
            })
            ids.append(doc_id)
        
        # Add in batches
        batch_size = 100
        indexed = 0
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            indexed += len(batch_docs)
        
        logger.info(f"Indexed {indexed} segments from {video_name}")
        return indexed
    
    def index_clips(self, video_name: str, clips: List[Dict]) -> int:
        """Index viral clip suggestions"""
        collection = self.collections.get("clips")
        if not collection:
            raise RuntimeError("Clips collection not available")
        
        documents = []
        metadatas = []
        ids = []
        
        for i, clip in enumerate(clips):
            doc_id = f"{video_name}_clip_{i}"
            # Combine title, hook, and excerpt for searchability
            doc_text = f"{clip.get('title', '')}. {clip.get('hook', '')}. {clip.get('transcript_excerpt', '')}"
            
            documents.append(doc_text)
            metadatas.append({
                "video_name": video_name,
                "clip_index": i,
                "viral_score": clip.get("viral_score", 0),
                "category": clip.get("category", "unknown"),
                "start_time": clip.get("start_time", 0),
                "end_time": clip.get("end_time", 0),
                "reasoning": clip.get("reasoning", "")
            })
            ids.append(doc_id)
        
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"Indexed {len(clips)} clips from {video_name}")
        return len(clips)
    
    def index_command(self, command: str, handler: str, category: str, examples: List[str]):
        """Index a voice command pattern"""
        collection = self.collections.get("commands")
        if not collection:
            raise RuntimeError("Commands collection not available")
        
        doc_id = f"cmd_{handler}"
        doc_text = f"{command}. Examples: {', '.join(examples)}"
        
        collection.upsert(
            documents=[doc_text],
            metadatas=[{
                "category": category,
                "handler": handler,
                "examples": json.dumps(examples)
            }],
            ids=[doc_id]
        )
        logger.info(f"Indexed command: {handler}")
    
    def search(self, collection_name: str, query: str, n_results: int = 5, 
               where: Dict = None) -> List[Dict]:
        """Search a collection"""
        collection = self.collections.get(collection_name)
        if not collection:
            raise RuntimeError(f"Collection {collection_name} not available")
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where
        )
        
        # Format results
        formatted = []
        for i in range(len(results["documents"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else None
            })
        
        return formatted
    
    def search_transcripts(self, query: str, video_name: str = None, n_results: int = 10):
        """Search video transcripts"""
        where = {"video_name": video_name} if video_name else None
        return self.search("transcripts", query, n_results, where)
    
    def search_clips(self, query: str, min_score: int = None, n_results: int = 10):
        """Search viral clips"""
        where = {"viral_score": {"$gte": min_score}} if min_score else None
        return self.search("clips", query, n_results, where)
    
    def find_command(self, query: str) -> Optional[Dict]:
        """Find the best matching command for a query"""
        results = self.search("commands", query, n_results=1)
        return results[0] if results else None
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = {
                "count": collection.count(),
                "description": COLLECTIONS[name]["description"]
            }
        return stats


# Global index instance
_index: Optional[KnowledgeIndex] = None

def get_index() -> KnowledgeIndex:
    """Get or create global index instance"""
    global _index
    if _index is None:
        _index = KnowledgeIndex()
    return _index


# Demo
async def main():
    index = KnowledgeIndex()
    
    # Print stats
    print("ChromaDB Collections:")
    for name, stats in index.get_stats().items():
        print(f"  {name}: {stats['count']} documents - {stats['description']}")
    
    # Index some test commands
    index.index_command(
        "take a screenshot",
        "desktop.screenshot",
        "desktop",
        ["screenshot", "capture screen", "take a picture of the screen"]
    )
    
    index.index_command(
        "start recording",
        "obs.start_recording",
        "obs",
        ["start recording", "begin recording", "record video"]
    )
    
    # Search test
    print("\nSearching for 'capture the screen':")
    results = index.find_command("capture the screen")
    if results:
        print(f"  Found: {results['metadata']['handler']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

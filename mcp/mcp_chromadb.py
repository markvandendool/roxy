#!/usr/bin/env python3
"""
MCP ChromaDB Server - RAG queries for AI assistants
Part of LUNA-000 CITADEL P6: MCP Architecture

Exposes:
- rag_query: Query the knowledge base
- rag_add: Add document to knowledge base
- rag_count: Get document count
- rag_collections: List collections

CHIEF FIX: Use DefaultEmbeddingFunction (384-dim) to match collection contract
"""

import json
import hashlib
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

ROXY_DIR = Path.home() / ".roxy"

TOOLS = {
    "rag_query": {
        "description": "Query the RAG knowledge base",
        "parameters": {
            "query": {"type": "string", "required": True},
            "n_results": {"type": "integer", "default": 5}
        }
    },
    "rag_add": {
        "description": "Add a document to the knowledge base",
        "parameters": {
            "content": {"type": "string", "required": True},
            "metadata": {"type": "object", "default": {}}
        }
    },
    "rag_count": {
        "description": "Get document count in knowledge base",
        "parameters": {}
    },
    "rag_collections": {
        "description": "List all collections",
        "parameters": {}
    }
}

def get_client():
    """Get ChromaDB client"""
    return chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))

def get_embedding_function():
    """Get DefaultEmbeddingFunction (384-dim) - MUST match collection"""
    return DefaultEmbeddingFunction()

def handle_tool(name, params=None):
    """Handle MCP tool call"""
    if params is None:
        params = {}
    
    try:
        client = get_client()
        embedding_fn = get_embedding_function()
        
        if name == "rag_query":
            query = params.get("query")
            n = params.get("n_results", 5)
            
            collection = client.get_collection("mindsong_docs", embedding_function=embedding_fn)
            results = collection.query(
                query_texts=[query],
                n_results=n
            )
            
            return {
                "documents": results.get("documents", [[]])[0],
                "metadatas": results.get("metadatas", [[]])[0],
                "distances": results.get("distances", [[]])[0]
            }
        
        elif name == "rag_add":
            content = params.get("content")
            metadata = params.get("metadata", {})
            
            collection = client.get_or_create_collection(
                "mindsong_docs", 
                embedding_function=embedding_fn
            )
            
            doc_id = hashlib.md5(content.encode()).hexdigest()[:12]
            
            collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[metadata] if metadata else None
            )
            
            return {"success": True, "id": doc_id}
        
        elif name == "rag_count":
            try:
                collection = client.get_collection("mindsong_docs", embedding_function=embedding_fn)
                return {"count": collection.count()}
            except Exception:
                return {"count": 0, "note": "Collection not yet created"}
        
        elif name == "rag_collections":
            collections = client.list_collections()
            return {"collections": [c.name for c in collections]}
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = handle_tool(tool, params)
        print(json.dumps(result, indent=2))
    else:
        print("MCP ChromaDB Server")
        print("Tools:", list(TOOLS.keys()))

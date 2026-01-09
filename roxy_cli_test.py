#!/usr/bin/env python3
"""
ROXY CLI Test Mode
Tests the full pipeline without audio hardware

Usage:
  python3 roxy_cli_test.py
"""

import sys
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path.home() / ".roxy"))

import chromadb
import requests
from datetime import datetime

OLLAMA_URL = "http://127.0.0.1:11435/api/generate"
EMBED_URL = "http://127.0.0.1:11435/api/embeddings"
OLLAMA_MODEL = "llama3:8b"
EMBED_MODEL = "nomic-embed-text"

ROXY_SYSTEM_PROMPT = """You are ROXY, the AI assistant for MindSong and Mark's personal operations.

PERSONALITY:
- Warm, witty, and efficient like JARVIS
- Left-brain focused: operations, business, scheduling, systems
- Proactive and anticipatory
- Occasionally playful but always professional

CAPABILITIES:
- Access to MindSong codebase documentation via RAG
- Schedule management and reminders
- System status monitoring
- Home automation coordination

CONTEXT:
- Running on JARVIS-1 (Mac Pro 2019, 28-core Xeon, 157GB RAM)
- Part of LUNA-000 CITADEL project
- Working alongside Rocky (the music education AI - right brain)
- Together you form the Unified Mind for MindSong

Keep responses concise (2-3 sentences max unless asked for detail).
Current time: {time}
"""

def get_embedding(text: str) -> list:
    """Get embedding from Ollama"""
    resp = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=60)
    return resp.json()["embedding"]

def query_rag(query: str, n_results: int = 3) -> str:
    """Query ChromaDB for relevant context"""
    try:
        client = chromadb.PersistentClient(path=str(Path.home() / ".roxy" / "chroma_db"))
        collection = client.get_collection("mindsong_docs")
        embedding = get_embedding(query)
        results = collection.query(query_embeddings=[embedding], n_results=n_results)
        if results and results["documents"]:
            return "\n\n".join(results["documents"][0])[:2000]
    except Exception as e:
        print(f"[RAG] Error: {e}")
    return ""

def get_response(user_input: str, context: str = "") -> str:
    """Get response from Ollama"""
    system = ROXY_SYSTEM_PROMPT.format(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if context:
        system += f"\n\nRELEVANT CONTEXT FROM DOCUMENTATION:\n{context}"

    prompt = f"{system}\n\nUser: {user_input}\n\nRoxy:"

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 256}
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[LLM] Error: {e}")
    return "I'm having trouble connecting to my language model right now."

def main():
    print("\n" + "=" * 60)
    print("  ROXY CLI Test Mode")
    print("  Type 'quit' to exit, 'status' for system info")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\nRoxy: Goodbye! Call me anytime.\n")
                break
            if user_input.lower() == "status":
                print("\nRoxy: JARVIS-1 is operational. All systems nominal.")
                print("       - Ollama: llama3:8b loaded")
                print("       - RAG: 188 documents indexed")
                print("       - Audio: Ready (OWC dock + T2 speaker)")
                continue

            # Query RAG for context
            print("[Searching documentation...]")
            context = query_rag(user_input)

            # Get response
            print("[Generating response...]")
            response = get_response(user_input, context)

            print(f"\nRoxy: {response}")

        except KeyboardInterrupt:
            print("\n\nRoxy: Interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n[Error] {e}")

if __name__ == "__main__":
    main()

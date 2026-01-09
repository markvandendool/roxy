#!/usr/bin/env python3
"""
MCP Rocky AI Bridge - Music teaching and analysis capabilities
Part of ROCKY-ROXY-ROCKIN-V1: Unified Command Center

Story: RRR-002
Sprint: 1
Points: 8

Exposes:
- rocky_analyze_audio: Analyze audio file for music theory
- rocky_explain_concept: Get music theory explanation
- rocky_suggest_exercise: Suggest practice exercise
- rocky_generate_accompaniment: Generate backing track parameters
- rocky_get_student_progress: Query student progress from RAG
- rocky_quick_answer: Quick music question answering
- rocky_voice_transition: Signal mode transition to/from Rocky
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger("roxy.mcp.rocky")

# Configuration
OLLAMA_BASE = "http://127.0.0.1:11435"
CHROMADB_BASE = "http://localhost:8000"
ROCKY_MODEL = "llama3:8b"  # Default model for Rocky
TIMEOUT = 30  # Music analysis can take longer

TOOLS = {
    "rocky_analyze_audio": {
        "description": "Analyze audio content for music theory elements",
        "parameters": {
            "description": {"type": "string", "required": True, "description": "Description of the audio or musical content"},
            "context": {"type": "string", "default": "", "description": "Additional context (genre, instrument, etc.)"}
        }
    },
    "rocky_explain_concept": {
        "description": "Explain a music theory concept in student-friendly terms",
        "parameters": {
            "concept": {"type": "string", "required": True, "description": "The music concept to explain"},
            "level": {"type": "string", "default": "intermediate", "description": "Student level: beginner|intermediate|advanced"},
            "instrument": {"type": "string", "default": "piano", "description": "Primary instrument context"}
        }
    },
    "rocky_suggest_exercise": {
        "description": "Suggest a practice exercise for skill development",
        "parameters": {
            "skill": {"type": "string", "required": True, "description": "Skill to develop (e.g., 'chord voicings', 'rhythm')"},
            "duration_minutes": {"type": "integer", "default": 15, "description": "Target practice duration"},
            "difficulty": {"type": "string", "default": "medium", "description": "Difficulty: easy|medium|hard"}
        }
    },
    "rocky_generate_accompaniment": {
        "description": "Generate parameters for a backing track / accompaniment",
        "parameters": {
            "key": {"type": "string", "required": True, "description": "Musical key (e.g., 'C major', 'A minor')"},
            "tempo": {"type": "integer", "default": 120, "description": "Tempo in BPM"},
            "style": {"type": "string", "default": "jazz", "description": "Musical style"},
            "bars": {"type": "integer", "default": 8, "description": "Number of bars"}
        }
    },
    "rocky_get_student_progress": {
        "description": "Query student progress and learning history",
        "parameters": {
            "student_id": {"type": "string", "default": "default", "description": "Student identifier"},
            "skill_area": {"type": "string", "default": None, "description": "Specific skill area to query"}
        }
    },
    "rocky_quick_answer": {
        "description": "Get a quick answer to a music question",
        "parameters": {
            "question": {"type": "string", "required": True, "description": "The music question"}
        }
    },
    "rocky_voice_transition": {
        "description": "Signal voice mode transition to/from Rocky personality",
        "parameters": {
            "direction": {"type": "string", "required": True, "description": "Transition direction: to_rocky|from_rocky"},
            "context": {"type": "string", "default": "", "description": "Conversation context to preserve"}
        }
    }
}

# Music theory knowledge base for quick lookups
MUSIC_THEORY_QUICK = {
    "major_scale": "W-W-H-W-W-W-H (Whole-Whole-Half-Whole-Whole-Whole-Half)",
    "minor_scale": "W-H-W-W-H-W-W (Natural minor)",
    "circle_of_fifths": "C-G-D-A-E-B-F#/Gb-Db-Ab-Eb-Bb-F-C",
    "chord_types": {
        "major": "1-3-5",
        "minor": "1-b3-5", 
        "diminished": "1-b3-b5",
        "augmented": "1-3-#5",
        "major7": "1-3-5-7",
        "minor7": "1-b3-5-b7",
        "dominant7": "1-3-5-b7"
    }
}


def _ollama_generate(prompt: str, model: str = ROCKY_MODEL, system: str = None) -> str:
    """Call Ollama for text generation"""
    try:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            data["system"] = system
        
        body = json.dumps(data).encode()
        req = Request(f"{OLLAMA_BASE}/api/generate", data=body, headers={
            "Content-Type": "application/json"
        })
        
        with urlopen(req, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode())
            return result.get("response", "")
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error: {e}"


def _query_chromadb(query: str, collection: str = "rocky_music", n_results: int = 3) -> List[str]:
    """Query ChromaDB for relevant context"""
    try:
        # Use local ChromaDB via file access (faster than HTTP for local)
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        
        client = chromadb.PersistentClient(path=str(Path.home() / ".roxy" / "chroma_db"))
        
        try:
            collection_obj = client.get_collection(collection, embedding_function=DefaultEmbeddingFunction())
            results = collection_obj.query(query_texts=[query], n_results=n_results)
            return results.get("documents", [[]])[0]
        except Exception:
            # Collection might not exist, return empty
            return []
    except Exception as e:
        logger.warning(f"ChromaDB query failed: {e}")
        return []


def handle_tool(name: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Handle MCP tool call"""
    if params is None:
        params = {}
    
    try:
        if name == "rocky_analyze_audio":
            description = params.get("description")
            context = params.get("context", "")
            
            if not description:
                return {"error": "description is required"}
            
            system_prompt = """You are Rocky, an expert music teacher and analyst. 
Analyze the described audio/music content and provide:
1. Key/mode identification
2. Chord progression analysis
3. Rhythm patterns noted
4. Musical style/genre
5. Teaching suggestions for a student studying this piece"""
            
            prompt = f"Analyze this musical content: {description}"
            if context:
                prompt += f"\n\nAdditional context: {context}"
            
            analysis = _ollama_generate(prompt, system=system_prompt)
            
            return {
                "analysis": analysis,
                "model_used": ROCKY_MODEL,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_explain_concept":
            concept = params.get("concept")
            level = params.get("level", "intermediate")
            instrument = params.get("instrument", "piano")
            
            if not concept:
                return {"error": "concept is required"}
            
            # Check quick lookup first
            quick_ref = None
            concept_lower = concept.lower().replace(" ", "_")
            if concept_lower in MUSIC_THEORY_QUICK:
                quick_ref = MUSIC_THEORY_QUICK[concept_lower]
            elif "chord" in concept_lower and "types" in MUSIC_THEORY_QUICK:
                quick_ref = MUSIC_THEORY_QUICK["chord_types"]
            
            # Get RAG context
            rag_context = _query_chromadb(f"music theory {concept}")
            
            system_prompt = f"""You are Rocky, a friendly and knowledgeable music teacher.
Explain concepts clearly for a {level} level student learning {instrument}.
Be encouraging, use examples, and relate to practical playing situations."""
            
            prompt = f"Explain this music concept: {concept}"
            if quick_ref:
                prompt += f"\n\nQuick reference: {quick_ref}"
            if rag_context:
                prompt += f"\n\nRelevant context: {' '.join(rag_context[:2])}"
            
            explanation = _ollama_generate(prompt, system=system_prompt)
            
            return {
                "concept": concept,
                "level": level,
                "instrument": instrument,
                "explanation": explanation,
                "quick_reference": quick_ref,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_suggest_exercise":
            skill = params.get("skill")
            duration = params.get("duration_minutes", 15)
            difficulty = params.get("difficulty", "medium")
            
            if not skill:
                return {"error": "skill is required"}
            
            system_prompt = """You are Rocky, a music practice coach.
Design specific, actionable practice exercises with:
1. Clear objectives
2. Step-by-step instructions
3. Time breakdown
4. Success criteria
5. Variations for different levels"""
            
            prompt = f"""Design a {duration}-minute {difficulty} practice exercise for developing: {skill}
Include specific fingerings, patterns, or techniques where applicable."""
            
            exercise = _ollama_generate(prompt, system=system_prompt)
            
            return {
                "skill": skill,
                "duration_minutes": duration,
                "difficulty": difficulty,
                "exercise": exercise,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_generate_accompaniment":
            key = params.get("key")
            tempo = params.get("tempo", 120)
            style = params.get("style", "jazz")
            bars = params.get("bars", 8)
            
            if not key:
                return {"error": "key is required"}
            
            system_prompt = """You are Rocky, generating accompaniment parameters.
Provide chord progression with:
1. Roman numeral analysis
2. Specific voicings
3. Rhythm pattern notation
4. Bass line suggestion"""
            
            prompt = f"""Generate a {bars}-bar accompaniment in {key} at {tempo} BPM in {style} style.
Format as a chord chart with bar-by-bar breakdown."""
            
            accompaniment = _ollama_generate(prompt, system=system_prompt)
            
            return {
                "key": key,
                "tempo": tempo,
                "style": style,
                "bars": bars,
                "accompaniment": accompaniment,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_get_student_progress":
            student_id = params.get("student_id", "default")
            skill_area = params.get("skill_area")
            
            # Query ChromaDB for student history
            query = f"student {student_id} progress"
            if skill_area:
                query += f" {skill_area}"
            
            context = _query_chromadb(query, collection="student_progress", n_results=5)
            
            return {
                "student_id": student_id,
                "skill_area": skill_area,
                "history": context if context else ["No recorded progress found"],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_quick_answer":
            question = params.get("question")
            
            if not question:
                return {"error": "question is required"}
            
            # Check quick lookups
            quick_ref = None
            q_lower = question.lower()
            for key, value in MUSIC_THEORY_QUICK.items():
                if key.replace("_", " ") in q_lower:
                    quick_ref = value
                    break
            
            system_prompt = "You are Rocky. Give a concise, direct answer to this music question."
            
            prompt = question
            if quick_ref:
                prompt += f" (Reference: {quick_ref})"
            
            answer = _ollama_generate(prompt, system=system_prompt)
            
            return {
                "question": question,
                "answer": answer,
                "quick_reference": quick_ref,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        elif name == "rocky_voice_transition":
            direction = params.get("direction")
            context = params.get("context", "")
            
            if direction not in ("to_rocky", "from_rocky"):
                return {"error": "direction must be 'to_rocky' or 'from_rocky'"}
            
            if direction == "to_rocky":
                greeting = "Hey there! Rocky here, your music buddy. What would you like to learn or practice today?"
            else:
                greeting = "Alright, switching back to ROXY mode. Rocky out!"
            
            return {
                "direction": direction,
                "greeting": greeting,
                "context_preserved": bool(context),
                "context_summary": context[:200] if context else None,
                "mode": "rocky" if direction == "to_rocky" else "roxy",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    except Exception as e:
        logger.error(f"Error in {name}: {e}")
        return {"error": str(e)}


def health_check() -> Dict[str, Any]:
    """Bridge health check for infrastructure monitoring"""
    try:
        # Check Ollama
        req = Request(f"{OLLAMA_BASE}/api/tags")
        with urlopen(req, timeout=5) as response:
            ollama_status = "up"
            models = json.loads(response.read().decode()).get("models", [])
            has_rocky_model = any(m.get("name", "").startswith(ROCKY_MODEL.split(":")[0]) for m in models)
    except Exception:
        ollama_status = "down"
        has_rocky_model = False
    
    return {
        "bridge": "mcp_rocky",
        "status": "healthy" if ollama_status == "up" else "degraded",
        "endpoints": {
            "ollama": {"url": OLLAMA_BASE, "status": ollama_status},
            "rocky_model": {"model": ROCKY_MODEL, "available": has_rocky_model}
        },
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    print("MCP Rocky Bridge - Health Check")
    print(json.dumps(health_check(), indent=2))

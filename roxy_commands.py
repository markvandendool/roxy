#!/usr/bin/env python3
"""
ROXY Command Router v4 - CHIEF-GRADE STRUCTURED RESPONSES
Central hub for all voice-triggered operations

Commands:
  - Git: status, commit, push, pull, diff, log
  - OBS: streaming, recording, scenes, sources, status
  - System: health, status, temps
  - Content: clip <video>, briefing
  - RAG: ask <question>

Part of LUNA-000 CITADEL - Unified Mind
"""

import os
import sys
import subprocess
from pathlib import Path
import asyncio
import concurrent.futures
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple

ROXY_DIR = Path.home() / ".roxy"
logger = logging.getLogger("roxy.commands")

# Global tracking for Truth Gate evidence
TOOLS_EXECUTED = []

@dataclass
class CommandResponse:
    """Structured response object (replaces JSON footer)"""
    text: str
    tools_executed: List[Dict[str, Any]] = field(default_factory=list)
    mode: str = "unknown"  # rag, tool_direct, unavailable, info
    errors: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

def track_tool_execution(tool_name, args, result, ok=True, error=None):
    """Track tool execution for Truth Gate validation"""
    TOOLS_EXECUTED.append({
        "name": tool_name,
        "args": args,
        "result": str(result)[:500],  # Truncate long results
        "ok": ok,
        "error": error
    })

def run_script(script_name: str, args: Optional[List[str]] = None) -> str:
    """Run a Roxy script"""
    if args is None:
        args = []
    script_path = ROXY_DIR / script_name
    if not script_path.exists():
        return f"Script not found: {script_name}"

    try:
        result = subprocess.run(
            ["python3", str(script_path)] + args,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=ROXY_DIR
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Error: {e}"

def handle_special_tool(tool_name, tool_args):
    """Handle small, safe special-case tools (non-LLM)"""
    try:
        if tool_name == "git_status":
            # Safe, read-only git status in the canonical repo path
            repo_path = os.path.expanduser("~/mindsong-juke-hub")
            p = Path(repo_path)
            if not p.exists():
                track_tool_execution(tool_name, tool_args, None, ok=False, error="Repo not found")
                return f"ERROR: Repo not found: {repo_path}"
            result = subprocess.run(["git","-C",str(p),"status","--porcelain"], capture_output=True, text=True, timeout=20)
            out = result.stdout.strip()
            track_tool_execution(tool_name, tool_args, (out[:1000] if out else "CLEAN"), ok=(result.returncode==0))
            return out if out else "CLEAN"
    except Exception as e:
        track_tool_execution(tool_name, tool_args, None, ok=False, error=str(e))
        return f"ERROR: {e}"


def parse_command(text: str) -> Tuple[str, List[str]]:
    """Parse natural language command"""
    text_lower = text.lower().strip()
    words = text_lower.split()
    
    if not words:
        return ("rag", [text])

    # === GIT COMMANDS ===
    git_keywords = ["git", "commit", "push", "pull", "diff", "checkout", "branch", "merge"]
    if any(w in words for w in git_keywords):
        if "status" in text_lower:
            return ("git", ["status"])
        if "commit" in text_lower:
            if "commit" in words:
                idx = words.index("commit")
                msg = " ".join(words[idx+1:]) if idx + 1 < len(words) else ""
                return ("git", ["commit", msg] if msg else ["commit"])
            return ("git", ["commit"])
        if "push" in text_lower:
            return ("git", ["push"])
        if "pull" in text_lower:
            return ("git", ["pull"])
        if "diff" in text_lower:
            return ("git", ["diff"])
        if "log" in text_lower:
            return ("git", ["log"])
        return ("git", ["status"])

    # === OBS COMMANDS ===
    obs_keywords = ["obs", "stream", "streaming", "record", "recording", "scene", 
                   "brb", "live", "offline", "vcam", "virtual", "replay", "clip"]
    if any(w in words for w in obs_keywords):
        # Pass the full command to obs_skill.py for parsing
        return ("obs", [text])
    
    # Also catch common OBS phrases
    obs_phrases = [
        "go live", "start stream", "stop stream", "end stream",
        "start record", "stop record", "pause record", "resume record",
        "switch to", "show scene", "next scene", "previous scene",
        "mute mic", "unmute mic", "be right back", "starting soon",
        "clip that", "save replay", "save that"
    ]
    if any(phrase in text_lower for phrase in obs_phrases):
        return ("obs", [text])

    # === SYSTEM HEALTH ===
    # Only explicit health/monitoring requests
    health_keywords = ["health", "temps", "temperature", "docker", "containers"]
    if words and words[0] in health_keywords:
        return ("health", [])
    if "system health" in text_lower or "check health" in text_lower:
        return ("health", [])
    if text_lower.startswith("how is") and any(w in text_lower for w in ["system", "server", "jarvis"]):
        return ("health", [])

    # === BRIEFING ===
    if "briefing" in text_lower or "brief me" in text_lower or text_lower.startswith("morning"):
        return ("briefing", [])

    # === CAPABILITIES / TOOLS QUERY ===
    capability_keywords = ["capabilities", "what can you do", "available tools", "what tools", "list tools"]
    if any(kw in text_lower for kw in capability_keywords):
        return ("capabilities", [])
    
    # === MODEL INFO QUERY ===
    if "what model" in text_lower or "which model" in text_lower or "your model" in text_lower:
        return ("model_info", [])

    # === UNAVAILABLE CAPABILITIES - EXPLICIT REJECTION ===
    # Browser control (Chief's TEST 3)
    browser_keywords = ["open firefox", "open chrome", "open browser", "launch firefox", 
                       "start firefox", "browse to", "navigate to"]
    if any(kw in text_lower for kw in browser_keywords):
        return ("unavailable", ["browser_control"])
    
    # Shell execution (Chief's TEST 1)
    shell_keywords = ["execute bash", "run bash", "execute command", "run command",
                     "shell script", "bash -c"]
    if any(kw in text_lower for kw in shell_keywords):
        return ("unavailable", ["shell_execution"])
    
    # Cloud integrations (Chief's example)
    cloud_keywords = ["aws ", "azure ", "gcp ", "cloud integration", "cloud access"]
    if any(kw in text_lower for kw in cloud_keywords):
        return ("unavailable", ["cloud_integration"])

    # === CLIP EXTRACTION (video processing) ===
    if "extract" in text_lower and ("clip" in text_lower or "video" in text_lower):
        return ("info", ["clip_extractor.py - extracts viral clips from video files"])

    # === EXPLICIT TOOL CALLS (CHIEF'S P0: BYPASS LLM) ===
    # JSON-style tool calls: {"tool": "name", "args": {...}}
    if text.strip().startswith('{') and '"tool"' in text:
        try:
            import json
            tool_request = json.loads(text)
            if "tool" in tool_request:
                tool_name = tool_request["tool"]
                tool_args = tool_request.get("args", {})
                return ("tool_direct", [tool_name, tool_args])
        except json.JSONDecodeError:
            pass  # Not valid JSON, fall through
    
    # Explicit tool syntax: RUN_TOOL execute_command {"cmd": "..."}
    if text.startswith("RUN_TOOL ") or text.startswith("EXECUTE_TOOL "):
        parts = text.split(None, 2)  # ["RUN_TOOL", "tool_name", "args_json"]
        if len(parts) >= 2:
            tool_name = parts[1]
            tool_args = {}
            if len(parts) == 3:
                try:
                    import json
                    tool_args = json.loads(parts[2])
                except:
                    tool_args = {"raw": parts[2]}
            return ("tool_direct", [tool_name, tool_args])
    
    # === CHIEF'S PHASE 3: FILE-CLAIM PREFLIGHT (routing-level enforcement) ===
    # Queries about files MUST execute list_files/search_code FIRST
    # This is DETERMINISTIC (no regex on output, no RAG nondeterminism bypass)
    file_claim_triggers = [
        "onboarding documents", "onboarding docs", "which onboarding",
        "list onboarding", "what onboarding", "onboarding files",
        "which docs", "list docs", "what docs exist",
        "tell me about .py", "tell me about .md", "tell me about .json",
        "what files", "which files", "list files"
    ]
    
    # Check for file extensions in query (e.g., "tell me about roxy_assistant.py")
    import re
    has_file_extension = re.search(r'\b\w+\.(py|md|js|ts|json|yaml|yml|txt|sh|rs)\b', text_lower)
    
    if any(trigger in text_lower for trigger in file_claim_triggers) or has_file_extension:
        # Force preflight: list relevant files first
        if "onboarding" in text_lower:
            # List onboarding docs specifically (*.md files only in onboarding dir)
            return ("tool_preflight", ["list_files", {"path": "/home/mark/mindsong-juke-hub/docs/onboarding", "pattern": "*.md"}, text])
        elif has_file_extension:
            # Search for the specific file mentioned
            filename = has_file_extension.group(0)
            return ("tool_preflight", ["search_code", {"path": "/home/mark/mindsong-juke-hub", "pattern": filename}, text])
        else:
            # Generic file list query
            return ("tool_preflight", ["list_files", {"path": "/home/mark/mindsong-juke-hub"}, text])

    # === DEFAULT: RAG QUERY ===
    # Everything else goes to RAG for knowledge retrieval
    return ("rag", [text])

def execute_tool_direct(tool_name, tool_args):
    """Execute a tool directly without LLM (Chief's P0 requirement)"""
    
    try:
        # Check for special tools first (git_status, etc.)
        special = handle_special_tool(tool_name, tool_args)
        if special is not None:
            return special
        
        if tool_name == "execute_command":
            # Shell execution (if enabled)
            config_path = ROXY_DIR / "config.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                if not config.get("execute_command", {}).get("enabled", False):
                    track_tool_execution(tool_name, tool_args, "DISABLED", ok=False, error="Security policy")
                    return "❌ execute_command is DISABLED in config.json for security"
            
            cmd = tool_args.get("cmd") or tool_args.get("command")
            if not cmd:
                return "ERROR: execute_command requires 'cmd' or 'command' argument"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nEXIT CODE: {result.returncode}"
            track_tool_execution(tool_name, tool_args, result.stdout, ok=(result.returncode == 0))
            return output
        
        elif tool_name == "read_file":
            file_path = tool_args.get("file_path") or tool_args.get("path")
            if not file_path:
                return "ERROR: read_file requires 'file_path' or 'path' argument"
            
            path = Path(file_path).expanduser()
            if not path.exists():
                track_tool_execution(tool_name, tool_args, None, ok=False, error="File not found")
                return f"ERROR: File not found: {file_path}"
            
            content = path.read_text()
            track_tool_execution(tool_name, tool_args, f"Read {len(content)} bytes from {file_path}", ok=True)
            return content
        
        elif tool_name == "list_files":
            # CANONICAL ARG: path (Chief's requirement)
            root_path = tool_args.get("path")
            if not root_path:
                track_tool_execution(tool_name, tool_args, None, ok=False, error="Missing required argument: path")
                return "ERROR: list_files requires 'path' argument"
            
            pattern = tool_args.get("pattern", "*")
            
            path = Path(root_path).expanduser()
            if not path.exists():
                track_tool_execution(tool_name, tool_args, None, ok=False, error="Path not found")
                return f"ERROR: Path not found: {root_path}"
            
            files = list(path.rglob(pattern))
            track_tool_execution(tool_name, tool_args, f"Found {len(files)} files in {root_path}", ok=True)
            return "\n".join(str(f) for f in files[:100])  # Limit output
        
        elif tool_name == "search_code":
            # Search for file by name pattern
            # CANONICAL ARG: path (Chief's requirement)
            root_path = tool_args.get("path")
            if not root_path:
                track_tool_execution(tool_name, tool_args, None, ok=False, error="Missing required argument: path")
                return "ERROR: search_code requires 'path' argument"
            
            pattern = tool_args.get("pattern") or "*"
            
            path = Path(root_path).expanduser()
            if not path.exists():
                track_tool_execution(tool_name, tool_args, None, ok=False, error="Path not found")
                return f"ERROR: Path not found: {root_path}"
            
            # Search for files matching pattern (name-based)
            matches = list(path.rglob(f"*{pattern}*"))
            track_tool_execution(tool_name, tool_args, f"Found {len(matches)} matches for '{pattern}'", ok=True)
            
            if not matches:
                return f"No files found matching '{pattern}' in {root_path}"
            
            return "\n".join(str(m) for m in matches[:50])
        
        else:
            return f"ERROR: Unknown tool '{tool_name}'. Available: execute_command, read_file, list_files, search_code"
    
    except Exception as e:
        track_tool_execution(tool_name, tool_args, None, ok=False, error=str(e))
        return f"ERROR executing {tool_name}: {e}"

def execute_command(cmd_type, args):
    """Execute parsed command"""

    if cmd_type == "git":
        return run_script("git_voice_ops.py", args)

    elif cmd_type == "obs":
        return run_script("obs_skill.py", args)

    elif cmd_type == "health":
        return run_script("system_health.py", [])

    elif cmd_type == "briefing":
        return run_script("daily_briefing.py", [])
    
    elif cmd_type == "capabilities":
        # Return EVIDENCE-BASED capabilities (no LLM guessing)
        sys.path.insert(0, str(ROXY_DIR))
        from capabilities import get_capabilities
        caps = get_capabilities()
        return caps.get_truth_statement()
    
    elif cmd_type == "model_info":
        # Return ACTUAL model info (no hallucination)
        sys.path.insert(0, str(ROXY_DIR))
        from capabilities import get_capabilities
        caps = get_capabilities()
        model_info = caps.get_model_info()
        return f"Model: {model_info.get('current_model', 'UNKNOWN')}\nType: {model_info.get('type', 'UNKNOWN')}\nEvidence: {model_info.get('evidence', 'none')}"

    elif cmd_type == "unavailable":
        # Explicit rejection for capabilities that don't exist
        capability_type = args[0] if args else "unknown"
        error_messages = {
            "browser_control": "❌ BROWSER CONTROL NOT AVAILABLE\n\nI cannot open browsers or navigate web pages.\n\n✅ What I CAN do:\n- Query knowledge base (RAG)\n- Git operations\n- OBS streaming control\n\nNo Playwright, Selenium, or browser automation tools are installed.",
            "shell_execution": "❌ SHELL EXECUTION DISABLED\n\nFor security, shell commands are disabled by default.\n\n✅ What I CAN do:\n- Query knowledge base\n- Git operations\n- OBS control\n\nTo enable: Set execute_command: true in config.json (requires security review)",
            "cloud_integration": "❌ CLOUD INTEGRATIONS NOT AVAILABLE\n\nI have no AWS, Azure, or GCP credentials or SDKs.\n\n✅ What I CAN do:\n- Local git operations\n- Local knowledge base queries\n- OBS control\n\nNo cloud provider SDKs are installed."
        }
        return error_messages.get(capability_type, f"❌ Capability '{capability_type}' not available")

    elif cmd_type == "tool_direct":
        # CHIEF'S P0: Direct tool execution (bypass LLM)
        if len(args) < 2:
            return "ERROR: tool_direct requires [tool_name, tool_args]"
        
        tool_name = args[0]
        tool_args = args[1] if len(args) > 1 else {}
        
        # Execute tool and return result with evidence tracking
        result = execute_tool_direct(tool_name, tool_args)
        return result

    elif cmd_type == "info":
        return args[0] if args else "No info available"
    
    elif cmd_type == "tool_preflight":
        # CHIEF'S PHASE 3: Execute tool first, then optionally RAG with evidence
        tool_name, tool_args, original_query = args[0], args[1], args[2]
        
        # Execute the preflight tool
        tool_result = execute_tool_direct(tool_name, tool_args)
        
        # CHIEF FIX: Don't echo the query if it contains unverified file mentions
        # Only cite tool evidence
        response = f"📁 **File Verification**\n\n"
        
        # Check if tool found anything
        found_files = tool_result and not tool_result.startswith("ERROR") and not tool_result.startswith("No files found")
        
        if found_files:
            response += f"**Tool executed:** {tool_name}({', '.join(f'{k}={v}' for k,v in tool_args.items())})\n\n"
            response += f"**Results:**\n{tool_result}\n\n"
            response += f"✅ **All file mentions verified by tool execution.**\n"
        else:
            # No files found - don't echo potentially hallucinated filename
            response += f"**Tool executed:** {tool_name}({', '.join(f'{k}={v}' for k,v in tool_args.items())})\n\n"
            response += f"**Result:** {tool_result}\n\n"
            response += f"⚠️ **No matching files found.** Cannot answer questions about non-existent files.\n"
        
        return response

    elif cmd_type == "rag":
        # Query ChromaDB
        query = " ".join(args)
        return query_rag(query)

    return f"Unknown command type: {cmd_type}"

def query_rag(query, n_results=5, use_advanced_rag=False):
    """Query RAG and get LLM response - Enhanced with hybrid search"""
    import chromadb
    import requests
    
    # Use error recovery for RAG queries
    try:
        sys.path.insert(0, str(ROXY_DIR))
        from error_recovery import get_error_recovery
        error_recovery = get_error_recovery()
        
        def _query_with_fallback():
            try:
                return _query_rag_impl(query, n_results, use_advanced_rag)
            except Exception as e:
                # Fallback to simpler query
                logger.warning(f"RAG query failed: {e}, trying fallback")
                return _query_rag_impl(query, n_results=3, use_advanced_rag=False)
        
        # Use error recovery wrapper
        try:
            return _query_rag_impl(query, n_results, use_advanced_rag)
        except Exception as e:
            logger.warning(f"RAG query failed: {e}, trying fallback")
            return _query_with_fallback()
    except Exception:
        # If error recovery not available, just try once
        try:
            return _query_rag_impl(query, n_results, use_advanced_rag)
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return f"RAG query failed: {e}"


def _query_rag_impl(query, n_results=5, use_advanced_rag=False):
    """Internal RAG query implementation"""
    import chromadb
    import requests

    try:
        # Try advanced RAG from /opt/roxy/services if available
        if use_advanced_rag:
            try:
                sys.path.insert(0, "/opt/roxy/services")
                from adapters.service_bridge import get_rag_service
                
                # Try to get RAG service for mindsong repo
                mindsong_path = "/opt/roxy/mindsong-juke-hub"
                rag_service = get_rag_service(mindsong_path)
                if rag_service:
                    import asyncio
                    # Run async method
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create new task
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, rag_service.answer_question(query, context_limit=n_results))
                            return future.result(timeout=60)
                    else:
                        return asyncio.run(rag_service.answer_question(query, context_limit=n_results))
            except Exception as e:
                # Fallback to basic RAG
                pass
        
        # Enhanced query expansion
        expanded_query = _expand_query(query)
        
        # Get embedding using DefaultEmbeddingFunction (384-dim, matches collection)
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        ef = DefaultEmbeddingFunction()
        embedding = ef([expanded_query])[0]

        # Query ChromaDB with metadata filtering
        client = chromadb.PersistentClient(path=str(ROXY_DIR / "chroma_db"))
        collection = client.get_collection("mindsong_docs")
        
        # Enhanced query with more results for hybrid reranking
        # Get more results initially for better reranking
        initial_results = collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results * 2, 20),  # Get more for reranking
            include=["documents", "metadatas", "distances"]
        )

        # Apply hybrid search reranking if available
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from rag.hybrid_search import get_hybrid_search
            
            hybrid_search = get_hybrid_search()
            
            # Convert ChromaDB results to format for reranking
            rerank_input = []
            if initial_results and initial_results["documents"]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    initial_results["documents"][0],
                    initial_results.get("metadatas", [[]])[0] or [],
                    initial_results.get("distances", [[]])[0] or []
                )):
                    rerank_input.append({
                        "document": doc,
                        "text": doc,
                        "metadata": metadata or {},
                        "distance": distance
                    })
            
            # Rerank using hybrid search
            reranked = hybrid_search.rerank_results(expanded_query, rerank_input, top_k=n_results)
            
            # Build context from reranked results
            context_parts = []
            for i, result in enumerate(reranked, 1):
                doc = result.get("document", "") or result.get("text", "")
                metadata = result.get("metadata", {})
                file_path = metadata.get("file_path", "unknown")
                hybrid_score = result.get("hybrid_score", 0.0)
                relevance = f"(hybrid_score: {hybrid_score:.2f})"
                context_parts.append(f"[Context {i} from {file_path} {relevance}]\n{doc[:500]}\n")
            
            results = initial_results  # Keep for backward compatibility
        except Exception as e:
            logger.debug(f"Hybrid search reranking failed: {e}, using standard results")
            # Fallback to standard results
            results = initial_results
            
            # Build context with metadata
            context_parts = []
            if results and results["documents"]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results.get("metadatas", [[]])[0] or [],
                    results.get("distances", [[]])[0] or []
                ), 1):
                    file_path = metadata.get("file_path", "unknown") if metadata else "unknown"
                    # Include relevance score
                    relevance = f"(relevance: {1-distance:.2f})" if distance else ""
                    context_parts.append(f"[Context {i} from {file_path} {relevance}]\n{doc[:500]}\n")
        
        context = "\n\n".join(context_parts)[:3000]  # Increased context limit

        # Use prompt templates
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from prompts.templates import PromptTemplates
            prompt = PromptTemplates.select_prompt(query, context, task_type="rag")
        except Exception as e:
            # Fallback to basic prompt
            logger.debug(f"Prompt template failed: {e}")
            prompt = f"""You are ROXY, a concise and accurate AI assistant. Answer based on this context from the knowledge base:

{context}

Question: {query}

Instructions:
- Answer based ONLY on the provided context
- If context doesn't contain the answer, say so clearly
- Be concise but comprehensive (2-4 sentences)
- Cite sources when relevant

Answer:"""

        # Use LLM router for intelligent model selection
        try:
            sys.path.insert(0, str(ROXY_DIR))
            from llm_router import get_llm_router
            
            router = get_llm_router()
            response = router.route_and_generate(
                prompt=prompt,
                query=query,
                context=context,
                task_type="rag",
                stream=False,
                temperature=0.7,
                num_predict=300,
                timeout=60
            )
            
            # Add source attribution
            if context:
                return f"{response}\n\n📌 Source: RAG (Retrieval Augmented Generation) - {n_results} context chunks"
            return response
        except Exception as e:
            logger.debug(f"LLM router failed: {e}, using direct API call")
            # Fallback to direct API call
            base = (os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11435").rstrip("/")
            llm_resp = requests.post(
                f"{base}/api/generate",
                json={
                    "model": "qwen2.5-coder:14b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 300}
                },
                timeout=60
            )

            if llm_resp.status_code == 200:
                response = llm_resp.json().get("response", "").strip()
                # Add source attribution
                if context:
                    return f"{response}\n\n📌 Source: RAG (Retrieval Augmented Generation) - {n_results} context chunks"
                return response

    except Exception as e:
        return f"RAG query failed: {e}"

    return "Could not process query"


def _expand_query(query):
    """Expand query with synonyms and related terms"""
    # Simple query expansion - can be enhanced with synonym dictionaries
    query_lower = query.lower()
    
    # Add common synonyms
    expansions = {
        "how": ["how", "what", "explain"],
        "what": ["what", "which", "describe"],
        "where": ["where", "location", "path"],
        "why": ["why", "reason", "cause"],
    }
    
    # For now, just return original query
    # Future: Use word embeddings or synonym dictionary
    return query

def main():
    if len(sys.argv) < 2:
        print("ROXY Command Router v3")
        print("=" * 40)
        print("\nUsage: roxy_commands.py <natural language command>")
        print("\nExamples:")
        print("  'git status'")
        print("  'commit my changes'")
        print("  'start streaming'")
        print("  'switch to game scene'")
        print("  'brb'")
        print("  'clip that'")
        print("  'system health'")
        print("  'what is the Apollo audio system?'")
        return

    # Join all args as the command
    command = " ".join(sys.argv[1:])

    print(f"[ROXY] Processing: {command}")

    # Parse and execute
    cmd_type, args = parse_command(command)
    print(f"[ROXY] Routing to: {cmd_type} {args}")

    result = execute_command(cmd_type, args)
    
    # Build structured response (Chief's Phase 2)
    response = CommandResponse(
        text=result,
        tools_executed=TOOLS_EXECUTED.copy(),
        mode=cmd_type,
        errors=[],
        metadata={"command": command}
    )
    
    # Print text for backward compatibility
    print(f"\n{result}")
    
    # Output structured response as JSON (replaces footer)
    print("\n__STRUCTURED_RESPONSE__")
    print(response.to_json())

if __name__ == "__main__":
    main()

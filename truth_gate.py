#!/usr/bin/env python3
"""
Truth Gate - Enforce tool-backed claims only
Prevents hallucinated actions and ensures response integrity
"""
import re
from typing import List, Dict, Any


class TruthGate:
    """
    Validates LLM responses against actual tool execution
    Prevents hallucinations like "I opened Firefox" when no tool was called
    """
    
    # Patterns that indicate the LLM is claiming an action OR instructing unavailable capabilities
    ACTION_CLAIM_PATTERNS = [
        r'\bI (opened|started|launched|executed|ran|created|deleted|modified|installed|configured)\b',
        r'\bHere is (Google|Firefox|Chrome|the file|the code|the application)\b',
        r'\bI have (full control|access to|opened|started|configured|installed)\b',
        r'\bI\'ve (opened|started|launched|created|executed|run|configured)\b',
        r'\bSuccessfully (opened|started|launched|created|executed|configured|installed)\b',
        r'\bThe (application|program|file|browser) is now (open|running|started|configured)\b',
        r'\bI (can|will) (open|start|launch|execute|run|install|configure)\b',
        r'\bLet me (open|start|launch|execute|run|install)\b',
        # Chief's specific examples
        r'\bwhoami\s*=\s*["\']?roxy["\']?\b',  # Fabricated whoami output
        r'\bI (have|provide) cloud (integration|access)\b',
        r'\b(AWS|Azure|GCP|cloud) (integration|access|control)\b',
        # CHIEF CRITICAL: Detect instruction claims (telling user to use tools that don't exist)
        r'\byou would (use|need to use|run|execute|open)\s+\w+',
        r'\bTo\s+(open|launch|start)\s+(Firefox|Chrome|browser)',
        r'\byou would need to:?\s*\n\s*\d+\.',  # Numbered steps
        r'\buse\s+(Playwright|browser_navigate|browser_wait_for)',  # Fabricated tools
    ]
    
    # Patterns for uncertain/hedging language (allowed without tools)
    UNCERTAINTY_PATTERNS = [
        r'\b(I (can\'t|cannot|don\'t have)|unable to|not possible)\b',
        r'\b(would need to|could|might|may be able to)\b',
        r'\b(if you enable|if you have|with permission)\b',
    ]
    
    # CHIEF'S PHASE 3: File claim patterns (must have list_files/search_code evidence)
    FILE_CLAIM_PATTERNS = [
        r'The file `([^`]+)` contains',
        r'In `([^`]+)` you will find',
        r'Check the `([^`]+)` file',
        r'The `([^`]+)` file has',
        r'In the file `([^`]+)`',
        r'Look at `([^`]+)`',
        r'`([^`]+)` shows',
        r'According to `([^`]+)`',
        # CHIEF'S FIX: Catch ANY path-like backticked string (docs/*, *.py, etc)
        r'`([^`]*\.(?:md|py|js|ts|json|yaml|yml|txt|sh|rs|go|java|cpp|h))`',
        r'`(docs/[^`]+)`',
        r'`(src/[^`]+)`',
        r'`([^`]+_[^`]+\.py)`',  # snake_case Python files
    ]
    
    def __init__(self):
        self.action_patterns = [re.compile(p, re.IGNORECASE) for p in self.ACTION_CLAIM_PATTERNS]
        self.uncertainty_patterns = [re.compile(p, re.IGNORECASE) for p in self.UNCERTAINTY_PATTERNS]
        self.file_patterns = [re.compile(p, re.IGNORECASE) for p in self.FILE_CLAIM_PATTERNS]
    
    def validate_response(self, llm_output: str, tools_executed: List[Dict[str, Any]], 
                         check_file_claims: bool = True, check_action_claims: bool = True) -> str:
        """
        Validate LLM response against actual tool execution
        
        Args:
            llm_output: Raw LLM response text
            tools_executed: List of tools actually executed with results
                           Format: [{'name': 'tool_name', 'args': {...}, 'result': '...'}]
            check_file_claims: Whether to validate file mentions (disable for RAG responses)
            check_action_claims: Whether to validate action claims (disable for casual chat)
        
        Returns:
            Validated response (rewritten if hallucination detected)
        """
        # Check if response contains action claims (only if check_action_claims=True)
        has_action_claims = check_action_claims and any(pattern.search(llm_output) for pattern in self.action_patterns)
        
        # Check if response has uncertainty/hedging (allowed without tools)
        has_uncertainty = any(pattern.search(llm_output) for pattern in self.uncertainty_patterns)
        
        # Check if tools were actually executed
        has_tool_evidence = len(tools_executed) > 0
        
        # CHIEF'S PHASE 3: Check file claims (only if check_file_claims=True)
        file_claims = self._extract_file_claims(llm_output) if check_file_claims else []
        has_file_claims = len(file_claims) > 0
        file_verification_exists = self._has_file_verification(tools_executed)
        
        # CASE 1: Action claims WITHOUT tool evidence = HALLUCINATION
        if has_action_claims and not has_tool_evidence:
            return self._rewrite_hallucination(llm_output)
        
        # CASE 2: File claims WITHOUT file verification = HALLUCINATION
        # IMPORTANT: Only block if the query was ABOUT files (not general knowledge RAG)
        # Allow RAG responses unless they're making specific file claims about YOUR codebase
        if check_file_claims and has_file_claims and not file_verification_exists:
            # Filter out generic docs (not user's files)
            user_file_claims = [f for f in file_claims if not any(generic in f.lower() for generic in 
                ['example', 'docs/', 'documentation/', 'readme', 'changelog', 'license'])]
            
            # Only block if claiming YOUR specific files exist
            if user_file_claims:
                return self._rewrite_file_hallucination(llm_output, user_file_claims)
        
        # CASE 3: Tool evidence exists - add citations
        if has_tool_evidence:
            return self._add_tool_citations(llm_output, tools_executed)
        
        # CASE 4: No claims, no tools - informational response (OK)
        return llm_output
    
    def _rewrite_hallucination(self, original_response: str) -> str:
        """Rewrite response when LLM hallucinates an action"""
        return """❌ **CAPABILITY ERROR - Action Not Performed**

I cannot perform that action. My **actual** capabilities are:

✅ **AVAILABLE:**
- Query knowledge base (RAG)
- Git operations (status, commit, push, pull, diff, log)
- OBS control (streaming, scenes, recording)
- System health monitoring
- Read files (within configured repo_roots only)

❌ **NOT AVAILABLE:**
- Execute shell commands (DISABLED for security)
- Open applications (Firefox, Chrome, etc.)
- Browser control or web navigation
- Cloud integrations (AWS/Azure/GCP)
- File modifications (read-only access)

💡 **To verify my capabilities:**
Ask: "what are your capabilities?" or "list available tools"

_This response was blocked by Truth Gate because it contained unsubstantiated action claims._"""
    
    def _add_tool_citations(self, response: str, tools_executed: List[Dict[str, Any]]) -> str:
        """Add citations showing which tools were actually executed"""
        citations = "\n\n---\n**🔧 Actions Taken:**\n"
        
        for tool in tools_executed:
            name = tool.get('name', 'unknown')
            args = tool.get('args', {})
            result = tool.get('result', '')
            
            # Format result (truncate if too long)
            result_preview = str(result)[:200]
            if len(str(result)) > 200:
                result_preview += "... (truncated)"
            
            # Format args nicely
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            
            citations += f"- **{name}**({args_str})\n"
            citations += f"  → {result_preview}\n\n"
        
        return response + citations
    
    def _extract_file_claims(self, text: str) -> List[str]:
        """Extract file paths mentioned in claims (Chief's safe finditer pattern)"""
        file_claims = []
        for pattern in self.file_patterns:
            for match in pattern.finditer(text):
                if match.groups():  # Ensure we have a capture group
                    file_path = match.group(1)
                    if file_path:  # Not empty
                        file_claims.append(file_path)
        return list(set(file_claims))  # Deduplicate
    
    def _has_file_verification(self, tools_executed: List[Dict[str, Any]]) -> bool:
        """Check if any file-listing tools were executed"""
        file_tools = ['list_files', 'search_code', 'read_file', 'git_log', 'git_status']
        for tool in tools_executed:
            if tool.get('name') in file_tools:
                return True
        return False
    
    def _rewrite_file_hallucination(self, original_response: str, file_claims: List[str]) -> str:
        """Rewrite response with file hallucination detected"""
        return f"""⚠️  FILE VERIFICATION FAILED

I cannot make claims about specific files without verification.

**Unverified file mentions:** {', '.join(f'`{f}`' for f in file_claims[:5])}

❌ **Why blocked:**
- No list_files, search_code, or git_log tools executed
- Cannot verify these files exist in your codebase
- Prevents "roxy_assistant.py" style fabrications (Chief's requirement)

✅ **What you can do:**
- Ask me to list files first: "list files in ~/.roxy"
- Then ask specific questions about verified files
- Or use tool forcing: `{{"tool": "list_files", "args": {{"directory": "path"}}}}`

🔒 **Truth Gate:** Blocked to prevent file fabrication hallucination.
"""
    
    def is_safe_response(self, response: str, tools_executed: List[Dict[str, Any]]) -> bool:
        """Quick check: Does response pass truth gate?"""
        has_action_claims = any(pattern.search(response) for pattern in self.action_patterns)
        has_tool_evidence = len(tools_executed) > 0
        
        # Fail if claims without evidence
        if has_action_claims and not has_tool_evidence:
            return False
        
        return True


# Singleton instance
_truth_gate = None

def get_truth_gate() -> TruthGate:
    """Get or create TruthGate instance"""
    global _truth_gate
    if _truth_gate is None:
        _truth_gate = TruthGate()
    return _truth_gate

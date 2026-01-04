#!/usr/bin/env python3
"""
Code Review Skill
=================
RU-012: Built-in Skills Package

Automated code review with structured feedback.
Analyzes git diffs, security issues, style, and best practices.

Features:
- Git diff analysis
- Security pattern detection
- Style guide enforcement
- Complexity metrics
- Improvement suggestions

SKILL_MANIFEST required for dynamic loading.
"""

import json
import re
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# SKILL MANIFEST (Required for skills_registry)
# =============================================================================

SKILL_MANIFEST = {
    "name": "code_review",
    "version": "1.0.0",
    "description": "Automated code review with security, style, and best practice analysis",
    "author": "ROXY",
    "keywords": [
        "code", "review", "diff", "git", "security", "style", "lint",
        "analyze", "audit", "quality", "pr", "pull request", "merge",
        "bug", "vulnerability", "refactor", "improve"
    ],
    "capabilities": [
        "diff_analysis", "security_scan", "style_check",
        "complexity_analysis", "suggestion_generation"
    ],
    "tools": [
        "review_diff", "review_file", "check_security", "analyze_complexity", "suggest_improvements"
    ],
    "dependencies": [],
    "category": "development"
}


# =============================================================================
# Types
# =============================================================================

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueType(Enum):
    SECURITY = "security"
    BUG = "bug"
    STYLE = "style"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"


@dataclass
class ReviewIssue:
    """Code review issue"""
    type: IssueType
    severity: Severity
    line: int
    message: str
    suggestion: str = ""
    code_snippet: str = ""


@dataclass
class ReviewReport:
    """Complete review report"""
    file_path: str
    issues: List[ReviewIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    score: int = 100  # 0-100
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Security Patterns
# =============================================================================

SECURITY_PATTERNS = {
    "python": [
        (r"eval\s*\(", "Avoid eval() - possible code injection", Severity.CRITICAL),
        (r"exec\s*\(", "Avoid exec() - possible code injection", Severity.CRITICAL),
        (r"subprocess\.call\s*\(.+shell\s*=\s*True", "Shell=True with subprocess is dangerous", Severity.HIGH),
        (r"os\.system\s*\(", "Use subprocess instead of os.system", Severity.MEDIUM),
        (r"pickle\.(load|loads)\s*\(", "Pickle can execute arbitrary code", Severity.HIGH),
        (r"yaml\.load\s*\([^)]*\)", "Use yaml.safe_load instead", Severity.HIGH),
        (r"__import__\s*\(", "Dynamic imports can be dangerous", Severity.MEDIUM),
        (r"input\s*\(.+\)\s*$", "Validate user input", Severity.LOW),
        (r"password\s*=\s*['\"]", "Hardcoded password detected", Severity.CRITICAL),
        (r"api_key\s*=\s*['\"]", "Hardcoded API key detected", Severity.CRITICAL),
        (r"secret\s*=\s*['\"]", "Hardcoded secret detected", Severity.CRITICAL),
        (r"requests\.get\(.+verify\s*=\s*False", "SSL verification disabled", Severity.HIGH),
    ],
    "javascript": [
        (r"eval\s*\(", "Avoid eval() - XSS risk", Severity.CRITICAL),
        (r"innerHTML\s*=", "Use textContent instead of innerHTML", Severity.HIGH),
        (r"document\.write\s*\(", "Avoid document.write()", Severity.MEDIUM),
        (r"new\s+Function\s*\(", "Avoid Function constructor", Severity.HIGH),
        (r"\.exec\s*\(", "Validate regex before exec()", Severity.MEDIUM),
        (r"password\s*[=:]\s*['\"]", "Hardcoded password detected", Severity.CRITICAL),
        (r"api[_-]?key\s*[=:]\s*['\"]", "Hardcoded API key detected", Severity.CRITICAL),
        (r"dangerouslySetInnerHTML", "Review dangerouslySetInnerHTML usage", Severity.HIGH),
    ],
    "general": [
        (r"TODO\s*:", "TODO found - review before merge", Severity.INFO),
        (r"FIXME\s*:", "FIXME found - must address", Severity.MEDIUM),
        (r"HACK\s*:", "HACK found - needs cleanup", Severity.MEDIUM),
        (r"XXX\s*:", "XXX marker found", Severity.LOW),
    ]
}


# =============================================================================
# Style Patterns
# =============================================================================

STYLE_PATTERNS = {
    "python": [
        (r"^\s*import \*", "Avoid wildcard imports", Severity.MEDIUM),
        (r"except\s*:", "Avoid bare except clauses", Severity.MEDIUM),
        (r"print\s*\(", "Consider using logging instead of print", Severity.INFO),
        (r"\.format\s*\(", "Consider f-strings for formatting", Severity.INFO),
        (r"== None", "Use 'is None' instead of '== None'", Severity.LOW),
        (r"!= None", "Use 'is not None' instead of '!= None'", Severity.LOW),
        (r"type\s*\(\s*\w+\s*\)\s*==", "Use isinstance() instead of type()", Severity.LOW),
    ],
    "javascript": [
        (r"var\s+", "Use let/const instead of var", Severity.LOW),
        (r"==(?!=)", "Use === instead of ==", Severity.MEDIUM),
        (r"!=(?!=)", "Use !== instead of !=", Severity.MEDIUM),
        (r"console\.log\s*\(", "Remove console.log before production", Severity.INFO),
        (r"debugger\s*;?", "Remove debugger statement", Severity.HIGH),
    ]
}


# =============================================================================
# Analysis Functions
# =============================================================================

def detect_language(content: str, filename: str = "") -> str:
    """Detect programming language from content or filename"""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "javascript",
        ".jsx": "javascript",
        ".tsx": "javascript",
        ".rb": "ruby",
        ".go": "golang",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "cpp",
        ".cs": "csharp",
    }
    
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in ext_map:
            return ext_map[ext]
    
    # Content-based detection
    if "def " in content and "import " in content:
        return "python"
    if "function " in content or "const " in content or "=>" in content:
        return "javascript"
    
    return "general"


def check_security(content: str, language: str = "general") -> List[ReviewIssue]:
    """Check for security issues"""
    issues = []
    lines = content.split("\n")
    
    # Get patterns for language
    patterns = SECURITY_PATTERNS.get(language, []) + SECURITY_PATTERNS.get("general", [])
    
    for i, line in enumerate(lines, 1):
        for pattern, message, severity in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(ReviewIssue(
                    type=IssueType.SECURITY,
                    severity=severity,
                    line=i,
                    message=message,
                    code_snippet=line.strip()[:100]
                ))
    
    return issues


def check_style(content: str, language: str = "general") -> List[ReviewIssue]:
    """Check for style issues"""
    issues = []
    lines = content.split("\n")
    
    patterns = STYLE_PATTERNS.get(language, [])
    
    for i, line in enumerate(lines, 1):
        # Line length
        if len(line) > 120:
            issues.append(ReviewIssue(
                type=IssueType.STYLE,
                severity=Severity.INFO,
                line=i,
                message=f"Line too long ({len(line)} > 120 characters)"
            ))
        
        # Pattern-based checks
        for pattern, message, severity in patterns:
            if re.search(pattern, line):
                issues.append(ReviewIssue(
                    type=IssueType.STYLE,
                    severity=severity,
                    line=i,
                    message=message,
                    code_snippet=line.strip()[:100]
                ))
    
    return issues


def analyze_complexity(content: str, language: str = "python") -> Dict[str, Any]:
    """Analyze code complexity metrics"""
    lines = content.split("\n")
    
    metrics = {
        "total_lines": len(lines),
        "blank_lines": sum(1 for l in lines if not l.strip()),
        "comment_lines": 0,
        "code_lines": 0,
        "function_count": 0,
        "class_count": 0,
        "avg_function_length": 0,
        "max_nesting_depth": 0,
        "complexity_score": "low"
    }
    
    if language == "python":
        comment_pattern = r"^\s*#"
        function_pattern = r"^\s*def\s+"
        class_pattern = r"^\s*class\s+"
    elif language in ["javascript", "typescript"]:
        comment_pattern = r"^\s*//"
        function_pattern = r"(function\s+\w+|=>\s*{|\(\s*\)\s*=>)"
        class_pattern = r"^\s*class\s+"
    else:
        comment_pattern = r"^\s*(#|//)"
        function_pattern = r"(def|function|func)\s+"
        class_pattern = r"class\s+"
    
    current_indent = 0
    max_indent = 0
    function_lines = []
    current_function_lines = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Count indent for nesting
        if stripped:
            indent = len(line) - len(line.lstrip())
            current_indent = indent // 4  # Assume 4-space indent
            max_indent = max(max_indent, current_indent)
        
        # Categorize line
        if not stripped:
            pass  # Already counted blank
        elif re.match(comment_pattern, stripped):
            metrics["comment_lines"] += 1
        else:
            metrics["code_lines"] += 1
        
        # Count structures
        if re.search(function_pattern, line):
            metrics["function_count"] += 1
            if current_function_lines > 0:
                function_lines.append(current_function_lines)
            current_function_lines = 0
        elif metrics["function_count"] > 0 and stripped:
            current_function_lines += 1
        
        if re.search(class_pattern, line):
            metrics["class_count"] += 1
    
    if current_function_lines > 0:
        function_lines.append(current_function_lines)
    
    metrics["max_nesting_depth"] = max_indent
    
    if function_lines:
        metrics["avg_function_length"] = sum(function_lines) / len(function_lines)
    
    # Calculate complexity score
    if metrics["max_nesting_depth"] > 5 or metrics["avg_function_length"] > 50:
        metrics["complexity_score"] = "high"
    elif metrics["max_nesting_depth"] > 3 or metrics["avg_function_length"] > 30:
        metrics["complexity_score"] = "medium"
    else:
        metrics["complexity_score"] = "low"
    
    return metrics


def parse_diff(diff_content: str) -> List[Tuple[str, str, int, str]]:
    """
    Parse git diff into (action, filename, line, content) tuples
    
    Actions: 'add', 'remove', 'context'
    """
    changes = []
    current_file = ""
    line_num = 0
    
    for line in diff_content.split("\n"):
        # File header
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@ "):
            # Parse line numbers: @@ -old,count +new,count @@
            match = re.search(r'\+(\d+)', line)
            if match:
                line_num = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            changes.append(("add", current_file, line_num, line[1:]))
            line_num += 1
        elif line.startswith("-") and not line.startswith("---"):
            changes.append(("remove", current_file, line_num, line[1:]))
        elif not line.startswith("\\"):
            if current_file:
                changes.append(("context", current_file, line_num, line))
            line_num += 1
    
    return changes


def review_diff(diff_content: str) -> Dict:
    """
    Review a git diff.
    
    Args:
        diff_content: Raw git diff output
    
    Returns:
        {success: bool, report: ReviewReport dict, ...}
    """
    try:
        changes = parse_diff(diff_content)
        
        if not changes:
            return {"success": False, "error": "No changes found in diff"}
        
        # Group by file
        files_changed = {}
        for action, filename, line, content in changes:
            if filename not in files_changed:
                files_changed[filename] = {"additions": [], "deletions": [], "all_content": []}
            
            if action == "add":
                files_changed[filename]["additions"].append((line, content))
            elif action == "remove":
                files_changed[filename]["deletions"].append((line, content))
            
            files_changed[filename]["all_content"].append(content)
        
        # Review each file
        all_issues = []
        file_reports = []
        
        for filename, file_changes in files_changed.items():
            # Combine additions for analysis
            added_content = "\n".join([c for _, c in file_changes["additions"]])
            language = detect_language(added_content, filename)
            
            # Security and style checks on new code
            security_issues = check_security(added_content, language)
            style_issues = check_style(added_content, language)
            
            file_issues = security_issues + style_issues
            all_issues.extend(file_issues)
            
            # File report
            file_reports.append({
                "filename": filename,
                "additions": len(file_changes["additions"]),
                "deletions": len(file_changes["deletions"]),
                "issues": len(file_issues),
                "language": language
            })
        
        # Calculate overall score
        score = 100
        for issue in all_issues:
            if issue.severity == Severity.CRITICAL:
                score -= 20
            elif issue.severity == Severity.HIGH:
                score -= 10
            elif issue.severity == Severity.MEDIUM:
                score -= 5
            elif issue.severity == Severity.LOW:
                score -= 2
        
        score = max(0, score)
        
        # Summary
        critical_count = sum(1 for i in all_issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in all_issues if i.severity == Severity.HIGH)
        
        if critical_count > 0:
            summary = f"⚠️ CRITICAL: {critical_count} critical issue(s) found - do not merge"
        elif high_count > 0:
            summary = f"⚠️ HIGH: {high_count} high-severity issue(s) require attention"
        elif all_issues:
            summary = f"✓ {len(all_issues)} minor issue(s) found - review recommended"
        else:
            summary = "✅ No issues detected - ready for review"
        
        return {
            "success": True,
            "score": score,
            "summary": summary,
            "total_issues": len(all_issues),
            "critical_issues": critical_count,
            "high_issues": high_count,
            "files_reviewed": len(files_changed),
            "files": file_reports,
            "issues": [
                {
                    "type": i.type.value,
                    "severity": i.severity.value,
                    "line": i.line,
                    "message": i.message,
                    "snippet": i.code_snippet
                }
                for i in all_issues
            ]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def review_file(file_path: str) -> Dict:
    """
    Review a single file.
    
    Args:
        file_path: Path to file
    
    Returns:
        Review report
    """
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        content = path.read_text()
        language = detect_language(content, str(path))
        
        # Run all checks
        security_issues = check_security(content, language)
        style_issues = check_style(content, language)
        metrics = analyze_complexity(content, language)
        
        all_issues = security_issues + style_issues
        
        # Score
        score = 100
        for issue in all_issues:
            if issue.severity == Severity.CRITICAL:
                score -= 20
            elif issue.severity == Severity.HIGH:
                score -= 10
            elif issue.severity == Severity.MEDIUM:
                score -= 5
            elif issue.severity == Severity.LOW:
                score -= 2
        
        score = max(0, score)
        
        return {
            "success": True,
            "file": str(path),
            "language": language,
            "score": score,
            "metrics": metrics,
            "issue_count": len(all_issues),
            "issues": [
                {
                    "type": i.type.value,
                    "severity": i.severity.value,
                    "line": i.line,
                    "message": i.message,
                    "snippet": i.code_snippet
                }
                for i in all_issues
            ]
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_git_diff(repo_path: str = ".", staged: bool = True) -> Dict:
    """Get git diff from repository"""
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}
        
        return {"success": True, "diff": result.stdout}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def suggest_improvements(content: str) -> Dict:
    """
    Suggest improvements for code.
    
    Returns structured suggestions based on analysis.
    """
    language = detect_language(content)
    metrics = analyze_complexity(content, language)
    issues = check_security(content, language) + check_style(content, language)
    
    suggestions = []
    
    # Complexity-based suggestions
    if metrics["max_nesting_depth"] > 4:
        suggestions.append({
            "category": "complexity",
            "priority": "high",
            "suggestion": "Consider extracting deeply nested code into separate functions"
        })
    
    if metrics["avg_function_length"] > 30:
        suggestions.append({
            "category": "maintainability",
            "priority": "medium",
            "suggestion": "Some functions are quite long - consider breaking them into smaller, focused functions"
        })
    
    if metrics["comment_lines"] < metrics["code_lines"] * 0.1:
        suggestions.append({
            "category": "documentation",
            "priority": "low",
            "suggestion": "Consider adding more comments to explain complex logic"
        })
    
    # Issue-based suggestions
    security_count = sum(1 for i in issues if i.type == IssueType.SECURITY)
    if security_count > 0:
        suggestions.append({
            "category": "security",
            "priority": "critical",
            "suggestion": f"Address {security_count} security issue(s) before deployment"
        })
    
    return {
        "success": True,
        "language": language,
        "metrics": metrics,
        "suggestions": suggestions,
        "suggestion_count": len(suggestions)
    }


# =============================================================================
# MCP Tool Interface
# =============================================================================

TOOLS = {
    "review_diff": {
        "description": "Review a git diff for issues",
        "parameters": {
            "diff_content": {"type": "string", "description": "Git diff output"}
        },
        "required": ["diff_content"]
    },
    "review_file": {
        "description": "Review a single file for issues",
        "parameters": {
            "file_path": {"type": "string", "description": "Path to file"}
        },
        "required": ["file_path"]
    },
    "check_security": {
        "description": "Check code for security vulnerabilities",
        "parameters": {
            "content": {"type": "string", "description": "Code content"},
            "language": {"type": "string", "default": "python"}
        },
        "required": ["content"]
    },
    "analyze_complexity": {
        "description": "Analyze code complexity metrics",
        "parameters": {
            "content": {"type": "string"},
            "language": {"type": "string", "default": "python"}
        },
        "required": ["content"]
    },
    "suggest_improvements": {
        "description": "Get improvement suggestions for code",
        "parameters": {
            "content": {"type": "string", "description": "Code to analyze"}
        },
        "required": ["content"]
    }
}


def handle_tool(name: str, params: Dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "review_diff": lambda p: review_diff(p["diff_content"]),
        "review_file": lambda p: review_file(p["file_path"]),
        "check_security": lambda p: {
            "success": True,
            "issues": [
                {"type": i.type.value, "severity": i.severity.value, "line": i.line, "message": i.message}
                for i in check_security(p["content"], p.get("language", "python"))
            ]
        },
        "analyze_complexity": lambda p: {
            "success": True,
            "metrics": analyze_complexity(p["content"], p.get("language", "python"))
        },
        "suggest_improvements": lambda p: suggest_improvements(p["content"])
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# Query Handler (for router integration)
# =============================================================================

def handle_query(query: str, params: Dict = None) -> Dict:
    """
    Handle a routed query.
    Called by expert_router when this skill is selected.
    """
    params = params or {}
    query_lower = query.lower()
    
    # Check for file path in query
    file_match = re.search(r'[./~][\w/.-]+\.\w+', query)
    
    if "diff" in query_lower or "pr" in query_lower or "pull request" in query_lower:
        if "diff_content" in params:
            return review_diff(params["diff_content"])
        else:
            # Try to get staged diff
            diff_result = get_git_diff()
            if diff_result.get("success") and diff_result.get("diff"):
                return review_diff(diff_result["diff"])
            return {"success": False, "error": "No diff content provided"}
    
    elif file_match:
        return review_file(file_match.group())
    
    elif "security" in query_lower:
        if "content" in params:
            return {
                "success": True,
                "issues": [
                    {"type": i.type.value, "severity": i.severity.value, "message": i.message}
                    for i in check_security(params["content"])
                ]
            }
    
    return {"success": False, "error": "Could not determine review action from query"}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: skill_code_review.py <command> [args]")
        print("Commands: review <file>, diff, suggest <file>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "review" and len(sys.argv) >= 3:
        result = review_file(sys.argv[2])
    elif cmd == "diff":
        diff_result = get_git_diff()
        if diff_result.get("success"):
            result = review_diff(diff_result["diff"])
        else:
            result = diff_result
    elif cmd == "suggest" and len(sys.argv) >= 3:
        content = Path(sys.argv[2]).read_text()
        result = suggest_improvements(content)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))

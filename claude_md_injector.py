#!/usr/bin/env python3
"""
CLAUDE.md Context Injector - Injects project context into prompts
Part of ROXY-AUTONOMOUS-CODING-AGENT-V1 (RCA-006)

Based on Claude Code's CLAUDE.md pattern for project-aware responses.
"""
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger("roxy.claude_md")

MAX_CONTEXT_SIZE = 50 * 1024
DEFAULT_CLAUDE_MD_NAME = "CLAUDE.md"
MAX_DEPTH = 5


@dataclass
class ClaudeContext:
    file_path: str
    content: str
    size_bytes: int
    truncated: bool = False
    sources: List[str] = None
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class ClaudeMDInjector:
    """
    Scans for CLAUDE.md files and injects context into prompts.
    
    Search order:
    1. Current working directory
    2. Parent directories up to MAX_DEPTH
    3. Git root directory
    """
    
    def __init__(self, max_size: int = MAX_CONTEXT_SIZE):
        self.max_size = max_size
        self._cache: dict[str, ClaudeContext] = {}
        self._found_paths: List[str] = []
    
    def find_claude_md(
        self,
        workdir: Optional[str] = None,
        alt_names: Optional[List[str]] = None
    ) -> Optional[ClaudeContext]:
        """
        Find CLAUDE.md file in directory tree.
        
        Args:
            workdir: Starting directory (default: current working dir)
            alt_names: Alternative filenames to search for
            
        Returns:
            ClaudeContext if found, None otherwise
        """
        if workdir is None:
            workdir = os.getcwd()
        
        if alt_names is None:
            alt_names = [DEFAULT_CLAUDE_MD_NAME, "AGENTS.md", ".claude/CLAUDE.md"]
        
        start_path = Path(workdir).resolve()
        
        for search_path in self._get_search_paths(start_path):
            for name in alt_names:
                file_path = search_path / name
                if file_path.exists() and file_path.is_file():
                    return self._read_context(file_path)
        
        return None
    
    def _get_search_paths(self, start_path: Path) -> List[Path]:
        """Get ordered list of directories to search."""
        paths = [start_path]
        
        parent = start_path.parent
        for _ in range(MAX_DEPTH):
            if parent == parent.parent:
                break
            paths.append(parent)
            parent = parent.parent
        
        git_root = self._find_git_root(start_path)
        if git_root and git_root not in paths:
            paths.append(git_root)
        
        return paths
    
    def _find_git_root(self, path: Path) -> Optional[Path]:
        """Find git repository root."""
        current = path
        while True:
            if (current / ".git").exists():
                return current
            if current == current.parent:
                break
            current = current.parent
        return None
    
    def _read_context(self, file_path: Path) -> ClaudeContext:
        """Read and validate CLAUDE.md content."""
        cache_key = str(file_path)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            content = file_path.read_text(encoding='utf-8')
            size = len(content.encode('utf-8'))
            
            truncated = False
            if size > self.max_size:
                content = content[:self.max_size]
                truncated = True
                logger.warning(
                    f"CLAUDE.md truncated from {size} to {self.max_size} bytes"
                )
            
            context = ClaudeContext(
                file_path=str(file_path),
                content=content,
                size_bytes=size if not truncated else self.max_size,
                truncated=truncated,
                sources=[str(file_path)]
            )
            
            self._cache[cache_key] = context
            self._found_paths.append(str(file_path))
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return ClaudeContext(
                file_path=str(file_path),
                content="",
                size_bytes=0
            )
    
    def inject_into_prompt(
        self,
        base_prompt: str,
        workdir: Optional[str] = None,
        section_header: str = "=== PROJECT CONTEXT ==="
    ) -> str:
        """
        Inject CLAUDE.md content into a prompt.
        
        Args:
            base_prompt: Base prompt to inject context into
            workdir: Working directory to search
            section_header: Header for the injected section
            
        Returns:
            Prompt with context injected
        """
        context = self.find_claude_md(workdir)
        
        if not context or not context.content:
            return base_prompt
        
        injected_section = f"""
{section_header}
File: {context.file_path}
{'[TRUNCATED - original was ' + str(context.size_bytes) + ' bytes]' if context.truncated else ''}

{context.content}

=== END PROJECT CONTEXT ==="""

        return base_prompt + injected_section
    
    def get_context_summary(self) -> dict:
        """Get summary of found context files."""
        return {
            "found": len(self._found_paths),
            "paths": self._found_paths,
            "cached": len(self._cache),
            "cache_keys": list(self._cache.keys()),
            "max_size": self.max_size
        }
    
    def clear_cache(self):
        """Clear the context cache."""
        self._cache.clear()
        self._found_paths.clear()


class MultiProjectContext:
    """
    Aggregate context from multiple project directories.
    Useful for monorepo or multi-project setups.
    """
    
    def __init__(self, max_size_per_project: int = MAX_CONTEXT_SIZE):
        self.injector = ClaudeMDInjector(max_size=max_size_per_project)
        self.project_paths: List[str] = []
        self._contexts: List[ClaudeContext] = []
    
    def add_project(self, path: str):
        """Add a project directory to search."""
        if path not in self.project_paths:
            self.project_paths.append(path)
    
    def find_all_contexts(self) -> List[ClaudeContext]:
        """Find CLAUDE.md in all registered projects."""
        self._contexts = []
        
        for project_path in self.project_paths:
            context = self.injector.find_claude_md(project_path)
            if context and context.content:
                self._contexts.append(context)
        
        return self._contexts
    
    def inject_all(
        self,
        base_prompt: str,
        section_header: str = "=== PROJECT CONTEXT ==="
    ) -> str:
        """Inject all found contexts into prompt."""
        contexts = self.find_all_contexts()
        
        if not contexts:
            return base_prompt
        
        if len(contexts) == 1:
            return self.injector.inject_into_prompt(
                base_prompt,
                contexts[0].file_path,
                section_header
            )
        
        sections = []
        for ctx in contexts:
            truncated_note = (
                f" [TRUNCATED - {ctx.size_bytes} bytes]"
                if ctx.truncated else ""
            )
            sections.append(f"""
### From: {ctx.file_path}{truncated_note}

{ctx.content}
""")
        
        injected_section = f"""
{section_header}
Sources: {len(contexts)} project(s)

{"".join(sections)}
=== END PROJECT CONTEXT ==="""
        
        return base_prompt + injected_section


def test_claude_md_injector():
    """Test CLAUDE.md detection and injection."""
    injector = ClaudeMDInjector()
    
    print("Test 1: Finding CLAUDE.md")
    
    test_dirs = [
        "/home/mark/work/mindsong_gh_https_1769765834",
        "/home/mark/.roxy",
        os.getcwd()
    ]
    
    for test_dir in test_dirs:
        print(f"\n  Searching in: {test_dir}")
        context = injector.find_claude_md(test_dir)
        
        if context:
            print(f"    Found: {context.file_path}")
            print(f"    Size: {context.size_bytes} bytes")
            print(f"    Truncated: {context.truncated}")
            print(f"    Preview: {context.content[:200]}...")
        else:
            print(f"    Not found")
    
    print("\n\nTest 2: Context summary")
    summary = injector.get_context_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    print("\n\nTest 3: Inject into prompt")
    base = "What files are in the project?"
    workdir = "/home/mark/work/mindsong_gh_https_1769765834"
    enhanced = injector.inject_into_prompt(base, workdir)
    print(f"Enhanced prompt length: {len(enhanced)} chars")
    print(f"Contains context: {'PROJECT CONTEXT' in enhanced}")


if __name__ == "__main__":
    test_claude_md_injector()

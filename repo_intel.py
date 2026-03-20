#!/usr/bin/env python3
"""
RepoIntel - Repository intelligence index for mindsong-juke-hub.

Builds a RAM-resident index from the mindsong repo:
  - Symbol index: file -> [class, function, const] with line numbers
  - Dependency map: file -> [imports/requires] -> files
  - Test map: test_file -> [tested_file]
  - File ownership: dir -> last modified by ROXY
  - Language stats: extensions -> file counts

Cached at ~/.roxy/repo-intel/{repo_hash}.json
Refresh on: file change, explicit rebuild, or >1hr stale.
"""
import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("roxy.repo_intel")

ROXY_DIR = Path.home() / ".roxy"
CACHE_DIR = ROXY_DIR / "repo-intel"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_REPO = Path.home() / "work" / "mindsong_gh_https_1769765834"

SKIP_DIRS = {
    ".git", ".next", "node_modules", "dist", "build", "__pycache__",
    ".venv", "venv", ".pytest_cache", ".mypy_cache", ".turbo",
    "public/releaseplan", "public/assets", ".claude", "coverage",
}

SKIP_EXTENSIONS = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
                   ".woff", ".woff2", ".ttf", ".mp4", ".webm", ".mp3",
                   ".zip", ".tar", ".gz", ".lock"}

MAX_FILE_SIZE = 512 * 1024


@dataclass
class FileSymbol:
    name: str
    kind: str  # class, function, const, type, method, property
    line: int
    file_path: str = ""
    signature: str = ""
    doc: str = ""


@dataclass
class FileIndex:
    rel_path: str
    size: int
    modified: float
    language: str
    symbols: List[FileSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    tested_by: List[str] = field(default_factory=list)
    last_modified_by: str = ""


@dataclass
class RepoIndex:
    root: str
    root_hash: str
    built_at: float
    file_count: int
    language_stats: Dict[str, int] = field(default_factory=dict)
    files: Dict[str, FileIndex] = field(default_factory=dict)
    symbol_index: Dict[str, List[FileSymbol]] = field(default_factory=dict)
    dependency_map: Dict[str, Set[str]] = field(default_factory=dict)
    test_map: Dict[str, str] = field(default_factory=dict)
    reverse_test_map: Dict[str, List[str]] = field(default_factory=dict)

    def is_stale(self, max_age_sec: float = 3600.0) -> bool:
        return (time.time() - self.built_at) > max_age_sec

    def find_file_with_symbol(self, symbol_name: str) -> List[FileSymbol]:
        results = []
        name_lower = symbol_name.lower()
        for sig_key, symbols in self.symbol_index.items():
            for sym in symbols:
                if name_lower in sym.name.lower():
                    results.append(sym)
        return results

    def find_file(self, filename: str) -> Optional[FileIndex]:
        return self.files.get(filename)

    def find_tests_for_file(self, file_path: str) -> List[str]:
        return self.reverse_test_map.get(file_path, [])

    def get_dependencies(self, file_path: str) -> Set[str]:
        return self.dependency_map.get(file_path, set())

    def get_language_stats(self) -> Dict[str, int]:
        return self.language_stats.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "root_hash": self.root_hash,
            "built_at": self.built_at,
            "file_count": self.file_count,
            "language_stats": self.language_stats,
            "files": {
                k: {
                    "rel_path": v.rel_path,
                    "size": v.size,
                    "modified": v.modified,
                    "language": v.language,
                    "symbols": [
                        {
                            "name": s.name,
                            "kind": s.kind,
                            "line": s.line,
                            "file_path": s.file_path,
                            "signature": s.signature,
                        }
                        for s in v.symbols
                    ],
                    "imports": v.imports,
                    "tested_by": v.tested_by,
                    "last_modified_by": v.last_modified_by,
                }
                for k, v in self.files.items()
            },
            "symbol_index": {
                k: [{
                    "name": s.name,
                    "kind": s.kind,
                    "line": s.line,
                    "file_path": s.file_path,
                    "signature": s.signature,
                }
                    for s in v]
                for k, v in self.symbol_index.items()
            },
            "dependency_map": {k: list(v) for k, v in self.dependency_map.items()},
            "test_map": self.test_map,
            "reverse_test_map": self.reverse_test_map,
        }


class RepoIndexer:
    """Builds RepoIndex from a repository using ripgrep + git."""

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".css": "css",
        ".scss": "scss",
        ".html": "html",
        ".htm": "html",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".rst": "restructuredtext",
        ".txt": "text",
        ".vue": "vue",
        ".svelte": "svelte",
        ".sql": "sql",
        ".graphql": "graphql",
        ".gql": "graphql",
    }

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = (repo_root or DEFAULT_REPO).resolve()
        self.root_hash = hashlib.md5(str(self.repo_root).encode()).hexdigest()[:12]

    def _should_skip_path(self, path: Path) -> bool:
        rel = str(path.relative_to(self.repo_root))
        parts = Path(rel).parts
        for skip in SKIP_DIRS:
            if skip in parts:
                return True
        if path.suffix in SKIP_EXTENSIONS:
            return True
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                return True
        except OSError:
            return True
        return False

    def _rg_search(self, pattern: str, file_pattern: str = ".",
                   flags: str = "", cwd: Optional[Path] = None) -> List[str]:
        """Run ripgrep and return matching lines with relative paths."""
        try:
            cmd = ["rg", "-n"]
            if flags:
                cmd.extend(flags.split())
            cmd.extend(["--color=never", "--line-number", pattern, file_pattern])
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=60,
                cwd=str(cwd or self.repo_root),
            )
            if result.returncode in (0, 1):
                return [
                    line.strip().lstrip("./")
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"ripgrep failed for pattern '{pattern}': {e}")
        return []

    def _get_git_authors(self, file_rel: str) -> str:
        """Get last author who modified this file via git."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%an", "--", file_rel],
                capture_output=True, text=True, timeout=10,
                cwd=str(self.repo_root),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def _detect_language(self, path: Path) -> str:
        ext = path.suffix
        return self.LANGUAGE_EXTENSIONS.get(ext, "unknown")

    def build(self, force: bool = False) -> RepoIndex:
        """Build or load the repository index.

        Uses ripgrep --files for fast file discovery (no Python walk).
        Then extracts symbols/imports in targeted ripgrep passes.
        """
        cache_file = CACHE_DIR / f"{self.root_hash}.json"

        if not force and cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                idx = self._dict_to_index(data)
                if not idx.is_stale(7200):
                    logger.info(f"RepoIntel cache hit: {self.repo_root} ({idx.file_count} files)")
                    return idx
            except Exception as e:
                logger.warning(f"Failed to load RepoIntel cache: {e}")

        logger.info(f"Building RepoIntel index for: {self.repo_root}")
        start = time.time()

        files: Dict[str, FileIndex] = {}
        symbol_index: Dict[str, List[FileSymbol]] = {}
        dependency_map: Dict[str, Set[str]] = {}
        language_stats: Dict[str, int] = {}
        test_map: Dict[str, str] = {}
        reverse_test_map: Dict[str, List[str]] = {}

        RG_EXT_MAP = {
            "python": ["*.py"],
            "typescript": ["*.ts", "*.tsx"],
            "javascript": ["*.js", "*.mjs", "*.cjs"],
            "bash": ["*.sh"],
            "css": ["*.css", "*.scss"],
            "html": ["*.html"],
            "json": ["*.json"],
            "yaml": ["*.yaml", "*.yml"],
            "markdown": ["*.md"],
        }
        MAX_FILES_PER_TYPE = 500
        for lang, globs in RG_EXT_MAP.items():
            count = 0
            for glob in globs:
                try:
                    result = subprocess.run(
                        ["rg", "--files", "--color=never", "-g", glob],
                        capture_output=True, text=True, timeout=15,
                        cwd=str(self.repo_root),
                    )
                    if result.returncode == 0:
                        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
                        for rel in paths:
                            if rel in files or count >= MAX_FILES_PER_TYPE:
                                break
                            try:
                                abs_p = self.repo_root / rel
                                stat = abs_p.stat()
                                if stat.st_size > MAX_FILE_SIZE:
                                    continue
                                language_stats[lang] = language_stats.get(lang, 0) + 1
                                files[rel] = FileIndex(
                                    rel_path=rel,
                                    size=stat.st_size,
                                    modified=stat.st_mtime,
                                    language=lang,
                                    last_modified_by=self._get_git_authors(rel),
                                )
                                count += 1
                            except OSError:
                                continue
                except Exception:
                    pass

        if time.time() - start > 20:
            logger.warning("RepoIntel file discovery taking too long, stopping early")
        else:
            logger.info(f"RepoIntel: discovered {len(files)} files in {time.time()-start:.1f}s")

        if files:
            py_symbols = self._rg_search(
                r"^class \w+|^def \w+|^async def \w+",
                file_pattern=".", flags="-g *.py",
            )
            for line in py_symbols:
                try:
                    rel_path, line_no, content = line.split(":", 2)
                    ln = int(line_no)
                    content = content.strip()
                    if content.startswith("class "):
                        kind, name = "class", content.split("(", 1)[0].replace("class ", "").strip()
                    else:
                        kind, name = "function", content.replace("async def ", "def ", 1).split("(")[0].replace("def ", "").strip()
                    if not name:
                        continue
                    sig_key = name.lower()
                    if sig_key not in symbol_index:
                        symbol_index[sig_key] = []
                    sym = FileSymbol(name=name, kind=kind, line=ln, file_path=rel_path)
                    symbol_index[sig_key].append(sym)
                    if rel_path in files:
                        files[rel_path].symbols.append(sym)
                except (ValueError, IndexError):
                    continue

            py_imports = self._rg_search(
                r"^import |^from ",
                file_pattern=".", flags="-g *.py",
            )
            for line in py_imports:
                try:
                    rel_path, _, content = line.split(":", 2)
                    if rel_path in files:
                        files[rel_path].imports.append(content.strip())
                except ValueError:
                    continue

        for fi in files.values():
            if fi.imports:
                dependency_map[fi.rel_path] = set(fi.imports)

            is_test = ("test" in fi.rel_path.lower() or "/tests/" in fi.rel_path or
                       fi.rel_path.endswith("_test.py") or fi.rel_path.endswith(".test.ts"))
            if is_test:
                base_name = fi.rel_path.rsplit(".", 1)[0]
                base_name = base_name.replace("_test", "").replace(".test", "")
                for f_path in files:
                    ext = f_path.rsplit(".", 1)[-1] if "." in f_path else ""
                    if (f_path.startswith(base_name) and f_path != fi.rel_path
                            and ext in ("ts", "tsx", "js", "jsx", "py")):
                        test_map[fi.rel_path] = f_path
                        if f_path not in reverse_test_map:
                            reverse_test_map[f_path] = []
                        reverse_test_map[f_path].append(fi.rel_path)
                        break

        idx = RepoIndex(
            root=str(self.repo_root),
            root_hash=self.root_hash,
            built_at=time.time(),
            file_count=len(files),
            language_stats=language_stats,
            files=files,
            symbol_index=symbol_index,
            dependency_map=dependency_map,
            test_map=test_map,
            reverse_test_map=reverse_test_map,
        )

        try:
            with open(cache_file, "w") as f:
                json.dump(idx.to_dict(), f)
            logger.info(f"RepoIntel saved: {cache_file} ({len(files)} files, {time.time()-start:.1f}s)")
        except Exception as e:
            logger.warning(f"Failed to save RepoIntel cache: {e}")

        return idx

    def _dict_to_index(self, data: Dict[str, Any]) -> RepoIndex:
        files = {}
        for k, v in data.get("files", {}).items():
            symbols = [FileSymbol(
                name=s["name"], kind=s["kind"], line=s["line"],
                file_path=s.get("file_path", v["rel_path"]),
                signature=s.get("signature", ""), doc=s.get("doc", ""))
                       for s in v.get("symbols", [])]
            files[k] = FileIndex(
                rel_path=v["rel_path"],
                size=v["size"],
                modified=v["modified"],
                language=v["language"],
                symbols=symbols,
                imports=v.get("imports", []),
                tested_by=v.get("tested_by", []),
                last_modified_by=v.get("last_modified_by", ""),
            )

        symbol_index = {}
        for k, v in data.get("symbol_index", {}).items():
            symbol_index[k] = [FileSymbol(
                name=s["name"], kind=s["kind"], line=s["line"],
                file_path=s.get("file_path", ""),
                signature=s.get("signature", ""))
                               for s in v]

        return RepoIndex(
            root=data["root"],
            root_hash=data["root_hash"],
            built_at=data["built_at"],
            file_count=data["file_count"],
            language_stats=data.get("language_stats", {}),
            files=files,
            symbol_index=symbol_index,
            dependency_map={k: set(v) for k, v in data.get("dependency_map", {}).items()},
            test_map=data.get("test_map", {}),
            reverse_test_map={k: v for k, v in data.get("reverse_test_map", {}).items()},
        )


_repo_index: Optional[RepoIndex] = None
_repo_index_root: Optional[str] = None


def get_repo_index(repo_root: Optional[Path] = None, force: bool = False) -> RepoIndex:
    """Get the global RepoIndex instance."""
    global _repo_index, _repo_index_root
    root = str(repo_root or DEFAULT_REPO)
    if _repo_index is None or _repo_index_root != root or (_repo_index and _repo_index.is_stale()):
        indexer = RepoIndexer(repo_root)
        _repo_index = indexer.build(force=force)
        _repo_index_root = root
    return _repo_index


def query_symbol(symbol_name: str, repo_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Find where a symbol is defined across the repo."""
    idx = get_repo_index(repo_root)
    results = []
    for sym in idx.find_file_with_symbol(symbol_name):
        file_info = idx.find_file(sym.file_path) if sym.file_path else None
        if not file_info:
            # Backward-compatible fallback for older cache files that did not
            # persist file_path inside symbol_index entries.
            for candidate in idx.files.values():
                for candidate_sym in candidate.symbols:
                    if candidate_sym.name == sym.name and candidate_sym.line == sym.line:
                        file_info = candidate
                        sym = candidate_sym
                        break
                if file_info:
                    break
        if file_info:
            results.append({
                "symbol": sym.name,
                "kind": sym.kind,
                "file": file_info.rel_path,
                "line": sym.line,
                "signature": sym.signature,
                "language": file_info.language,
            })
    return results


def get_file_context(file_path: str, repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Get file context: symbols, imports, dependencies, tests."""
    idx = get_repo_index(repo_root)
    fi = idx.find_file(file_path)
    if not fi:
        return {}

    return {
        "path": file_path,
        "language": fi.language,
        "size": fi.size,
        "symbols": [
            {"name": s.name, "kind": s.kind, "line": s.line, "signature": s.signature}
            for s in fi.symbols
        ],
        "imports": fi.imports,
        "dependencies": list(idx.get_dependencies(file_path)),
        "tests": idx.find_tests_for_file(file_path),
        "last_modified_by": fi.last_modified_by,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Building RepoIntel index...")
    idx = RepoIndexer().build(force=True)
    print(f"Indexed {idx.file_count} files in {idx.root}")
    print(f"Languages: {idx.language_stats}")
    print(f"Symbols: {len(idx.symbol_index)} unique")
    print(f"Cache: {CACHE_DIR / f'{idx.root_hash}.json'}")

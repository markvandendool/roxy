#!/usr/bin/env python3
"""
Chat Log Parser - Parse Claude Code and Codex chat logs into unified format.

Part of ROXY-CHAT-EXTRACTION-V1 (EXTRACT-001)

Parses:
- ~/.claude/history.jsonl (720+ prompts)
- ~/.codex/history.jsonl (442+ sessions with code blocks)
- ~/.claude/projects/*/*.jsonl (session transcripts)
- ~/.claude/todos/*.json (todo snapshots)
"""

import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, List, Dict, Any


@dataclass
class ConversationTurn:
    """Unified conversation turn format."""
    timestamp: str
    session_id: str
    content: str
    source_file: str
    source_type: str  # claude_history, codex_history, session_transcript, todo
    project: str = ""
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """Extract code blocks with language detection."""
    blocks = []
    # Match ```language\ncode\n``` or ```\ncode\n```
    pattern = r'```(\w*)\n(.*?)```'
    for match in re.finditer(pattern, text, re.DOTALL):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        if code:
            blocks.append({
                'language': lang,
                'code': code,
                'length': len(code)
            })

    # Also match shell commands (lines starting with $, #, or common commands)
    shell_patterns = [
        r'^(\$\s+.+)$',
        r'^(curl\s+.+)$',
        r'^(ssh\s+.+)$',
        r'^(git\s+.+)$',
        r'^(python3?\s+.+)$',
        r'^(bun\s+.+)$',
        r'^(npm\s+.+)$',
        r'^(rsync\s+.+)$',
    ]
    for pattern in shell_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            cmd = match.group(1).strip()
            if cmd and len(cmd) > 10:
                blocks.append({
                    'language': 'shell',
                    'code': cmd,
                    'length': len(cmd)
                })

    return blocks


def parse_claude_history(path: Path) -> Iterator[ConversationTurn]:
    """
    Parse Claude Code history.jsonl

    Format: {"display": "msg", "timestamp": 1767281236394, "project": "/path", "sessionId": "uuid"}
    """
    if not path.exists():
        print(f"  [SKIP] {path} not found", file=sys.stderr)
        return

    print(f"  [PARSE] {path}", file=sys.stderr)
    count = 0

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ts_ms = data.get('timestamp', 0)
                ts_iso = datetime.fromtimestamp(ts_ms / 1000).isoformat() if ts_ms else ""

                content = data.get('display', '')
                if not content:
                    continue

                code_blocks = extract_code_blocks(content)

                yield ConversationTurn(
                    timestamp=ts_iso,
                    session_id=data.get('sessionId', ''),
                    content=content,
                    source_file=str(path),
                    source_type='claude_history',
                    project=data.get('project', ''),
                    code_blocks=code_blocks,
                    metadata={
                        'line_num': line_num,
                        'has_pasted': bool(data.get('pastedContents', {}))
                    }
                )
                count += 1
            except json.JSONDecodeError as e:
                print(f"  [WARN] Line {line_num}: JSON error: {e}", file=sys.stderr)
                continue

    print(f"  [DONE] Parsed {count} entries from Claude history", file=sys.stderr)


def parse_codex_history(path: Path) -> Iterator[ConversationTurn]:
    """
    Parse Codex history.jsonl - rich sessions with full scripts!

    Format: {"session_id": "uuid", "ts": 1767672733, "text": "full content"}
    """
    if not path.exists():
        print(f"  [SKIP] {path} not found", file=sys.stderr)
        return

    print(f"  [PARSE] {path}", file=sys.stderr)
    count = 0

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ts_unix = data.get('ts', 0)
                ts_iso = datetime.fromtimestamp(ts_unix).isoformat() if ts_unix else ""

                content = data.get('text', '')
                if not content:
                    continue

                code_blocks = extract_code_blocks(content)

                # Codex often has entire shell scripts inline
                if content.startswith('#') or content.startswith('set '):
                    # Likely a shell script
                    code_blocks.append({
                        'language': 'shell',
                        'code': content,
                        'length': len(content)
                    })

                yield ConversationTurn(
                    timestamp=ts_iso,
                    session_id=data.get('session_id', ''),
                    content=content,
                    source_file=str(path),
                    source_type='codex_history',
                    project='',
                    code_blocks=code_blocks,
                    metadata={
                        'line_num': line_num,
                        'content_length': len(content)
                    }
                )
                count += 1
            except json.JSONDecodeError as e:
                print(f"  [WARN] Line {line_num}: JSON error: {e}", file=sys.stderr)
                continue

    print(f"  [DONE] Parsed {count} entries from Codex history", file=sys.stderr)


def parse_session_transcript(path: Path) -> Iterator[ConversationTurn]:
    """
    Parse full session transcripts from projects/*.jsonl

    These contain the complete conversation with tool calls and responses.
    """
    if not path.exists():
        return

    print(f"  [PARSE] {path.name}", file=sys.stderr)
    count = 0
    session_id = path.stem  # Use filename as session ID

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)

                # Session transcripts have various formats - extract content
                content = ""
                if isinstance(data, dict):
                    # Could be message, tool_result, etc.
                    if 'content' in data:
                        content = data['content']
                    elif 'message' in data:
                        content = data['message']
                    elif 'text' in data:
                        content = data['text']
                    elif 'result' in data:
                        content = str(data['result'])

                if not content or len(content) < 20:
                    continue

                # Handle content that's a list (multi-part messages)
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and 'text' in part:
                            text_parts.append(part['text'])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = '\n'.join(text_parts)

                if not isinstance(content, str):
                    content = str(content)

                code_blocks = extract_code_blocks(content)

                yield ConversationTurn(
                    timestamp=data.get('timestamp', ''),
                    session_id=session_id,
                    content=content,
                    source_file=str(path),
                    source_type='session_transcript',
                    project=str(path.parent.name),
                    code_blocks=code_blocks,
                    metadata={
                        'line_num': line_num,
                        'role': data.get('role', ''),
                        'type': data.get('type', '')
                    }
                )
                count += 1
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"  [WARN] Line {line_num}: {e}", file=sys.stderr)
                continue

    if count > 0:
        print(f"  [DONE] Parsed {count} entries from {path.name}", file=sys.stderr)


def parse_todo_snapshots(path: Path) -> Iterator[ConversationTurn]:
    """
    Parse todo snapshots from ~/.claude/todos/*.json
    """
    if not path.exists() or not path.is_dir():
        return

    print(f"  [PARSE] Todo snapshots from {path}", file=sys.stderr)
    count = 0

    for todo_file in path.glob('*.json'):
        try:
            with open(todo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            todos = data.get('todos', [])
            if not todos:
                continue

            # Build content from todos
            todo_text = []
            for todo in todos:
                status = todo.get('status', 'pending')
                content = todo.get('content', '')
                marker = '[x]' if status == 'completed' else '[ ]'
                todo_text.append(f"{marker} {content}")

            content = "TODO LIST:\n" + '\n'.join(todo_text)

            yield ConversationTurn(
                timestamp=data.get('timestamp', ''),
                session_id=todo_file.stem,
                content=content,
                source_file=str(todo_file),
                source_type='todo_snapshot',
                project='',
                code_blocks=[],
                metadata={
                    'todo_count': len(todos),
                    'completed': sum(1 for t in todos if t.get('status') == 'completed')
                }
            )
            count += 1
        except Exception as e:
            print(f"  [WARN] {todo_file.name}: {e}", file=sys.stderr)
            continue

    print(f"  [DONE] Parsed {count} todo snapshots", file=sys.stderr)


def parse_all_sources(
    claude_dir: Path = None,
    codex_dir: Path = None,
    limit: int = 0
) -> Iterator[ConversationTurn]:
    """
    Parse all chat log sources.

    Args:
        claude_dir: Path to ~/.claude
        codex_dir: Path to ~/.codex
        limit: Max entries (0 = unlimited)
    """
    claude_dir = claude_dir or Path.home() / '.claude'
    codex_dir = codex_dir or Path.home() / '.codex'

    count = 0

    # 1. Claude history
    print("\n[1/4] Parsing Claude history...", file=sys.stderr)
    for turn in parse_claude_history(claude_dir / 'history.jsonl'):
        yield turn
        count += 1
        if limit and count >= limit:
            return

    # 2. Codex history
    print("\n[2/4] Parsing Codex history...", file=sys.stderr)
    for turn in parse_codex_history(codex_dir / 'history.jsonl'):
        yield turn
        count += 1
        if limit and count >= limit:
            return

    # 3. Session transcripts
    print("\n[3/4] Parsing session transcripts...", file=sys.stderr)
    projects_dir = claude_dir / 'projects'
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for session_file in project_dir.glob('*.jsonl'):
                if 'agent-' in session_file.name:
                    # Skip agent logs for now (subagent output)
                    continue
                for turn in parse_session_transcript(session_file):
                    yield turn
                    count += 1
                    if limit and count >= limit:
                        return

    # 4. Todo snapshots
    print("\n[4/4] Parsing todo snapshots...", file=sys.stderr)
    for turn in parse_todo_snapshots(claude_dir / 'todos'):
        yield turn
        count += 1
        if limit and count >= limit:
            return

    print(f"\n[TOTAL] Parsed {count} conversation turns", file=sys.stderr)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Parse chat logs into unified format')
    parser.add_argument('--output', '-o', default=str(Path.home() / '.roxy/knowledge/parsed_conversations.jsonl'),
                        help='Output JSONL file')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Max entries to parse (0 = unlimited)')
    parser.add_argument('--claude-dir', default=str(Path.home() / '.claude'),
                        help='Claude config directory')
    parser.add_argument('--codex-dir', default=str(Path.home() / '.codex'),
                        help='Codex config directory')

    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== Chat Log Parser ===", file=sys.stderr)
    print(f"Output: {output_path}", file=sys.stderr)
    if args.limit:
        print(f"Limit: {args.limit} entries", file=sys.stderr)

    total_turns = 0
    total_code_blocks = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        for turn in parse_all_sources(
            claude_dir=Path(args.claude_dir),
            codex_dir=Path(args.codex_dir),
            limit=args.limit
        ):
            f.write(json.dumps(turn.to_dict()) + '\n')
            total_turns += 1
            total_code_blocks += len(turn.code_blocks)

    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Total turns: {total_turns}", file=sys.stderr)
    print(f"Total code blocks: {total_code_blocks}", file=sys.stderr)
    print(f"Output file: {output_path}", file=sys.stderr)
    print(f"Output size: {output_path.stat().st_size / 1024 / 1024:.2f} MB", file=sys.stderr)


if __name__ == '__main__':
    main()

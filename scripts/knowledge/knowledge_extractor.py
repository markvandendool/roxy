#!/usr/bin/env python3
"""
Knowledge Extractor - Extract structured knowledge from parsed conversations.

Part of ROXY-CHAT-EXTRACTION-V1 (EXTRACT-002)

Uses:
- Fast regex patterns for explicit knowledge (TODOs, scripts, errors)
- Ollama LLM for nuanced extraction (insights, decisions, architecture)
"""

import json
import re
import sys
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator
import urllib.request
import urllib.error


# Knowledge types
KNOWLEDGE_TYPES = {
    'PLAN': 'Plans, sprints, epics, roadmaps',
    'TODO': 'TODOs, FIXMEs, loose ends, pending work',
    'DECISION': 'Architectural decisions, design choices',
    'SCRIPT': 'Shell scripts, commands, code snippets',
    'PROBLEM': 'Errors, bugs, crashes, issues',
    'SOLUTION': 'Fixes, workarounds, resolutions',
    'INSIGHT': 'Key learnings, realizations, discoveries',
    'ARCHITECTURE': 'System design, patterns, structure',
    'CONFIG': 'Configuration, setup, installation steps',
    'API': 'API endpoints, curl commands, HTTP calls',
}


@dataclass
class Knowledge:
    """Extracted knowledge item."""
    id: str
    type: str
    content: str
    title: str
    confidence: float  # 0.0 - 1.0
    source_file: str
    source_session: str
    timestamp: str
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5
    actionable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Regex patterns for fast extraction
REGEX_PATTERNS = {
    'TODO': [
        (r'TODO[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'FIXME[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'\[ \]\s+(.+?)(?:\n|$)', 0.8),
        (r'(?:need to|should|must)\s+(.+?)(?:\.|$)', 0.6),
        (r'(?:pending|blocked|waiting)[:\s]+(.+?)(?:\n|$)', 0.7),
    ],
    'SCRIPT': [
        (r'```(?:bash|sh|shell)\n(.+?)```', 0.95),
        (r'```\n((?:curl|ssh|git|python|bun|npm|rsync).+?)```', 0.9),
        (r'^\$\s+(.+)$', 0.85),
        (r'^(curl\s+-[A-Za-z]+\s+.+)$', 0.9),
        (r'^(ssh\s+\S+\s+.+)$', 0.85),
    ],
    'PROBLEM': [
        (r'(?:error|ERROR)[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'(?:failed|FAILED)[:\s]+(.+?)(?:\n|$)', 0.85),
        (r'(?:crash|CRASH)[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'(?:bug|BUG)[:\s]+(.+?)(?:\n|$)', 0.85),
        (r'(?:issue|ISSUE)[:\s]+(.+?)(?:\n|$)', 0.7),
    ],
    'SOLUTION': [
        (r'(?:fixed|Fixed|FIXED)[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'(?:resolved|Resolved)[:\s]+(.+?)(?:\n|$)', 0.85),
        (r'(?:the fix|The fix)[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'(?:workaround|Workaround)[:\s]+(.+?)(?:\n|$)', 0.8),
        (r'(?:solution|Solution)[:\s]+(.+?)(?:\n|$)', 0.85),
    ],
    'DECISION': [
        (r'(?:decided|Decided) (?:to )?(.+?)(?:\.|$)', 0.8),
        (r'(?:chose|Chose) (.+?) (?:because|over|instead)', 0.85),
        (r'(?:went with|going with) (.+?)(?:\.|$)', 0.75),
    ],
    'INSIGHT': [
        (r'(?:learned|Learned) that (.+?)(?:\.|$)', 0.8),
        (r'(?:realized|Realized) (.+?)(?:\.|$)', 0.85),
        (r'(?:key insight|Key insight)[:\s]+(.+?)(?:\n|$)', 0.9),
        (r'(?:important|Important)[:\s]+(.+?)(?:\n|$)', 0.7),
    ],
    'API': [
        (r'((?:GET|POST|PUT|DELETE|PATCH)\s+\S+)', 0.9),
        (r'(curl\s+-X\s+\w+\s+.+?)(?:\n|$)', 0.95),
        (r'(?:endpoint|Endpoint)[:\s]+(\S+)', 0.85),
    ],
}

# Tags extraction patterns
TAG_PATTERNS = [
    (r'\b(GPU|gpu|VRAM|vram)\b', 'gpu'),
    (r'\b(ROXY|roxy)\b', 'roxy'),
    (r'\b(SKOREQ|skoreq)\b', 'skoreq'),
    (r'\b(audio|Audio|AUDIO)\b', 'audio'),
    (r'\b(video|Video|VIDEO)\b', 'video'),
    (r'\b(OBS|obs)\b', 'obs'),
    (r'\b(NDI|ndi)\b', 'ndi'),
    (r'\b(Ollama|ollama|OLLAMA)\b', 'ollama'),
    (r'\b(PostgreSQL|postgres|Postgres|POSTGRES)\b', 'postgres'),
    (r'\b(Redis|redis|REDIS)\b', 'redis'),
    (r'\b(Docker|docker|DOCKER)\b', 'docker'),
    (r'\b(SSH|ssh)\b', 'ssh'),
    (r'\b(Mac Studio|macstudio)\b', 'mac-studio'),
    (r'\b(mission|Mission|MISSION)\b', 'mission'),
    (r'\b(pipeline|Pipeline)\b', 'pipeline'),
    (r'\b(RAG|rag|memory)\b', 'rag'),
]


def extract_tags(text: str) -> List[str]:
    """Extract relevant tags from text."""
    tags = set()
    for pattern, tag in TAG_PATTERNS:
        if re.search(pattern, text):
            tags.add(tag)
    return sorted(tags)


def generate_id(content: str, type: str) -> str:
    """Generate unique ID for knowledge item."""
    hash_input = f"{type}:{content[:500]}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:12]


def generate_title(content: str, max_len: int = 80) -> str:
    """Generate a title from content."""
    # Take first line or sentence
    first_line = content.split('\n')[0].strip()
    first_sentence = re.split(r'[.!?]', first_line)[0].strip()

    title = first_sentence if len(first_sentence) < max_len else first_line[:max_len]

    # Clean up
    title = re.sub(r'^[#\-\*\s]+', '', title)
    title = re.sub(r'\s+', ' ', title)

    if len(title) > max_len:
        title = title[:max_len-3] + '...'

    return title or content[:max_len]


def extract_with_regex(
    content: str,
    source_file: str,
    source_session: str,
    timestamp: str
) -> List[Knowledge]:
    """Fast regex-based extraction for explicit patterns."""
    items = []
    seen_hashes = set()

    for knowledge_type, patterns in REGEX_PATTERNS.items():
        for pattern, base_confidence in patterns:
            flags = re.MULTILINE | re.DOTALL if '```' in pattern else re.MULTILINE
            for match in re.finditer(pattern, content, flags):
                extracted = match.group(1).strip()

                # Skip very short or very long extractions
                if len(extracted) < 10 or len(extracted) > 5000:
                    continue

                # Skip duplicates
                content_hash = hashlib.md5(extracted.encode()).hexdigest()
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                # Calculate importance
                importance = 0.5
                if knowledge_type in ('TODO', 'PROBLEM'):
                    importance = 0.7
                if knowledge_type == 'SCRIPT':
                    importance = 0.8
                if 'critical' in extracted.lower() or 'urgent' in extracted.lower():
                    importance = 0.9

                # Determine if actionable
                actionable = knowledge_type in ('TODO', 'PROBLEM', 'SCRIPT')

                tags = extract_tags(extracted)

                item = Knowledge(
                    id=generate_id(extracted, knowledge_type),
                    type=knowledge_type,
                    content=extracted,
                    title=generate_title(extracted),
                    confidence=base_confidence,
                    source_file=source_file,
                    source_session=source_session,
                    timestamp=timestamp,
                    tags=tags,
                    importance=importance,
                    actionable=actionable,
                    metadata={'extraction_method': 'regex'}
                )
                items.append(item)

    return items


# LLM extraction prompt
LLM_EXTRACTION_PROMPT = """Analyze this conversation segment and extract valuable knowledge.

For each distinct piece of knowledge, provide:
1. type: One of PLAN, TODO, DECISION, SCRIPT, PROBLEM, SOLUTION, INSIGHT, ARCHITECTURE, CONFIG, API
2. content: The actual knowledge (full text)
3. title: A short title (max 80 chars)
4. confidence: 1-100 (how confident you are this is valuable)
5. tags: Relevant keywords (gpu, roxy, skoreq, audio, etc.)
6. actionable: true if this requires follow-up action

Focus on:
- Architectural decisions with rationale
- Unfinished work or loose ends
- Key insights and learnings
- Configuration patterns
- Problem-solution pairs

Skip:
- Generic conversation filler
- Duplicate information
- Trivial details

Respond ONLY with valid JSON array:
[
  {"type": "...", "content": "...", "title": "...", "confidence": 85, "tags": [...], "actionable": true},
  ...
]

Conversation segment:
"""


def extract_with_llm(
    content: str,
    source_file: str,
    source_session: str,
    timestamp: str,
    ollama_url: str = "http://127.0.0.1:11435"
) -> List[Knowledge]:
    """LLM-based extraction for nuanced knowledge."""
    items = []

    # Skip if content is too short
    if len(content) < 100:
        return items

    # Truncate if too long
    truncated = content[:8000] if len(content) > 8000 else content

    prompt = LLM_EXTRACTION_PROMPT + truncated

    try:
        payload = json.dumps({
            "model": "qwen2.5:7b",  # Fast model for extraction
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 2000,
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            response_text = result.get('response', '')

            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                extracted_items = json.loads(json_match.group())

                for item in extracted_items:
                    if not isinstance(item, dict):
                        continue

                    knowledge_type = item.get('type', 'INSIGHT').upper()
                    if knowledge_type not in KNOWLEDGE_TYPES:
                        knowledge_type = 'INSIGHT'

                    item_content = item.get('content', '')
                    if not item_content or len(item_content) < 20:
                        continue

                    confidence = item.get('confidence', 70) / 100.0
                    tags = item.get('tags', [])
                    if isinstance(tags, str):
                        tags = [tags]

                    # Add auto-detected tags
                    tags.extend(extract_tags(item_content))
                    tags = sorted(set(tags))

                    knowledge = Knowledge(
                        id=generate_id(item_content, knowledge_type),
                        type=knowledge_type,
                        content=item_content,
                        title=item.get('title', generate_title(item_content)),
                        confidence=confidence,
                        source_file=source_file,
                        source_session=source_session,
                        timestamp=timestamp,
                        tags=tags,
                        importance=confidence,
                        actionable=item.get('actionable', False),
                        metadata={'extraction_method': 'llm'}
                    )
                    items.append(knowledge)

    except urllib.error.URLError as e:
        print(f"  [WARN] LLM unavailable: {e}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"  [WARN] LLM response not valid JSON: {e}", file=sys.stderr)
    except Exception as e:
        print(f"  [WARN] LLM extraction error: {e}", file=sys.stderr)

    return items


def extract_from_conversation(
    turn: Dict[str, Any],
    use_llm: bool = True,
    ollama_url: str = "http://127.0.0.1:11435"
) -> List[Knowledge]:
    """Extract knowledge from a single conversation turn."""
    content = turn.get('content', '')
    source_file = turn.get('source_file', '')
    source_session = turn.get('session_id', '')
    timestamp = turn.get('timestamp', '')

    items = []

    # 1. Fast regex extraction
    items.extend(extract_with_regex(content, source_file, source_session, timestamp))

    # 2. Extract code blocks separately
    for block in turn.get('code_blocks', []):
        code = block.get('code', '')
        lang = block.get('language', 'text')

        if len(code) < 20:
            continue

        item = Knowledge(
            id=generate_id(code, 'SCRIPT'),
            type='SCRIPT',
            content=code,
            title=generate_title(code),
            confidence=0.95,
            source_file=source_file,
            source_session=source_session,
            timestamp=timestamp,
            tags=[lang] + extract_tags(code),
            importance=0.8,
            actionable=True,
            metadata={'extraction_method': 'code_block', 'language': lang}
        )
        items.append(item)

    # 3. LLM extraction for nuanced content (only for longer content)
    if use_llm and len(content) > 500:
        items.extend(extract_with_llm(
            content, source_file, source_session, timestamp, ollama_url
        ))

    return items


def process_conversations(
    input_path: Path,
    output_dir: Path,
    use_llm: bool = True,
    ollama_url: str = "http://127.0.0.1:11435",
    limit: int = 0
) -> Dict[str, int]:
    """Process all conversations and write extracted knowledge."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output files by type
    output_files = {t: open(output_dir / f"extracted_{t}.jsonl", 'w') for t in KNOWLEDGE_TYPES}

    stats = {t: 0 for t in KNOWLEDGE_TYPES}
    stats['total_turns'] = 0
    stats['total_items'] = 0
    seen_ids = set()

    print(f"Processing: {input_path}", file=sys.stderr)
    print(f"LLM: {'enabled' if use_llm else 'disabled'}", file=sys.stderr)

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if limit and line_num > limit:
                break

            if line_num % 100 == 0:
                print(f"  Processed {line_num} turns, extracted {stats['total_items']} items", file=sys.stderr)

            try:
                turn = json.loads(line.strip())
                stats['total_turns'] += 1

                items = extract_from_conversation(turn, use_llm=use_llm, ollama_url=ollama_url)

                for item in items:
                    # Deduplicate
                    if item.id in seen_ids:
                        continue
                    seen_ids.add(item.id)

                    # Write to type-specific file
                    output_files[item.type].write(json.dumps(item.to_dict()) + '\n')
                    stats[item.type] += 1
                    stats['total_items'] += 1

            except Exception as e:
                print(f"  [WARN] Line {line_num}: {e}", file=sys.stderr)
                continue

    # Close all files
    for f in output_files.values():
        f.close()

    return stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract knowledge from parsed conversations')
    parser.add_argument('--input', '-i',
                        default=str(Path.home() / '.roxy/knowledge/parsed_conversations.jsonl'),
                        help='Input JSONL from chat_log_parser.py')
    parser.add_argument('--output-dir', '-o',
                        default=str(Path.home() / '.roxy/knowledge'),
                        help='Output directory')
    parser.add_argument('--no-llm', action='store_true',
                        help='Disable LLM extraction (regex only)')
    parser.add_argument('--ollama-url', default='http://127.0.0.1:11435',
                        help='Ollama API URL')
    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Max turns to process (0 = unlimited)')

    args = parser.parse_args()

    print("=== Knowledge Extractor ===", file=sys.stderr)

    stats = process_conversations(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        use_llm=not args.no_llm,
        ollama_url=args.ollama_url,
        limit=args.limit
    )

    print("\n=== Extraction Summary ===", file=sys.stderr)
    print(f"Total turns processed: {stats['total_turns']}", file=sys.stderr)
    print(f"Total items extracted: {stats['total_items']}", file=sys.stderr)
    print("\nBy type:", file=sys.stderr)
    for t in KNOWLEDGE_TYPES:
        if stats[t] > 0:
            print(f"  {t}: {stats[t]}", file=sys.stderr)


if __name__ == '__main__':
    main()

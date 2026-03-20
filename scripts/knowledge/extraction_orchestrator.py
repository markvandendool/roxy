#!/usr/bin/env python3
"""
Extraction Orchestrator - Main pipeline for chat log knowledge extraction.

Part of ROXY-CHAT-EXTRACTION-V1 (EXTRACT-005)

Entry point: python extraction_orchestrator.py

Pipeline:
1. Parse all chat log sources (chat_log_parser.py)
2. Extract structured knowledge (knowledge_extractor.py)
3. Ingest into RAG brain (knowledge_ingestor.py)
4. Generate actionable reports
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add current directory to path
SCRIPT_DIR = Path(__file__).parent
ROXY_ROOT = Path.home() / ".roxy"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROXY_ROOT))

from chat_log_parser import parse_all_sources, ConversationTurn
from knowledge_extractor import extract_from_conversation, Knowledge
from knowledge_ingestor import KnowledgeIngestor

# Output directories
KNOWLEDGE_DIR = ROXY_ROOT / "knowledge"
REPORTS_DIR = KNOWLEDGE_DIR / "reports"


@dataclass
class PipelineStats:
    """Statistics from the extraction pipeline."""
    conversations_parsed: int = 0
    knowledge_extracted: int = 0
    knowledge_ingested: int = 0
    knowledge_skipped: int = 0
    errors: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_seconds(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversations_parsed": self.conversations_parsed,
            "knowledge_extracted": self.knowledge_extracted,
            "knowledge_ingested": self.knowledge_ingested,
            "knowledge_skipped": self.knowledge_skipped,
            "errors": self.errors,
            "duration_seconds": round(self.duration_seconds, 2),
        }


def progress_bar(current: int, total: int, prefix: str = "", width: int = 40) -> str:
    """Create a text progress bar."""
    if total == 0:
        return f"{prefix} [{'=' * width}] 100%"

    percent = current / total
    filled = int(width * percent)
    bar = '=' * filled + '-' * (width - filled)
    return f"{prefix} [{bar}] {percent*100:.1f}% ({current}/{total})"


def run_pipeline(
    limit: int = 0,
    dry_run: bool = False,
    skip_parsing: bool = False,
    skip_extraction: bool = False,
    skip_ingestion: bool = False,
    skip_reports: bool = False,
    use_llm: bool = False,
    ollama_url: str = "http://localhost:11434",
) -> PipelineStats:
    """
    Run the full extraction pipeline.

    Args:
        limit: Max conversations to process (0 = unlimited)
        dry_run: Don't actually store anything
        skip_parsing: Skip parsing step (use existing parsed file)
        skip_extraction: Skip extraction step (use existing extracted files)
        skip_ingestion: Skip ingestion step
        skip_reports: Skip report generation
        use_llm: Use Ollama LLM for nuanced extraction
        ollama_url: Ollama API URL

    Returns:
        Pipeline statistics
    """
    stats = PipelineStats()
    stats.start_time = time.time()

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    parsed_file = KNOWLEDGE_DIR / "parsed_conversations.jsonl"

    # ==========================================
    # PHASE 1: Parse Chat Logs
    # ==========================================
    if not skip_parsing:
        print("\n" + "=" * 60, file=sys.stderr)
        print("PHASE 1: Parsing Chat Logs", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        with open(parsed_file, 'w', encoding='utf-8') as f:
            for turn in parse_all_sources(limit=limit):
                f.write(json.dumps(turn.to_dict()) + '\n')
                stats.conversations_parsed += 1

                if stats.conversations_parsed % 100 == 0:
                    print(progress_bar(stats.conversations_parsed, limit or 10000, "Parsing"), file=sys.stderr, end='\r')

        print(f"\n[PHASE 1] Parsed {stats.conversations_parsed} conversations", file=sys.stderr)
    else:
        # Count existing parsed conversations
        if parsed_file.exists():
            with open(parsed_file, 'r') as f:
                stats.conversations_parsed = sum(1 for _ in f)
            print(f"[SKIP] Using existing parsed file: {stats.conversations_parsed} conversations", file=sys.stderr)

    # ==========================================
    # PHASE 2: Extract Knowledge
    # ==========================================
    if not skip_extraction:
        print("\n" + "=" * 60, file=sys.stderr)
        print("PHASE 2: Extracting Knowledge", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Read parsed conversations
        conversations = []
        if parsed_file.exists():
            with open(parsed_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            conversations.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

        print(f"[INFO] Processing {len(conversations)} conversations", file=sys.stderr)

        # Extract knowledge
        extracted_by_type: Dict[str, List[Dict]] = {}

        for i, conv in enumerate(conversations):
            # Extract from this conversation
            knowledge_items = extract_from_conversation(
                conv,
                use_llm=use_llm,
                ollama_url=ollama_url,
            )

            for item in knowledge_items:
                k_type = item.type
                if k_type not in extracted_by_type:
                    extracted_by_type[k_type] = []
                extracted_by_type[k_type].append(item.to_dict())
                stats.knowledge_extracted += 1

            if (i + 1) % 50 == 0:
                print(progress_bar(i + 1, len(conversations), "Extracting"), file=sys.stderr, end='\r')

        print(f"\n[PHASE 2] Extracted {stats.knowledge_extracted} knowledge items", file=sys.stderr)

        # Write extracted knowledge by type
        for k_type, items in extracted_by_type.items():
            output_file = KNOWLEDGE_DIR / f"extracted_{k_type}.jsonl"
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in items:
                    f.write(json.dumps(item) + '\n')
            print(f"  [{k_type}]: {len(items)} items -> {output_file.name}", file=sys.stderr)
    else:
        # Count existing extracted knowledge
        for f in KNOWLEDGE_DIR.glob("extracted_*.jsonl"):
            with open(f, 'r') as fh:
                stats.knowledge_extracted += sum(1 for _ in fh)
        print(f"[SKIP] Using existing extracted files: {stats.knowledge_extracted} items", file=sys.stderr)

    # ==========================================
    # PHASE 3: Ingest into RAG Brain
    # ==========================================
    if not skip_ingestion:
        print("\n" + "=" * 60, file=sys.stderr)
        print("PHASE 3: Ingesting into RAG Brain", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        ingestor = KnowledgeIngestor(dry_run=dry_run)
        ingestor.ingest_all(KNOWLEDGE_DIR)

        ingest_stats = ingestor.get_stats()
        stats.knowledge_ingested = ingest_stats['ingested']
        stats.knowledge_skipped = ingest_stats['skipped']
        stats.errors += ingest_stats['errors']

        print(f"[PHASE 3] Ingested: {stats.knowledge_ingested}, Skipped: {stats.knowledge_skipped}", file=sys.stderr)

    # ==========================================
    # PHASE 4: Generate Reports
    # ==========================================
    if not skip_reports:
        print("\n" + "=" * 60, file=sys.stderr)
        print("PHASE 4: Generating Reports", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        generate_loose_ends_report(KNOWLEDGE_DIR, REPORTS_DIR)
        generate_scripts_catalog(KNOWLEDGE_DIR, REPORTS_DIR)
        generate_decisions_log(KNOWLEDGE_DIR, REPORTS_DIR)

        print(f"[PHASE 4] Reports generated in {REPORTS_DIR}", file=sys.stderr)

    stats.end_time = time.time()
    return stats


def generate_loose_ends_report(knowledge_dir: Path, reports_dir: Path):
    """Generate LOOSE_ENDS.md from extracted TODOs."""
    todo_file = knowledge_dir / "extracted_TODO.jsonl"
    output_file = reports_dir / "LOOSE_ENDS.md"

    todos = []
    if todo_file.exists():
        with open(todo_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    todos.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass

    # Sort by importance/confidence
    todos.sort(key=lambda x: (-x.get('importance', 0.5), -x.get('confidence', 0.5)))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Loose Ends & TODOs\n\n")
        f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
        f.write(f"**Total items: {len(todos)}**\n\n")
        f.write("---\n\n")

        # Group by actionable status
        actionable = [t for t in todos if t.get('actionable', False)]
        informational = [t for t in todos if not t.get('actionable', False)]

        if actionable:
            f.write("## Actionable Items\n\n")
            for i, todo in enumerate(actionable[:100], 1):  # Limit to top 100
                f.write(f"### {i}. {todo.get('title', 'Untitled')}\n\n")
                f.write(f"- **Confidence**: {todo.get('confidence', 0):.0%}\n")
                f.write(f"- **Source**: `{todo.get('source_file', 'unknown')}`\n")
                if todo.get('tags'):
                    f.write(f"- **Tags**: {', '.join(todo.get('tags', []))}\n")
                f.write(f"\n{todo.get('content', '')}\n\n")
                f.write("---\n\n")

        if informational:
            f.write("## Informational Items\n\n")
            for i, todo in enumerate(informational[:50], 1):  # Limit to top 50
                f.write(f"### {i}. {todo.get('title', 'Untitled')}\n\n")
                f.write(f"{todo.get('content', '')[:500]}...\n\n")
                f.write("---\n\n")

    print(f"  LOOSE_ENDS.md: {len(todos)} items", file=sys.stderr)


def generate_scripts_catalog(knowledge_dir: Path, reports_dir: Path):
    """Generate SCRIPTS_CATALOG.md from extracted scripts."""
    script_file = knowledge_dir / "extracted_SCRIPT.jsonl"
    output_file = reports_dir / "SCRIPTS_CATALOG.md"

    scripts = []
    if script_file.exists():
        with open(script_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    scripts.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass

    # Sort by confidence
    scripts.sort(key=lambda x: -x.get('confidence', 0.5))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Scripts Catalog\n\n")
        f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
        f.write(f"**Total scripts: {len(scripts)}**\n\n")
        f.write("---\n\n")

        # Table of contents
        f.write("## Table of Contents\n\n")
        for i, script in enumerate(scripts[:50], 1):
            title = script.get('title', 'Untitled')[:50]
            f.write(f"{i}. [{title}](#{i}-{title.lower().replace(' ', '-')[:20]})\n")
        f.write("\n---\n\n")

        # Script entries
        for i, script in enumerate(scripts[:50], 1):
            title = script.get('title', 'Untitled')
            f.write(f"## {i}. {title}\n\n")
            f.write(f"- **Confidence**: {script.get('confidence', 0):.0%}\n")
            f.write(f"- **Source**: `{script.get('source_file', 'unknown')}`\n")
            if script.get('tags'):
                f.write(f"- **Tags**: {', '.join(script.get('tags', []))}\n")
            f.write("\n```bash\n")
            f.write(script.get('content', ''))
            f.write("\n```\n\n")
            f.write("---\n\n")

    print(f"  SCRIPTS_CATALOG.md: {len(scripts)} scripts", file=sys.stderr)


def generate_decisions_log(knowledge_dir: Path, reports_dir: Path):
    """Generate DECISIONS.md from extracted decisions and insights."""
    output_file = reports_dir / "DECISIONS.md"

    items = []

    # Collect decisions
    decision_file = knowledge_dir / "extracted_DECISION.jsonl"
    if decision_file.exists():
        with open(decision_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    item['_category'] = 'DECISION'
                    items.append(item)
                except json.JSONDecodeError:
                    pass

    # Collect insights
    insight_file = knowledge_dir / "extracted_INSIGHT.jsonl"
    if insight_file.exists():
        with open(insight_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    item['_category'] = 'INSIGHT'
                    items.append(item)
                except json.JSONDecodeError:
                    pass

    # Collect architecture notes
    arch_file = knowledge_dir / "extracted_ARCHITECTURE.jsonl"
    if arch_file.exists():
        with open(arch_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    item['_category'] = 'ARCHITECTURE'
                    items.append(item)
                except json.JSONDecodeError:
                    pass

    # Sort by confidence/importance
    items.sort(key=lambda x: (-x.get('importance', 0.5), -x.get('confidence', 0.5)))

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Decisions & Insights Log\n\n")
        f.write(f"*Generated: {datetime.now().isoformat()}*\n\n")
        f.write(f"**Total items: {len(items)}**\n\n")
        f.write("---\n\n")

        # Group by category
        categories = {}
        for item in items:
            cat = item.get('_category', 'OTHER')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        for category in ['DECISION', 'ARCHITECTURE', 'INSIGHT']:
            if category not in categories:
                continue

            f.write(f"## {category.title()}s\n\n")

            for i, item in enumerate(categories[category][:30], 1):
                f.write(f"### {i}. {item.get('title', 'Untitled')}\n\n")
                f.write(f"- **Confidence**: {item.get('confidence', 0):.0%}\n")
                f.write(f"- **Source**: `{item.get('source_file', 'unknown')}`\n")
                if item.get('timestamp'):
                    f.write(f"- **When**: {item.get('timestamp')}\n")
                f.write(f"\n{item.get('content', '')}\n\n")
                f.write("---\n\n")

    print(f"  DECISIONS.md: {len(items)} items", file=sys.stderr)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extraction Orchestrator - Chat Log Knowledge Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with sample
  python extraction_orchestrator.py --limit 100

  # Dry run (don't store)
  python extraction_orchestrator.py --dry-run

  # Skip parsing (use existing parsed file)
  python extraction_orchestrator.py --skip-parsing

  # Use Ollama LLM for better extraction
  python extraction_orchestrator.py --use-llm

  # Run in background
  nohup python extraction_orchestrator.py > extraction.log 2>&1 &
"""
    )

    parser.add_argument('--limit', '-l', type=int, default=0,
                        help='Max conversations to process (0 = unlimited)')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would happen without storing')
    parser.add_argument('--skip-parsing', action='store_true',
                        help='Skip parsing (use existing parsed_conversations.jsonl)')
    parser.add_argument('--skip-extraction', action='store_true',
                        help='Skip extraction (use existing extracted_*.jsonl)')
    parser.add_argument('--skip-ingestion', action='store_true',
                        help='Skip RAG brain ingestion')
    parser.add_argument('--skip-reports', action='store_true',
                        help='Skip report generation')
    parser.add_argument('--use-llm', action='store_true',
                        help='Use Ollama LLM for nuanced extraction')
    parser.add_argument('--ollama-url', default='http://localhost:11434',
                        help='Ollama API URL')
    parser.add_argument('--output', '-o', default=str(KNOWLEDGE_DIR),
                        help='Output directory')

    args = parser.parse_args()

    print("\n" + "=" * 60, file=sys.stderr)
    print("  ROXY-CHAT-EXTRACTION-V1", file=sys.stderr)
    print("  Mine the Goldmine - Chat Log Knowledge Pipeline", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Started: {datetime.now().isoformat()}", file=sys.stderr)
    print(f"  Limit: {'unlimited' if args.limit == 0 else args.limit}", file=sys.stderr)
    print(f"  Dry run: {args.dry_run}", file=sys.stderr)
    print(f"  Use LLM: {args.use_llm}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    try:
        stats = run_pipeline(
            limit=args.limit,
            dry_run=args.dry_run,
            skip_parsing=args.skip_parsing,
            skip_extraction=args.skip_extraction,
            skip_ingestion=args.skip_ingestion,
            skip_reports=args.skip_reports,
            use_llm=args.use_llm,
            ollama_url=args.ollama_url,
        )

        print("\n" + "=" * 60, file=sys.stderr)
        print("  PIPELINE COMPLETE", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"  Duration: {stats.duration_seconds:.1f} seconds", file=sys.stderr)
        print(f"  Conversations parsed: {stats.conversations_parsed}", file=sys.stderr)
        print(f"  Knowledge extracted: {stats.knowledge_extracted}", file=sys.stderr)
        print(f"  Knowledge ingested: {stats.knowledge_ingested}", file=sys.stderr)
        print(f"  Duplicates skipped: {stats.knowledge_skipped}", file=sys.stderr)
        print(f"  Errors: {stats.errors}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        # Output JSON stats
        print(json.dumps(stats.to_dict(), indent=2))

        sys.exit(0 if stats.errors == 0 else 1)

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Pipeline stopped by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

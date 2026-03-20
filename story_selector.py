#!/usr/bin/env python3
"""
Story Selector - Autonomous story selection for ROXY
Finds the next best story to work on based on priority, readiness, and dependencies.
"""
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("roxy.story_selector")

PRIORITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SKOREQ_INDEX = Path.home() / "work" / "mindsong_gh_https_1769765834" / "docs" / "skoreq" / "index.json"


@dataclass
class Story:
    id: str
    title: str
    description: str = ""
    priority: str = "medium"
    points: int = 0
    status: str = "pending"
    epic_id: str = ""
    sprint: str = ""
    files_in_scope: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    plan_id: str = ""
    commit: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class StorySelection:
    story: Story
    score: float
    reasons: List[str] = field(default_factory=list)


class StorySelector:
    """
    Autonomous story selector for ROXY.
    
    Selects the next best story based on:
    - Priority (critical > high > medium > low)
    - Readiness (has files_in_scope, acceptance criteria)
    - Age (older stories get slight boost)
    - Dependencies (stories that unblock others)
    - Active execution filter (skip if already running)
    """
    
    def __init__(self, skoreq_index: Optional[Path] = None, skoreq_root: Optional[Path] = None):
        self.skoreq_index = skoreq_index or SKOREQ_INDEX
        self.skoreq_root = skoreq_root or self.skoreq_index.parent
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 60.0
    
    def _load_index(self, force: bool = False) -> Dict[str, Any]:
        """Load SKOREQ index with caching."""
        now = time.time()
        if not force and (now - self._cache_time) < self._cache_ttl:
            return self._cache
        
        if not self.skoreq_index.exists():
            logger.warning(f"SKOREQ index not found: {self.skoreq_index}")
            return {"plans": []}
        
        try:
            with open(self.skoreq_index) as f:
                data = json.load(f)
            self._cache = data
            self._cache_time = now
            return data
        except Exception as e:
            logger.error(f"Failed to load SKOREQ index: {e}")
            return {"plans": []}
    
    def _load_plan_stories(self, plan: Dict[str, Any]) -> List[Story]:
        """Load stories from a plan's FINAL_PROPOSAL.json."""
        stories = []
        plan_id = plan.get("planId", "")
        plan_path = plan.get("path", "")
        
        if not plan_path:
            return stories
        
        # Paths in index are absolute from repo root, resolve to skoreq_root
        if plan_path.startswith("/"):
            # Extract plan name from path like /docs/skoreq/PLAN-NAME
            parts = Path(plan_path).parts
            if "skoreq" in parts:
                idx = parts.index("skoreq")
                plan_name = parts[idx + 1] if idx + 1 < len(parts) else ""
                proposal_path = self.skoreq_root / plan_name / "04_FINAL_PROPOSAL.json"
            else:
                proposal_path = Path(plan_path) / "04_FINAL_PROPOSAL.json"
        else:
            proposal_path = self.skoreq_root / plan_path / "04_FINAL_PROPOSAL.json"
        
        if not proposal_path.exists():
            return stories
        
        try:
            with open(proposal_path) as f:
                proposal = json.load(f)
            
            for story in proposal.get("stories", []):
                story_obj = Story(
                    id=story.get("id", ""),
                    title=story.get("title", ""),
                    description=story.get("description", ""),
                    priority=story.get("priority", "medium"),
                    points=story.get("points", 0),
                    status=story.get("status", "pending"),
                    epic_id=story.get("epicId", plan_id),
                    sprint=story.get("sprint", ""),
                    files_in_scope=story.get("filesInScope", []),
                    acceptance_criteria=story.get("acceptanceCriteria", []),
                    dependencies=story.get("dependencies", []),
                    created_at=story.get("createdAt"),
                    updated_at=story.get("updatedAt"),
                    plan_id=plan_id,
                    commit=story.get("commit", ""),
                    tags=story.get("tags", []),
                )
                stories.append(story_obj)
        except Exception as e:
            logger.debug(f"Failed to load {proposal_path}: {e}")
        
        return stories
    
    def find_all_stories(self) -> List[Story]:
        """Find all stories from SKOREQ plans."""
        stories = []
        data = self._load_index()
        
        for plan in data.get("plans", []):
            plan_id = plan.get("planId", "")
            plan_status = plan.get("status", "")
            
            if plan_status in ("done", "blocked", "cancelled"):
                continue
            
            plan_stories = self._load_plan_stories(plan)
            stories.extend(plan_stories)
        
        return stories
    
    def _calculate_readiness(self, story: Story) -> float:
        """Calculate story readiness score (0-100)."""
        score = 100.0
        reasons = []
        
        if not story.files_in_scope:
            score -= 20
            reasons.append("no files_in_scope")
        
        if not story.description or len(story.description) < 50:
            score -= 10
            reasons.append("short description")
        
        if not story.acceptance_criteria:
            score -= 15
            reasons.append("no acceptance criteria")
        
        if not story.points:
            score -= 10
            reasons.append("no story points")
        
        if story.dependencies:
            score += 5
            reasons.append(f"has {len(story.dependencies)} dependencies")
        
        return max(0, min(100, score))
    
    def _calculate_priority_score(self, story: Story) -> float:
        """Calculate priority score."""
        base = PRIORITY_ORDER.get(story.priority.lower(), 2) * 25
        
        if story.status == "todo":
            base += 10
        
        age_days = 0
        if story.created_at:
            try:
                created = datetime.fromisoformat(story.created_at.replace("Z", "+00:00"))
                age_days = (datetime.now() - created.replace(tzinfo=None)).days
            except:
                pass
        
        age_bonus = min(age_days * 2, 50)
        
        return base + age_bonus
    
    def _check_dependencies(self, story: Story, all_stories: List[Story]) -> bool:
        """Check if all dependencies are done."""
        if not story.dependencies:
            return True
        
        story_map = {s.id: s for s in all_stories}
        for dep_id in story.dependencies:
            dep = story_map.get(dep_id)
            if not dep or dep.status != "done":
                return False
        return True
    
    def find(
        self,
        active_executions: Optional[List[str]] = None,
        max_results: int = 5,
        min_readiness: float = 30.0,
    ) -> List[StorySelection]:
        """
        Find the best stories to work on.
        
        Args:
            active_executions: List of story IDs currently being executed
            max_results: Maximum number of stories to return
            min_readiness: Minimum readiness score (0-100)
            
        Returns:
            List of StorySelection objects sorted by score
        """
        active_executions = active_executions or []
        all_stories = self.find_all_stories()
        
        candidates = []
        
        for story in all_stories:
            if story.status not in ("todo", "pending"):
                continue
            
            if story.id in active_executions:
                continue
            
            if not self._check_dependencies(story, all_stories):
                continue
            
            readiness = self._calculate_readiness(story)
            if readiness < min_readiness:
                continue
            
            priority_score = self._calculate_priority_score(story)
            total_score = (readiness * 0.6) + (priority_score * 0.4)
            
            reasons = [
                f"readiness={readiness:.0f}",
                f"priority={story.priority}",
            ]
            
            if story.points:
                reasons.append(f"{story.points} pts")
            
            selection = StorySelection(
                story=story,
                score=total_score,
                reasons=reasons,
            )
            candidates.append(selection)
        
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:max_results]
    
    def get_next_story(self, active_executions: Optional[List[str]] = None) -> Optional[Story]:
        """Get the single best story to work on next."""
        selections = self.find(active_executions, max_results=1)
        return selections[0].story if selections else None
    
    def build_envelope(self, story: Story) -> "MissionEnvelope":
        """Build a MissionEnvelope from a Story for mission supervisor."""
        try:
            from mission_supervisor import MissionEnvelope
        except ImportError:
            from dataclasses import dataclass as MissionEnvelope

        goal = f"{story.title}\n\n{story.description}"

        constraints = []
        required_evidence = []
        for ac in story.acceptance_criteria:
            if ac.lower().startswith("must") or ac.lower().startswith("shall"):
                constraints.append(ac)
            else:
                required_evidence.append(ac)

        tool_budget = max(5, (story.points or 3) * 3)

        verification_plan = self._derive_verification_plan(story)

        rollback_command = ""
        if story.commit:
            rollback_command = f"git checkout {story.commit}"

        envelope = MissionEnvelope(
            mission_id=f"mission-{story.id}-{int(time.time())}",
            story_id=story.id,
            story_title=story.title,
            goal=goal,
            constraints=constraints,
            required_evidence=required_evidence,
            tool_budget=tool_budget,
            verification_plan=verification_plan,
            rollback_command=rollback_command,
            files_in_scope=story.files_in_scope,
            max_retries=2,
        )
        return envelope

    CMD_PREFIXES = ("cmd:", "bash:", "shell:")

    SHELL_COMMAND_PATTERNS = (
        "grep", "find", "ls", "cat", "git ", "diff ", "stat ",
        "bun ", "pnpm ", "node ", "npm ", "tsx ", "tsc",
        "vitest", "playwright", "eslint", "npx ", "bunx ",
        "python", "pip3", "pytest", "cargo ", "rustc ",
        "bash ", "sh ", "curl ", "wget ",
    )

    SHELL_COMMAND_STARTERS = (
        "grep ", "find ", "ls ", "cat ", "git ", "diff ", "stat ",
        "bun ", "pnpm ", "node ", "npm ", "tsx ", "tsc",
        "vitest", "playwright", "eslint", "npx ", "bunx ",
        "python", "pip3", "pytest", "cargo ", "rustc ",
        "bash ", "sh ", "curl ", "wget ",
        "pnpm test", "bun test", "npm test",
    )

    def _looks_like_command(self, text: str) -> bool:
        t = text.strip().lower()
        return any(t.startswith(s) for s in self.SHELL_COMMAND_STARTERS)

    def _strip_cmd_prefix(self, step: str) -> str:
        lowered = step.lower().strip()
        for prefix in self.CMD_PREFIXES:
            if lowered.startswith(prefix):
                return step[len(prefix):].strip()
        return step.strip()

    def _extract_embedded_command(self, text: str) -> Optional[str]:
        """Extract a shell command embedded in acceptance criteria text."""
        t = text.strip()
        t_lower = t.lower()

        if any(t_lower.startswith(p) for p in self.SHELL_COMMAND_STARTERS):
            return self._strip_cmd_prefix(t)

        cmd_patterns = [
            r"grep\s+-[A-Za-z]+\s+['\"].*?['\"]",
            r"find\s+[^\n]+(?:\s+-name|\s+-type|\s+-exec|\s+-o|\s+-a|\s+\|)",
            r"(?:bun|pnpm|node|npm|tsx|tsc|vitest|playwright|eslint)\s+[^\n]+",
            r"git\s+(?:status|diff|log|show|checkout|branch)\s+[^\n]+",
            r"python3?\s+[^\n]+",
            r"bash\s+[^\n]+",
            r"[A-Za-z0-9_./-]+\.(?:sh|bash|mjs|ts)\b[^\n]*",
        ]
        for pattern in cmd_patterns:
            import re
            m = re.search(pattern, t, re.IGNORECASE)
            if m:
                cmd = m.group(0).rstrip(".,;:) ").strip()
                if len(cmd) > 4 and (" " in cmd or "/" in cmd):
                    return cmd
        return None

    def _derive_verification_plan(self, story: Story) -> List[str]:
        """
        Build a verification_plan with executable commands.

        Strategy:
        1. Extract explicit cmd:/bash:/shell: prefixed steps from ACs
        2. Extract embedded shell commands from AC text (grep, bun, pnpm, etc.)
        3. Auto-derive commands from files_in_scope using RepoIntel
        4. Fall back to prose "Verify: ..." for prose-only ACs
        """
        plan: List[str] = []
        seen_cmds: Set[str] = set()

        for ac in story.acceptance_criteria:
            ac_stripped = ac.strip()
            ac_lower = ac_stripped.lower()

            if any(ac_lower.startswith(p) for p in ("cmd:", "bash:", "shell:")):
                plan.append(ac_stripped)
                continue

            cmd = self._extract_embedded_command(ac_stripped)
            if cmd:
                normalized = cmd.strip()
                if normalized not in seen_cmds:
                    seen_cmds.add(normalized)
                    plan.append(f"cmd: {normalized}")

        if story.files_in_scope:
            auto_cmds = self._derive_commands_from_files(story)
            for cmd in auto_cmds:
                if cmd not in seen_cmds:
                    seen_cmds.add(cmd)
                    plan.append(f"cmd: {cmd}")

        if not plan:
            for ac in story.acceptance_criteria:
                plan.append(f"Verify: {ac}")

        return plan

    def _derive_commands_from_files(self, story: Story) -> List[str]:
        """Auto-derive verification commands from files_in_scope using RepoIntel."""
        cmds: List[str] = []
        seen: Set[str] = set()

        try:
            from repo_intel import get_file_context
        except Exception:
            return self._derive_commands_fallback(story)

        repo_root = self.skoreq_root.parent
        ts_files: List[str] = []
        test_files: List[str] = []
        shell_files: List[str] = []
        py_files: List[str] = []
        has_typecheck = False
        has_test = False

        for path in story.files_in_scope:
            normalized = path
            if path.startswith("/"):
                try:
                    normalized = str(Path(path).relative_to(repo_root))
                except ValueError:
                    normalized = path

            ext = Path(normalized).suffix.lower()
            if ext in (".ts", ".tsx"):
                ts_files.append(normalized)
                ctx = get_file_context(normalized, repo_root=repo_root) or {}
                for test in (ctx.get("tests") or []):
                    if test not in test_files:
                        test_files.append(test)
            elif ext in (".sh", ".bash"):
                shell_files.append(normalized)
            elif ext == ".py":
                py_files.append(normalized)

        if ts_files:
            test_patterns = [
                ("vitest unit", f"vitest run --reporter=basic {' '.join(ts_files[:3])}" if len(ts_files) <= 3 else "vitest run tests/unit --reporter=basic"),
            ]
            for label, cmd in test_patterns:
                if cmd not in seen:
                    seen.add(cmd)
                    cmds.append(cmd)

            typecheck = "pnpm typecheck"
            if typecheck not in seen:
                seen.add(typecheck)
                cmds.append(typecheck)

            lint_cmd = f"pnpm lint --max-warnings=0 {' '.join(ts_files[:5])}" if ts_files else None
            if lint_cmd and lint_cmd not in seen:
                seen.add(lint_cmd)
                cmds.append(lint_cmd)

        if test_files:
            test_cmd = f"bun test {' '.join(test_files[:3])}"
            if test_cmd not in seen:
                seen.add(test_cmd)
                cmds.append(test_cmd)
            has_test = True

        if shell_files:
            for sf in shell_files[:2]:
                check_cmd = f"bash -n {sf}"
                if check_cmd not in seen:
                    seen.add(check_cmd)
                    cmds.append(check_cmd)

        if py_files:
            test_patterns = [
                f"python3 -m py_compile {' '.join(py_files[:3])}",
                "python3 -m pytest tests/unit -x -q --tb=short" if not has_test else "",
            ]
            for cmd in test_patterns:
                if cmd and cmd not in seen:
                    seen.add(cmd)
                    cmds.append(cmd)

        return cmds

    def _derive_commands_fallback(self, story: Story) -> List[str]:
        """Fallback command derivation without RepoIntel."""
        cmds: List[str] = []
        seen: Set[str] = set()

        for path in story.files_in_scope:
            ext = Path(path).suffix.lower()
            if ext in (".ts", ".tsx"):
                if "pnpm typecheck" not in seen:
                    seen.add("pnpm typecheck")
                    cmds.append("pnpm typecheck")
            elif ext in (".sh", ".bash"):
                cmd = f"bash -n {path}"
                if cmd not in seen:
                    seen.add(cmd)
                    cmds.append(cmd)
            elif ext == ".py":
                cmd = f"python3 -m py_compile {path}"
                if cmd not in seen:
                    seen.add(cmd)
                    cmds.append(cmd)

        return cmds

    def mark_complete(self, story_id: str) -> bool:
        """Mark a story as done in the SKOREQ index."""
        data = self._load_index(force=True)
        updated = False

        for plan in data.get("plans", []):
            plan_path = plan.get("path", "")
            if not plan_path:
                continue

            if plan_path.startswith("/"):
                parts = Path(plan_path).parts
                if "skoreq" in parts:
                    idx = parts.index("skoreq")
                    plan_name = parts[idx + 1] if idx + 1 < len(parts) else ""
                    proposal_path = self.skoreq_root / plan_name / "04_FINAL_PROPOSAL.json"
                else:
                    proposal_path = Path(plan_path) / "04_FINAL_PROPOSAL.json"
            else:
                proposal_path = self.skoreq_root / plan_path / "04_FINAL_PROPOSAL.json"

            if not proposal_path.exists():
                continue

            try:
                with open(proposal_path) as f:
                    proposal = json.load(f)

                for story in proposal.get("stories", []):
                    if story.get("id") == story_id:
                        story["status"] = "done"
                        story["completedAt"] = datetime.now().isoformat()
                        updated = True

                if updated:
                    with open(proposal_path, "w") as f:
                        json.dump(proposal, f, indent=2)
                    logger.info(f"Marked story complete: {story_id}")
                    self._cache_time = 0
                    break

            except Exception as e:
                logger.warning(f"Failed to update story status for {story_id}: {e}")

        return updated

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all story statuses."""
        stories = self.find_all_stories()
        
        by_status = {"done": 0, "in_progress": 0, "todo": 0, "pending": 0, "blocked": 0}
        by_priority = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        total_points = 0
        done_points = 0
        
        for story in stories:
            by_status[story.status] = by_status.get(story.status, 0) + 1
            by_priority[story.priority] = by_priority.get(story.priority, 0) + 1
            total_points += story.points or 0
            if story.status == "done":
                done_points += story.points or 0
        
        return {
            "total_stories": len(stories),
            "by_status": by_status,
            "by_priority": by_priority,
            "total_points": total_points,
            "done_points": done_points,
            "completion_pct": (done_points / total_points * 100) if total_points > 0 else 0,
            "cache_age": time.time() - self._cache_time,
        }


async def test_story_selector():
    """Test the story selector."""
    selector = StorySelector()
    
    print("=== Story Status Summary ===")
    summary = selector.get_status_summary()
    print(f"Total stories: {summary['total_stories']}")
    print(f"By status: {summary['by_status']}")
    print(f"By priority: {summary['by_priority']}")
    print(f"Points: {summary['done_points']}/{summary['total_points']} ({summary['completion_pct']:.1f}%)")
    
    print("\n=== Top Stories ===")
    selections = selector.find(max_results=5)
    for i, sel in enumerate(selections, 1):
        s = sel.story
        print(f"{i}. [{s.priority}] {s.id}: {s.title}")
        print(f"   Score: {sel.score:.1f} | {', '.join(sel.reasons)}")
    
    print("\n=== Next Story ===")
    next_story = selector.get_next_story()
    if next_story:
        print(f"Next: {next_story.id} - {next_story.title}")
    else:
        print("No stories available")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_story_selector())

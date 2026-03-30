"""
Tool Failure Learning Loop

AAA Quality Implementation: Law 0 Reuse - Extends tool_retry.py

This module extends ROXY's tool_retry.py with learning capabilities:
- Pattern → fix mapping with root-cause tracking
- Automatic recipe generation from failures
- Success rate improvement over time

Usage:
    from learning_loop import LearningLoop, record_failure, get_fix_recipe
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.learning_loop")

ROXY_ROOT = Path.home() / ".roxy"


@dataclass
class FailurePattern:
    """Represents a failure pattern with fix recipes."""
    pattern_id: str
    error_type: str
    error_message: str
    tool_name: str
    command_hint: str
    occurrences: int = 0
    successful_fixes: int = 0
    recipes: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    success_rate: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "tool_name": self.tool_name,
            "command_hint": self.command_hint,
            "occurrences": self.occurrences,
            "successful_fixes": self.successful_fixes,
            "recipes": self.recipes,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "success_rate": self.success_rate,
        }


@dataclass
class FixRecipe:
    """A fix recipe for a failure pattern."""
    pattern_id: str
    strategy: str
    command: str
    description: str
    success_count: int = 0
    failure_count: int = 0
    last_used: str = ""
    
    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "strategy": self.strategy,
            "command": self.command,
            "description": self.description,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used,
        }


class LearningLoop:
    """
    Learning loop for tool failures.
    
    Tracks failure patterns and fix recipes, improving success rate
    over time by learning from repeated failures.
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    """
    
    def __init__(self, data_file: Optional[Path] = None):
        """
        Initialize learning loop.
        
        Args:
            data_file: Path to persistence file
        """
        self.data_file = data_file or (ROXY_ROOT / "data" / "learning_loop.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.patterns: dict[str, FailurePattern] = {}
        self.recipes: dict[str, list[FixRecipe]] = defaultdict(list)
        self._load()
        
        logger.info(f"LearningLoop initialized: {len(self.patterns)} patterns")
    
    def _load(self) -> None:
        """Load patterns from disk."""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            self.patterns = {
                k: FailurePattern(**v) 
                for k, v in data.get("patterns", {}).items()
            }
            self.recipes = {
                k: [FixRecipe(**r) for r in v]
                for k, v in data.get("recipes", {}).items()
            }
        except Exception as e:
            logger.warning(f"Could not load learning data: {e}")
    
    def _save(self) -> None:
        """Save patterns to disk."""
        try:
            data = {
                "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
                "recipes": {k: [r.to_dict() for r in v] for k, v in self.recipes.items()},
                "last_updated": datetime.utcnow().isoformat(),
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save learning data: {e}")
    
    def _generate_pattern_id(
        self,
        tool_name: str,
        error_type: str,
        command_hint: str,
    ) -> str:
        """Generate a stable pattern ID."""
        import hashlib
        key = f"{tool_name}:{error_type}:{command_hint[:50]}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def record_failure(
        self,
        tool_name: str,
        error_type: str,
        error_message: str,
        command_hint: str = "",
        proposed_fix: Optional[str] = None,
    ) -> FailurePattern:
        """
        Record a tool failure.
        
        Args:
            tool_name: Name of the failed tool
            error_type: Type of error (timeout, auth, etc.)
            error_message: Full error message
            command_hint: Hint of the command that failed
            proposed_fix: Optional fix strategy
            
        Returns:
            FailurePattern that was recorded
        """
        pattern_id = self._generate_pattern_id(tool_name, error_type, command_hint)
        now = datetime.utcnow().isoformat()
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = now
            pattern.error_message = error_message[:500]  # Truncate
            
            if proposed_fix and proposed_fix not in pattern.recipes:
                pattern.recipes.append(proposed_fix)
        else:
            pattern = FailurePattern(
                pattern_id=pattern_id,
                error_type=error_type,
                error_message=error_message[:500],
                tool_name=tool_name,
                command_hint=command_hint[:100],
                occurrences=1,
                first_seen=now,
                last_seen=now,
                recipes=[proposed_fix] if proposed_fix else [],
            )
            self.patterns[pattern_id] = pattern
        
        self._save()
        
        logger.info(
            f"Recorded failure: pattern={pattern_id}, "
            f"tool={tool_name}, occurrences={pattern.occurrences}"
        )
        
        return pattern
    
    def record_success(
        self,
        pattern_id: str,
        recipe_strategy: str,
    ) -> None:
        """
        Record a successful fix for a pattern.
        
        Args:
            pattern_id: Pattern that was fixed
            recipe_strategy: Strategy that worked
        """
        if pattern_id not in self.patterns:
            logger.warning(f"Unknown pattern: {pattern_id}")
            return
        
        pattern = self.patterns[pattern_id]
        pattern.successful_fixes += 1
        pattern.success_rate = pattern.successful_fixes / pattern.occurrences
        
        # Update recipe stats
        for recipe in self.recipes.get(pattern_id, []):
            if recipe.strategy == recipe_strategy:
                recipe.success_count += 1
                recipe.last_used = datetime.utcnow().isoformat()
        
        self._save()
        
        logger.info(
            f"Fix success: pattern={pattern_id}, "
            f"strategy={recipe_strategy}, "
            f"success_rate={pattern.success_rate:.2f}"
        )
    
    def get_fix_recipe(
        self,
        tool_name: str,
        error_type: str,
        command_hint: str = "",
    ) -> Optional[FixRecipe]:
        """
        Get the best fix recipe for a failure.
        
        Args:
            tool_name: Name of the failed tool
            error_type: Type of error
            command_hint: Hint of the command
            
        Returns:
            Best FixRecipe if found, None otherwise
        """
        pattern_id = self._generate_pattern_id(tool_name, error_type, command_hint)
        
        if pattern_id not in self.patterns:
            return None
        
        recipes = self.recipes.get(pattern_id, [])
        if not recipes:
            return None
        
        # Return best recipe by success rate
        return max(recipes, key=lambda r: r.success_count / max(r.success_count + r.failure_count, 1))
    
    def add_recipe(
        self,
        pattern_id: str,
        strategy: str,
        command: str,
        description: str,
    ) -> FixRecipe:
        """
        Add a fix recipe to a pattern.
        
        Args:
            pattern_id: Pattern to add recipe to
            strategy: Retry strategy name
            command: Fix command
            description: Human-readable description
            
        Returns:
            FixRecipe that was added
        """
        recipe = FixRecipe(
            pattern_id=pattern_id,
            strategy=strategy,
            command=command,
            description=description,
        )
        
        self.recipes[pattern_id].append(recipe)
        
        if pattern_id in self.patterns:
            self.patterns[pattern_id].recipes.append(strategy)
        
        self._save()
        
        return recipe
    
    def get_improvement_stats(self) -> dict:
        """Get improvement statistics."""
        if not self.patterns:
            return {"total_patterns": 0, "improvement_rate": 0.0}
        
        improved = sum(
            1 for p in self.patterns.values()
            if p.occurrences > 1 and p.success_rate > 0.5
        )
        
        return {
            "total_patterns": len(self.patterns),
            "patterns_with_fixes": len(self.recipes),
            "improved_patterns": improved,
            "improvement_rate": improved / len(self.patterns),
            "total_failures": sum(p.occurrences for p in self.patterns.values()),
            "total_successful_fixes": sum(p.successful_fixes for p in self.patterns.values()),
        }
    
    def export_learning_data(self) -> dict:
        """Export all learning data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "recipes": {k: [r.to_dict() for r in v] for k, v in self.recipes.items()},
            "stats": self.get_improvement_stats(),
        }


# Singleton
_loop: Optional[LearningLoop] = None


def get_learning_loop() -> LearningLoop:
    """Get singleton learning loop."""
    global _loop
    if _loop is None:
        _loop = LearningLoop()
    return _loop


def record_failure(**kwargs) -> FailurePattern:
    """Convenience: record a failure."""
    return get_learning_loop().record_failure(**kwargs)


def record_fix(pattern_id: str, strategy: str) -> None:
    """Convenience: record a successful fix."""
    get_learning_loop().record_success(pattern_id, strategy)


def get_recipe(**kwargs) -> Optional[FixRecipe]:
    """Convenience: get a fix recipe."""
    return get_learning_loop().get_fix_recipe(**kwargs)


# CLI
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Learning Loop CLI")
    parser.add_argument("--record", action="store_true", help="Record a failure")
    parser.add_argument("--tool", default="bash", help="Tool name")
    parser.add_argument("--error", default="timeout", help="Error type")
    parser.add_argument("--message", default="", help="Error message")
    parser.add_argument("--fix", help="Proposed fix")
    parser.add_argument("--stats", action="store_true", help="Show improvement stats")
    parser.add_argument("--export", action="store_true", help="Export all data")
    
    args = parser.parse_args()
    
    loop = LearningLoop()
    
    if args.record:
        pattern = loop.record_failure(
            tool_name=args.tool,
            error_type=args.error,
            error_message=args.message,
            command_hint="",
            proposed_fix=args.fix,
        )
        print(f"Recorded: pattern={pattern.pattern_id}")
    
    if args.stats:
        stats = loop.get_improvement_stats()
        print(json.dumps(stats, indent=2))
    
    if args.export:
        print(json.dumps(loop.export_learning_data(), indent=2))
    
    if not (args.record or args.stats or args.export):
        parser.print_help()

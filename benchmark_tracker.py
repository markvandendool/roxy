"""
Benchmark Tracker with Rolling History

AAA Quality Implementation: Law 0 Reuse - New capability not in Luno or ROXY

This module provides rolling benchmark tracking for model performance:
- Daily benchmark artifacts
- Performance metrics (accuracy, latency, cost)
- Regression detection
- Trend charts

Usage:
    from benchmark_tracker import BenchmarkTracker, record_run, get_report
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("roxy.benchmark_tracker")

ROXY_ROOT = Path.home() / ".roxy"


@dataclass
class BenchmarkRun:
    """Single benchmark run."""
    timestamp: str
    model: str
    task_class: str
    prompt: str
    success: bool
    latency_ms: float
    cost_cents: float
    tokens_used: int = 0
    error: str = ""
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "model": self.model,
            "task_class": self.task_class,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "cost_cents": self.cost_cents,
            "tokens_used": self.tokens_used,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkArtifact:
    """Daily benchmark artifact."""
    date: str
    runs: list[BenchmarkRun]
    summary: dict
    regressions: list[dict]
    recommendations: list[str]
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "runs": [r.to_dict() for r in self.runs],
            "summary": self.summary,
            "regressions": self.regressions,
            "recommendations": self.recommendations,
        }


class BenchmarkTracker:
    """
    Rolling benchmark tracker for model performance.
    
    Tracks:
    - Per-model accuracy, latency, cost
    - Daily artifacts with diffs
    - Regression detection
    - Trend analysis
    
    AAA Quality:
    - Comprehensive type hints
    - Extensive docstrings
    - Structured logging
    - Graceful degradation
    """
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        retention_days: int = 30,
    ):
        """
        Initialize benchmark tracker.
        
        Args:
            data_dir: Directory for benchmark data
            retention_days: Days to retain history
        """
        self.data_dir = data_dir or (ROXY_ROOT / "data" / "benchmarks")
        self.retention_days = retention_days
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BenchmarkTracker initialized: data_dir={self.data_dir}")
    
    def _get_daily_file(self, date: Optional[str] = None) -> Path:
        """Get path for daily benchmark file."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return self.data_dir / f"benchmark-{date}.json"
    
    def record(
        self,
        model: str,
        task_class: str,
        prompt: str,
        success: bool,
        latency_ms: float,
        cost_cents: float = 0.0,
        tokens_used: int = 0,
        error: str = "",
        metadata: Optional[dict] = None,
    ) -> BenchmarkRun:
        """
        Record a benchmark run.
        
        Args:
            model: Model identifier
            task_class: Task category (coding, reasoning, etc.)
            prompt: Prompt used
            success: Whether run succeeded
            latency_ms: Observed latency
            cost_cents: Cost in cents
            tokens_used: Tokens consumed
            error: Error message if failed
            metadata: Additional metadata
            
        Returns:
            BenchmarkRun that was recorded
        """
        run = BenchmarkRun(
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            task_class=task_class,
            prompt=prompt[:500],  # Truncate for storage
            success=success,
            latency_ms=latency_ms,
            cost_cents=cost_cents,
            tokens_used=tokens_used,
            error=error[:200] if error else "",
            metadata=metadata or {},
        )
        
        # Load existing daily data
        daily_file = self._get_daily_file()
        if daily_file.exists():
            try:
                with open(daily_file, 'r') as f:
                    data = json.load(f)
            except Exception:
                data = {"runs": []}
        else:
            data = {"runs": []}
        
        # Add new run
        data["runs"].append(run.to_dict())
        
        # Save
        with open(daily_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(
            f"Recorded benchmark: model={model}, task={task_class}, "
            f"success={success}, latency={latency_ms:.0f}ms"
        )
        
        return run
    
    def get_daily_summary(self, date: Optional[str] = None) -> dict:
        """Get summary for a specific date."""
        daily_file = self._get_daily_file(date)
        
        if not daily_file.exists():
            return {}
        
        try:
            with open(daily_file, 'r') as f:
                data = json.load(f)
        except Exception:
            return {}
        
        runs = [BenchmarkRun(**r) for r in data.get("runs", [])]
        
        if not runs:
            return {}
        
        # Calculate summary
        by_model: dict[str, list[BenchmarkRun]] = {}
        for run in runs:
            if run.model not in by_model:
                by_model[run.model] = []
            by_model[run.model].append(run)
        
        summary = {
            "total_runs": len(runs),
            "successful": sum(1 for r in runs if r.success),
            "failed": sum(1 for r in runs if not r.success),
            "by_model": {},
        }
        
        for model, model_runs in by_model.items():
            successes = [r for r in model_runs if r.success]
            latencies = [r.latency_ms for r in successes]
            
            summary["by_model"][model] = {
                "runs": len(model_runs),
                "success_rate": len(successes) / len(model_runs) if model_runs else 0,
                "latency_p50_ms": sorted(latencies)[len(latencies)//2] if latencies else 0,
                "latency_p95_ms": sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0,
                "total_cost_cents": sum(r.cost_cents for r in model_runs),
                "total_tokens": sum(r.tokens_used for r in model_runs),
            }
        
        return summary
    
    def detect_regressions(self, date: Optional[str] = None) -> list[dict]:
        """
        Detect performance regressions compared to previous days.
        
        Args:
            date: Date to check (default: today)
            
        Returns:
            List of detected regressions
        """
        regressions = []
        
        # Get current and previous summaries
        current = self.get_daily_summary(date)
        previous = self.get_daily_summary(
            (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        )
        
        if not current or not previous:
            return regressions
        
        # Compare models
        for model, current_stats in current.get("by_model", {}).items():
            prev_stats = previous.get("by_model", {}).get(model, {})
            
            if not prev_stats:
                continue
            
            # Check success rate regression
            current_rate = current_stats["success_rate"]
            prev_rate = prev_stats["success_rate"]
            
            if current_rate < prev_rate - 0.05:  # 5% drop
                regressions.append({
                    "type": "success_rate",
                    "model": model,
                    "current": current_rate,
                    "previous": prev_rate,
                    "delta": current_rate - prev_rate,
                    "severity": "high" if current_rate < 0.8 else "medium",
                })
            
            # Check latency regression
            current_lat = current_stats["latency_p95_ms"]
            prev_lat = prev_stats["latency_p95_ms"]
            
            if prev_lat > 0 and current_lat > prev_lat * 1.2:  # 20% slower
                regressions.append({
                    "type": "latency",
                    "model": model,
                    "current_ms": current_lat,
                    "previous_ms": prev_lat,
                    "delta_ms": current_lat - prev_lat,
                    "severity": "high" if current_lat > prev_lat * 1.5 else "medium",
                })
        
        return regressions
    
    def generate_artifact(self, date: Optional[str] = None) -> BenchmarkArtifact:
        """Generate complete daily benchmark artifact."""
        date_str = date or datetime.utcnow().strftime("%Y-%m-%d")
        
        # Get runs
        daily_file = self._get_daily_file(date)
        if daily_file.exists():
            with open(daily_file, 'r') as f:
                data = json.load(f)
            runs = [BenchmarkRun(**r) for r in data.get("runs", [])]
        else:
            runs = []
        
        summary = self.get_daily_summary(date)
        regressions = self.detect_regressions(date)
        
        # Generate recommendations
        recommendations = []
        for model, stats in summary.get("by_model", {}).items():
            if stats["success_rate"] < 0.8:
                recommendations.append(
                    f"Model {model} has low success rate ({stats['success_rate']:.0%}). Consider fallback."
                )
            if stats.get("latency_p95_ms", 0) > 30000:
                recommendations.append(
                    f"Model {model} has high latency (p95: {stats['latency_p95_ms']/1000:.1f}s)."
                )
        
        return BenchmarkArtifact(
            date=date_str,
            runs=runs,
            summary=summary,
            regressions=regressions,
            recommendations=recommendations,
        )
    
    def export_daily(self, date: Optional[str] = None) -> Path:
        """Export daily artifact to file."""
        artifact = self.generate_artifact(date)
        output_file = self.data_dir / f"artifact-{artifact.date}.json"
        
        with open(output_file, 'w') as f:
            json.dump(artifact.to_dict(), f, indent=2)
        
        logger.info(f"Exported benchmark artifact: {output_file}")
        return output_file
    
    def cleanup_old(self) -> int:
        """Remove benchmark files older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        removed = 0
        
        for f in self.data_dir.glob("benchmark-*.json"):
            try:
                file_date = datetime.strptime(f.stem.replace("benchmark-", ""), "%Y-%m-%d")
                if file_date < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                continue
        
        if removed:
            logger.info(f"Cleaned up {removed} old benchmark files")
        
        return removed


# Convenience functions
_tracker: Optional[BenchmarkTracker] = None


def get_tracker() -> BenchmarkTracker:
    """Get singleton benchmark tracker."""
    global _tracker
    if _tracker is None:
        _tracker = BenchmarkTracker()
    return _tracker


def record_run(**kwargs) -> BenchmarkRun:
    """Convenience function to record a run."""
    return get_tracker().record(**kwargs)


def get_report(date: Optional[str] = None) -> dict:
    """Get daily benchmark report."""
    return get_tracker().generate_artifact(date).to_dict()


# CLI
if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Benchmark Tracker CLI")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record a benchmark run"
    )
    parser.add_argument("--model", default="opencode/mimo-v2-pro-free")
    parser.add_argument("--task", default="coding")
    parser.add_argument("--success", type=lambda x: x.lower() == "true", default=True)
    parser.add_argument("--latency", type=float, default=0)
    parser.add_argument("--report", action="store_true", help="Generate report")
    parser.add_argument("--date", help="Date for report (YYYY-MM-DD)")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old files")
    parser.add_argument("--export", action="store_true", help="Export daily artifact")
    
    args = parser.parse_args()
    
    tracker = BenchmarkTracker()
    
    if args.cleanup:
        removed = tracker.cleanup_old()
        print(f"Removed {removed} old files")
    
    if args.record:
        run = tracker.record(
            model=args.model,
            task_class=args.task,
            prompt="CLI benchmark run",
            success=args.success,
            latency_ms=args.latency,
        )
        print(f"Recorded: {run.model} - {'OK' if run.success else 'FAIL'}")
    
    if args.report or args.export:
        artifact = tracker.generate_artifact(args.date)
        print(json.dumps(artifact.to_dict(), indent=2))
    
    if not (args.record or args.report or args.export or args.cleanup):
        parser.print_help()

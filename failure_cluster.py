#!/usr/bin/env python3
"""
Failure Cluster - Error analysis and clustering for debugging
Groups similar failures to identify root causes.
"""
import json
import logging
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("roxy.failure_cluster")

AUDIT_LOG = Path.home() / ".roxy" / "data" / "tool_audit.jsonl"
ERROR_LOG = Path.home() / ".roxy" / "logs" / "errors.log"


@dataclass
class Failure:
    timestamp: float
    tool_name: str
    error_type: str
    error_message: str
    command: str = ""
    exit_code: int = -1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_signature(self) -> str:
        """Get a signature for clustering similar failures."""
        parts = [
            self.tool_name,
            self.error_type,
        ]
        if self.command:
            cmd_parts = self.command.split()
            if cmd_parts:
                parts.append(cmd_parts[0])
        return "|".join(parts)


@dataclass
class FailureCluster:
    signature: str
    count: int
    first_seen: float
    last_seen: float
    error_type: str
    sample_errors: List[str] = field(default_factory=list)
    affected_tools: Set[str] = field(default_factory=set)
    affected_files: Set[str] = field(default_factory=set)
    
    def get_severity(self) -> str:
        """Calculate cluster severity."""
        if self.count >= 10:
            return "critical"
        elif self.count >= 5:
            return "high"
        elif self.count >= 2:
            return "medium"
        return "low"
    
    def get_recommendation(self) -> str:
        """Get recommendation for fixing this cluster."""
        if "timeout" in self.error_type.lower():
            return "Increase timeout for this tool or optimize the operation"
        elif "permission" in self.error_type.lower() or "denied" in self.error_type.lower():
            return "Check file permissions or run with appropriate privileges"
        elif "not found" in self.error_message.lower() or "no such" in self.error_message.lower():
            return "Verify file paths or install missing dependencies"
        elif "memory" in self.error_type.lower():
            return "Reduce batch sizes or add memory limits"
        return "Investigate root cause and add error handling"


class FailureClusterer:
    """
    Analyzes failure patterns and clusters similar errors.
    
    Features:
    - Parse audit logs and error logs
    - Extract error signatures
    - Cluster by similarity
    - Generate recommendations
    """
    
    def __init__(self, audit_log: Optional[Path] = None, error_log: Optional[Path] = None):
        self.audit_log = audit_log or AUDIT_LOG
        self.error_log = error_log or ERROR_LOG
        self._failures: List[Failure] = []
        self._clusters: Dict[str, FailureCluster] = {}
    
    def load_failures_from_audit(self, hours: int = 24) -> List[Failure]:
        """Load failures from tool audit log."""
        failures = []
        if not self.audit_log.exists():
            return failures
        
        cutoff = time.time() - (hours * 3600)
        
        try:
            with open(self.audit_log) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("status") == "failed" or entry.get("exit_code", 0) != 0:
                            failure = Failure(
                                timestamp=datetime.fromisoformat(entry.get("timestamp", "2000-01-01")).timestamp() if "timestamp" in entry else 0,
                                tool_name=entry.get("tool_name", "unknown"),
                                error_type=entry.get("reason", "unknown"),
                                error_message=entry.get("error", ""),
                                command=entry.get("arguments", {}).get("command", ""),
                                exit_code=entry.get("exit_code", -1),
                                metadata=entry,
                            )
                            if failure.timestamp >= cutoff:
                                failures.append(failure)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            logger.warning(f"Failed to load audit log: {e}")
        
        self._failures = failures
        return failures
    
    def load_failures_from_errors(self, hours: int = 24) -> List[Failure]:
        """Load failures from error log."""
        failures = []
        if not self.error_log.exists():
            return failures
        
        cutoff = time.time() - (hours * 3600)
        
        error_pattern = re.compile(
            r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?"
            r"(?P<error_type>ERROR|WARNING).*?"
            r"(?P<message>.*?)(?=\n\d{4}-|\Z)",
            re.DOTALL,
        )
        
        try:
            with open(self.error_log) as f:
                content = f.read()
            
            for match in error_pattern.finditer(content):
                try:
                    ts_str = match.group("timestamp")
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp()
                    if ts >= cutoff:
                        failure = Failure(
                            timestamp=ts,
                            tool_name="system",
                            error_type=match.group("error_type"),
                            error_message=match.group("message").strip()[:200],
                            metadata={"source": "error_log"},
                        )
                        failures.append(failure)
                except (ValueError, AttributeError):
                    continue
        except Exception as e:
            logger.warning(f"Failed to load error log: {e}")
        
        self._failures.extend(failures)
        return failures
    
    def cluster_failures(self) -> Dict[str, FailureCluster]:
        """Cluster failures by signature."""
        clusters: Dict[str, List[Failure]] = defaultdict(list)
        
        for failure in self._failures:
            sig = failure.get_signature()
            clusters[sig].append(failure)
        
        self._clusters = {}
        for sig, failures in clusters.items():
            if len(failures) < 1:
                continue
            
            cluster = FailureCluster(
                signature=sig,
                count=len(failures),
                first_seen=min(f.timestamp for f in failures),
                last_seen=max(f.timestamp for f in failures),
                error_type=failures[0].error_type,
                sample_errors=[f.error_message[:100] for f in failures[:3]],
                affected_tools={f.tool_name for f in failures},
                affected_files=set(),
            )
            self._clusters[sig] = cluster
        
        return self._clusters
    
    def get_top_clusters(self, limit: int = 10) -> List[FailureCluster]:
        """Get top failure clusters by count."""
        return sorted(
            self._clusters.values(),
            key=lambda c: c.count,
            reverse=True,
        )[:limit]
    
    def get_analysis_report(self) -> Dict[str, Any]:
        """Generate full analysis report."""
        if not self._clusters:
            self.cluster_failures()
        
        top_clusters = self.get_top_clusters(10)
        
        total_failures = sum(c.count for c in self._clusters.values())
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for cluster in self._clusters.values():
            severity_counts[cluster.get_severity()] += cluster.count
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_failures": len(self._failures),
                "unique_clusters": len(self._clusters),
                "total_clustered_failures": total_failures,
                "severity_counts": severity_counts,
            },
            "top_clusters": [
                {
                    "signature": c.signature,
                    "count": c.count,
                    "severity": c.get_severity(),
                    "error_type": c.error_type,
                    "sample_errors": c.sample_errors,
                    "first_seen": datetime.fromtimestamp(c.first_seen).isoformat(),
                    "last_seen": datetime.fromtimestamp(c.last_seen).isoformat(),
                    "recommendation": c.get_recommendation(),
                }
                for c in top_clusters
            ],
            "recommendations": [
                c.get_recommendation()
                for c in top_clusters[:5]
            ],
        }
    
    def get_action_items(self) -> List[Dict[str, Any]]:
        """Get prioritized action items from failure analysis."""
        if not self._clusters:
            self.cluster_failures()
        
        items = []
        for cluster in self.get_top_clusters(10):
            severity = cluster.get_severity()
            if severity in ("critical", "high"):
                items.append({
                    "priority": severity,
                    "issue": f"{cluster.error_type}: {cluster.count} failures",
                    "signature": cluster.signature,
                    "recommendation": cluster.get_recommendation(),
                    "first_seen": datetime.fromtimestamp(cluster.first_seen).isoformat(),
                    "last_seen": datetime.fromtimestamp(cluster.last_seen).isoformat(),
                })
        
        return items


def analyze_failures(hours: int = 24) -> Dict[str, Any]:
    """Quick analysis of failures."""
    clusterer = FailureClusterer()
    clusterer.load_failures_from_audit(hours)
    clusterer.load_failures_from_errors(hours)
    clusterer.cluster_failures()
    return clusterer.get_analysis_report()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("ROXY Failure Analysis")
    print("=" * 50)
    
    report = analyze_failures(hours=24)
    
    print(f"\nSummary:")
    print(f"  Total failures: {report['summary']['total_failures']}")
    print(f"  Unique clusters: {report['summary']['unique_clusters']}")
    print(f"  Severity: {report['summary']['severity_counts']}")
    
    print(f"\nTop Failure Clusters:")
    for i, cluster in enumerate(report["top_clusters"][:5], 1):
        print(f"\n{i}. [{cluster['severity'].upper()}] {cluster['error_type']}")
        print(f"   Count: {cluster['count']}")
        print(f"   Last seen: {cluster['last_seen']}")
        print(f"   Recommendation: {cluster['recommendation']}")
    
    print(f"\nAction Items:")
    for item in report.get("recommendations", [])[:3]:
        print(f"  - {item}")

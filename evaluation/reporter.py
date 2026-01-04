#!/usr/bin/env python3
"""
Evaluation Reporter - Generates evaluation reports
"""
import logging
from pathlib import Path
from typing import Dict, Any
from .metrics import get_metrics_collector

logger = logging.getLogger("roxy.evaluation.reporter")

ROXY_DIR = Path.home() / ".roxy"
REPORTS_DIR = ROXY_DIR / "logs" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class EvaluationReporter:
    """Generates evaluation reports"""
    
    def generate_text_report(self) -> str:
        """Generate text-based evaluation report"""
        collector = get_metrics_collector()
        stats = collector.get_stats()
        
        report_lines = [
            "=" * 60,
            "ROXY Evaluation Report",
            "=" * 60,
            "",
            f"Total Queries: {stats['total_queries']}",
            f"Average Response Time: {stats['avg_response_time']}s",
            "",
        ]
        
        if stats.get('avg_accuracy') is not None:
            report_lines.append(f"Average Accuracy: {stats['avg_accuracy']:.0%}")
        
        if stats.get('avg_truthfulness') is not None:
            report_lines.append(f"Average Truthfulness: {stats['avg_truthfulness']:.0%}")
        
        report_lines.extend([
            f"Cache Hit Rate: {stats['cache_hit_rate']:.0%}",
            f"Source Attribution Rate: {stats['source_attribution_rate']:.0%}",
            "",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate JSON evaluation report"""
        collector = get_metrics_collector()
        stats = collector.get_stats()
        recent = collector.get_recent_metrics(10)
        
        return {
            "summary": stats,
            "recent_queries": recent,
            "timestamp": str(Path(__file__).stat().st_mtime)
        }
    
    def save_report(self, format: str = "text"):
        """Save report to file"""
        if format == "text":
            report = self.generate_text_report()
            report_file = REPORTS_DIR / f"evaluation_{Path(__file__).stat().st_mtime}.txt"
            report_file.write_text(report)
            logger.info(f"Saved text report: {report_file}")
            return report_file
        else:
            report = self.generate_json_report()
            import json
            report_file = REPORTS_DIR / f"evaluation_{Path(__file__).stat().st_mtime}.json"
            report_file.write_text(json.dumps(report, indent=2))
            logger.info(f"Saved JSON report: {report_file}")
            return report_file















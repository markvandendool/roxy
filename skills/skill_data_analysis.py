#!/usr/bin/env python3
"""
Data Analysis Skill
===================
RU-012: Built-in Skills Package

Data analysis and visualization capabilities.
Handles CSV, JSON, tabular data with statistical analysis.

Features:
- CSV/JSON data loading
- Statistical summaries
- Pattern detection
- Trend analysis
- Data quality checks

SKILL_MANIFEST required for dynamic loading.
"""

import json
import csv
import io
import re
import statistics
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from collections import Counter


# =============================================================================
# SKILL MANIFEST (Required for skills_registry)
# =============================================================================

SKILL_MANIFEST = {
    "name": "data_analysis",
    "version": "1.0.0",
    "description": "Data analysis with statistics, patterns, and insights generation",
    "author": "ROXY",
    "keywords": [
        "data", "analyze", "analysis", "csv", "json", "statistics", "stats",
        "chart", "graph", "trend", "pattern", "insight", "summary",
        "table", "excel", "spreadsheet", "numbers", "mean", "average"
    ],
    "capabilities": [
        "csv_analysis", "json_analysis", "statistics", 
        "pattern_detection", "data_quality", "insights"
    ],
    "tools": [
        "analyze_csv", "analyze_json", "summarize_data", "detect_patterns", 
        "check_quality", "generate_insights"
    ],
    "dependencies": [],
    "category": "analysis"
}


# =============================================================================
# Types
# =============================================================================

@dataclass
class ColumnStats:
    """Statistics for a data column"""
    name: str
    dtype: str  # "numeric", "string", "datetime", "boolean", "mixed"
    count: int
    unique: int
    missing: int
    
    # Numeric stats (if applicable)
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    
    # String stats (if applicable)
    avg_length: Optional[float] = None
    most_common: Optional[List[tuple]] = None


@dataclass
class DataSummary:
    """Summary of analyzed data"""
    row_count: int
    column_count: int
    columns: List[ColumnStats]
    quality_score: float
    patterns: List[str]
    insights: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Data Loading
# =============================================================================

def load_csv(content: str) -> List[Dict]:
    """Load CSV content into list of dicts"""
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def load_json(content: str) -> Union[List, Dict]:
    """Load JSON content"""
    return json.loads(content)


def normalize_data(data: Any) -> List[Dict]:
    """Normalize data to list of dicts for analysis"""
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            return data
        # List of values - convert to dicts
        return [{"value": v, "index": i} for i, v in enumerate(data)]
    
    if isinstance(data, dict):
        # Single dict - wrap in list
        return [data]
    
    return []


# =============================================================================
# Analysis Functions
# =============================================================================

def infer_dtype(values: List[Any]) -> str:
    """Infer data type from values"""
    types = set()
    
    for v in values:
        if v is None or v == "" or str(v).lower() in ("null", "none", "nan"):
            continue
        
        # Try numeric
        try:
            float(v)
            types.add("numeric")
            continue
        except (ValueError, TypeError):
            pass
        
        # Try datetime
        if isinstance(v, str):
            if re.match(r'\d{4}-\d{2}-\d{2}', v):
                types.add("datetime")
                continue
        
        # Try boolean
        if str(v).lower() in ("true", "false", "yes", "no", "1", "0"):
            types.add("boolean")
            continue
        
        types.add("string")
    
    if len(types) == 0:
        return "unknown"
    if len(types) == 1:
        return types.pop()
    return "mixed"


def analyze_column(name: str, values: List[Any]) -> ColumnStats:
    """Analyze a single column"""
    dtype = infer_dtype(values)
    
    # Basic stats
    count = len(values)
    missing = sum(1 for v in values if v is None or v == "" or str(v).lower() in ("null", "none", "nan"))
    non_null = [v for v in values if v is not None and v != "" and str(v).lower() not in ("null", "none", "nan")]
    unique = len(set(str(v) for v in non_null))
    
    stats = ColumnStats(
        name=name,
        dtype=dtype,
        count=count,
        unique=unique,
        missing=missing
    )
    
    if dtype == "numeric" and non_null:
        try:
            nums = [float(v) for v in non_null]
            stats.mean = statistics.mean(nums)
            stats.median = statistics.median(nums)
            if len(nums) > 1:
                stats.std = statistics.stdev(nums)
            stats.min_val = min(nums)
            stats.max_val = max(nums)
        except:
            pass
    
    elif dtype == "string" and non_null:
        str_vals = [str(v) for v in non_null]
        stats.avg_length = sum(len(s) for s in str_vals) / len(str_vals)
        counter = Counter(str_vals)
        stats.most_common = counter.most_common(5)
    
    return stats


def analyze_data(data: List[Dict]) -> DataSummary:
    """Analyze tabular data"""
    if not data:
        return DataSummary(
            row_count=0,
            column_count=0,
            columns=[],
            quality_score=0,
            patterns=[],
            insights=["No data to analyze"]
        )
    
    # Get all column names
    columns = set()
    for row in data:
        columns.update(row.keys())
    columns = sorted(columns)
    
    # Analyze each column
    column_stats = []
    for col in columns:
        values = [row.get(col) for row in data]
        stats = analyze_column(col, values)
        column_stats.append(stats)
    
    # Calculate quality score
    total_cells = len(data) * len(columns)
    missing_cells = sum(s.missing for s in column_stats)
    quality_score = ((total_cells - missing_cells) / total_cells * 100) if total_cells > 0 else 0
    
    # Detect patterns
    patterns = detect_data_patterns(data, column_stats)
    
    # Generate insights
    insights = generate_data_insights(data, column_stats)
    
    return DataSummary(
        row_count=len(data),
        column_count=len(columns),
        columns=column_stats,
        quality_score=round(quality_score, 1),
        patterns=patterns,
        insights=insights
    )


def detect_data_patterns(data: List[Dict], column_stats: List[ColumnStats]) -> List[str]:
    """Detect patterns in data"""
    patterns = []
    
    for stats in column_stats:
        # High cardinality
        if stats.unique == stats.count - stats.missing:
            patterns.append(f"'{stats.name}' has all unique values (possible ID column)")
        
        # Low cardinality
        elif stats.unique <= 5 and stats.count > 20:
            patterns.append(f"'{stats.name}' has low cardinality ({stats.unique} unique values) - possible category")
        
        # Numeric ranges
        if stats.dtype == "numeric" and stats.min_val is not None:
            range_val = stats.max_val - stats.min_val
            if range_val == 0:
                patterns.append(f"'{stats.name}' has constant value ({stats.min_val})")
            elif stats.std and stats.std / abs(stats.mean) < 0.1:
                patterns.append(f"'{stats.name}' has low variance (tight clustering around {stats.mean:.2f})")
        
        # Missing data pattern
        if stats.missing > stats.count * 0.5:
            patterns.append(f"'{stats.name}' is mostly missing ({stats.missing}/{stats.count})")
    
    return patterns[:10]  # Limit patterns


def generate_data_insights(data: List[Dict], column_stats: List[ColumnStats]) -> List[str]:
    """Generate insights from data"""
    insights = []
    
    # Overall insight
    numeric_cols = [s for s in column_stats if s.dtype == "numeric"]
    string_cols = [s for s in column_stats if s.dtype == "string"]
    
    insights.append(f"Dataset has {len(data)} rows and {len(column_stats)} columns")
    
    if numeric_cols:
        insights.append(f"{len(numeric_cols)} numeric columns available for quantitative analysis")
    
    if string_cols:
        insights.append(f"{len(string_cols)} text columns available for categorical analysis")
    
    # Quality insights
    for stats in column_stats:
        if stats.missing > 0:
            pct = (stats.missing / stats.count) * 100
            if pct > 20:
                insights.append(f"⚠️ '{stats.name}' has {pct:.0f}% missing values - consider handling")
    
    # Numeric insights
    for stats in numeric_cols:
        if stats.mean is not None and stats.std is not None:
            if stats.std > stats.mean * 2:
                insights.append(f"'{stats.name}' has high variance (std={stats.std:.2f}) - outliers likely")
    
    # Categorical insights
    for stats in string_cols:
        if stats.most_common:
            top_val, top_count = stats.most_common[0]
            pct = (top_count / (stats.count - stats.missing)) * 100
            if pct > 50:
                insights.append(f"'{stats.name}' dominated by '{top_val[:20]}' ({pct:.0f}%)")
    
    return insights[:10]  # Limit insights


def check_data_quality(data: List[Dict]) -> Dict:
    """Check data quality and return report"""
    if not data:
        return {"success": False, "error": "No data provided"}
    
    issues = []
    warnings = []
    
    columns = set()
    for row in data:
        columns.update(row.keys())
    
    # Check for inconsistent schemas
    schema_issues = 0
    for row in data:
        if set(row.keys()) != columns:
            schema_issues += 1
    
    if schema_issues > 0:
        issues.append(f"Inconsistent schema: {schema_issues} rows have different columns")
    
    # Check each column
    for col in columns:
        values = [row.get(col) for row in data]
        missing = sum(1 for v in values if v is None or v == "")
        
        if missing == len(values):
            issues.append(f"Column '{col}' is entirely empty")
        elif missing > len(values) * 0.5:
            warnings.append(f"Column '{col}' is >50% empty")
        
        # Check for mixed types
        dtype = infer_dtype(values)
        if dtype == "mixed":
            warnings.append(f"Column '{col}' has mixed data types")
    
    # Calculate score
    total_checks = len(columns) * 2 + 1
    issues_weight = len(issues) * 2 + len(warnings)
    quality_score = max(0, 100 - (issues_weight / total_checks * 100))
    
    return {
        "success": True,
        "quality_score": round(quality_score, 1),
        "issues": issues,
        "warnings": warnings,
        "issue_count": len(issues),
        "warning_count": len(warnings),
        "recommendation": "Good quality" if quality_score >= 80 else "Needs attention" if quality_score >= 50 else "Poor quality"
    }


# =============================================================================
# Public API
# =============================================================================

def analyze_csv_content(content: str) -> Dict:
    """
    Analyze CSV content.
    
    Args:
        content: CSV string
    
    Returns:
        Analysis summary
    """
    try:
        data = load_csv(content)
        summary = analyze_data(data)
        
        return {
            "success": True,
            "format": "csv",
            "row_count": summary.row_count,
            "column_count": summary.column_count,
            "quality_score": summary.quality_score,
            "columns": [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "count": c.count,
                    "unique": c.unique,
                    "missing": c.missing,
                    "mean": c.mean,
                    "median": c.median,
                    "std": c.std,
                    "min": c.min_val,
                    "max": c.max_val
                }
                for c in summary.columns
            ],
            "patterns": summary.patterns,
            "insights": summary.insights
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_json_content(content: str) -> Dict:
    """
    Analyze JSON content.
    
    Args:
        content: JSON string
    
    Returns:
        Analysis summary
    """
    try:
        data = load_json(content)
        normalized = normalize_data(data)
        
        if not normalized:
            return {"success": False, "error": "Could not normalize JSON to tabular format"}
        
        summary = analyze_data(normalized)
        
        return {
            "success": True,
            "format": "json",
            "original_type": "array" if isinstance(data, list) else "object",
            "row_count": summary.row_count,
            "column_count": summary.column_count,
            "quality_score": summary.quality_score,
            "columns": [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "unique": c.unique,
                    "missing": c.missing
                }
                for c in summary.columns
            ],
            "patterns": summary.patterns,
            "insights": summary.insights
        }
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def analyze_file(file_path: str) -> Dict:
    """
    Analyze a data file (CSV or JSON).
    
    Args:
        file_path: Path to file
    
    Returns:
        Analysis summary
    """
    try:
        path = Path(file_path).expanduser()
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        content = path.read_text()
        
        if path.suffix.lower() == ".csv":
            return analyze_csv_content(content)
        elif path.suffix.lower() == ".json":
            return analyze_json_content(content)
        else:
            # Try to detect format
            content_stripped = content.strip()
            if content_stripped.startswith(('[', '{')):
                return analyze_json_content(content)
            else:
                return analyze_csv_content(content)
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def summarize_numbers(values: List[float]) -> Dict:
    """
    Get statistical summary of numeric values.
    
    Args:
        values: List of numbers
    
    Returns:
        Statistical summary
    """
    if not values:
        return {"success": False, "error": "No values provided"}
    
    try:
        nums = [float(v) for v in values if v is not None]
        
        if not nums:
            return {"success": False, "error": "No valid numbers"}
        
        return {
            "success": True,
            "count": len(nums),
            "sum": sum(nums),
            "mean": statistics.mean(nums),
            "median": statistics.median(nums),
            "mode": statistics.mode(nums) if len(nums) > 1 else nums[0],
            "std": statistics.stdev(nums) if len(nums) > 1 else 0,
            "variance": statistics.variance(nums) if len(nums) > 1 else 0,
            "min": min(nums),
            "max": max(nums),
            "range": max(nums) - min(nums),
            "quartiles": {
                "q1": statistics.quantiles(nums, n=4)[0] if len(nums) >= 4 else None,
                "q2": statistics.median(nums),
                "q3": statistics.quantiles(nums, n=4)[2] if len(nums) >= 4 else None
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP Tool Interface
# =============================================================================

TOOLS = {
    "analyze_csv": {
        "description": "Analyze CSV data content",
        "parameters": {
            "content": {"type": "string", "description": "CSV content as string"}
        },
        "required": ["content"]
    },
    "analyze_json": {
        "description": "Analyze JSON data content",
        "parameters": {
            "content": {"type": "string", "description": "JSON content as string"}
        },
        "required": ["content"]
    },
    "analyze_file": {
        "description": "Analyze a data file (CSV or JSON)",
        "parameters": {
            "file_path": {"type": "string", "description": "Path to data file"}
        },
        "required": ["file_path"]
    },
    "summarize_data": {
        "description": "Get statistical summary of numeric values",
        "parameters": {
            "values": {"type": "array", "items": {"type": "number"}}
        },
        "required": ["values"]
    },
    "check_quality": {
        "description": "Check data quality and return issues",
        "parameters": {
            "content": {"type": "string", "description": "CSV or JSON content"},
            "format": {"type": "string", "enum": ["csv", "json"], "default": "csv"}
        },
        "required": ["content"]
    },
    "generate_insights": {
        "description": "Generate insights from data",
        "parameters": {
            "content": {"type": "string"},
            "format": {"type": "string", "enum": ["csv", "json"], "default": "csv"}
        },
        "required": ["content"]
    }
}


def handle_tool(name: str, params: Dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "analyze_csv": lambda p: analyze_csv_content(p["content"]),
        "analyze_json": lambda p: analyze_json_content(p["content"]),
        "analyze_file": lambda p: analyze_file(p["file_path"]),
        "summarize_data": lambda p: summarize_numbers(p["values"]),
        "check_quality": lambda p: check_data_quality(
            load_csv(p["content"]) if p.get("format", "csv") == "csv" else normalize_data(load_json(p["content"]))
        ),
        "generate_insights": lambda p: {
            "success": True,
            "insights": analyze_data(
                load_csv(p["content"]) if p.get("format", "csv") == "csv" else normalize_data(load_json(p["content"]))
            ).insights
        }
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# Query Handler (for router integration)
# =============================================================================

def handle_query(query: str, params: Dict = None) -> Dict:
    """
    Handle a routed query.
    Called by expert_router when this skill is selected.
    """
    params = params or {}
    query_lower = query.lower()
    
    # Check for file path
    file_match = re.search(r'[./~][\w/.-]+\.(csv|json)', query, re.IGNORECASE)
    if file_match:
        return analyze_file(file_match.group())
    
    # Check for provided content
    if "content" in params:
        content = params["content"]
        fmt = params.get("format", "csv")
        if fmt == "json" or content.strip().startswith(('[', '{')):
            return analyze_json_content(content)
        return analyze_csv_content(content)
    
    # Check for values
    if "values" in params:
        return summarize_numbers(params["values"])
    
    # Extract numbers from query
    numbers = re.findall(r'[-+]?\d*\.?\d+', query)
    if numbers and len(numbers) >= 2:
        return summarize_numbers([float(n) for n in numbers])
    
    return {"success": False, "error": "Provide a file path, content, or values to analyze"}


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: skill_data_analysis.py <command> [args]")
        print("Commands: analyze <file>, stats <numbers...>, quality <file>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "analyze" and len(sys.argv) >= 3:
        result = analyze_file(sys.argv[2])
    elif cmd == "stats" and len(sys.argv) >= 3:
        nums = [float(n) for n in sys.argv[2:]]
        result = summarize_numbers(nums)
    elif cmd == "quality" and len(sys.argv) >= 3:
        path = Path(sys.argv[2])
        content = path.read_text()
        data = load_csv(content) if path.suffix == ".csv" else normalize_data(load_json(content))
        result = check_data_quality(data)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    print(json.dumps(result, indent=2))

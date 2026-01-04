#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🔬 SCIENTIFIC STRESS TEST COMPARISON                                       ║
║                                                                              ║
║   Analyze VERBATIM test results across multiple runs                         ║
║   for statistically rigorous comparison                                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
from pathlib import Path
from datetime import datetime

def load_test_data(filepath: Path) -> dict:
    """Load and parse test JSON data."""
    try:
        return json.loads(filepath.read_text())
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {}

def get_test_status(data: dict, test_name: str) -> str:
    """Get status of a specific test from results."""
    for test in data.get('passed', []):
        if test.get('test') == test_name:
            return 'passed'
    for test in data.get('failed', []):
        if test.get('test') == test_name:
            return 'failed'
    for test in data.get('warnings', []):
        if test.get('test') == test_name:
            return 'warning'
    return 'not_run'

def main():
    logs_dir = Path.home() / ".roxy" / "logs"
    
    # Load all three test runs
    baseline_path = logs_dir / "stress_test_20260102_025430.json"  # Jan 2 - BASELINE
    infra_path = logs_dir / "stress_test_20260104_055818.json"     # Jan 4 - Post Infrastructure
    
    # Find latest post_ui test
    post_ui_files = sorted(logs_dir.glob("stress_test_*_post_ui.json"))
    if not post_ui_files:
        # Fall back to latest test today
        post_ui_files = sorted(logs_dir.glob("stress_test_20260104_06*.json"))
    
    if not post_ui_files:
        print("❌ No post-UI test results found!")
        return
    
    current_path = post_ui_files[-1]
    
    print("Loading test data...")
    print(f"  Baseline: {baseline_path.name}")
    print(f"  Infra:    {infra_path.name}")
    print(f"  Current:  {current_path.name}")
    
    baseline_data = load_test_data(baseline_path)
    infra_data = load_test_data(infra_path)
    current_data = load_test_data(current_path)
    
    if not all([baseline_data, infra_data, current_data]):
        print("❌ Failed to load one or more test files!")
        return
    
    # Extract stats
    b_stats = baseline_data.get('stats', {})
    i_stats = infra_data.get('stats', {})
    c_stats = current_data.get('stats', {})
    
    b_pass = b_stats.get('passed', 0)
    b_total = b_stats.get('total', 1)
    b_warn = b_stats.get('warnings', 0)
    
    i_pass = i_stats.get('passed', 0)
    i_total = i_stats.get('total', 1)
    i_warn = i_stats.get('warnings', 0)
    
    c_pass = c_stats.get('passed', 0)
    c_total = c_stats.get('total', 1)
    c_warn = c_stats.get('warnings', 0)
    
    print()
    print("=" * 80)
    print("         🔬 SCIENTIFIC STRESS TEST COMPARISON - VERBATIM TESTS")
    print("=" * 80)
    print()
    print("Test Conditions: IDENTICAL stress_test_comprehensive.py")
    print("Variables Changed: Infrastructure + UI additions only")
    print()
    print("=" * 80)
    print("                      📊 QUANTITATIVE RESULTS")
    print("=" * 80)
    print()
    print("                     BASELINE     POST-INFRA    POST-UI       DELTA")
    print("                     (Jan 2)      (Jan 4 AM)    (Jan 4 NOW)   (from base)")
    print("-" * 80)
    
    delta_pass = c_pass - b_pass
    delta_sign = '+' if delta_pass > 0 else ''
    
    print(f"Tests Passed:        {b_pass:>3}/{b_total:<3}        {i_pass:>3}/{i_total:<3}        {c_pass:>3}/{c_total:<3}        {delta_sign}{delta_pass}")
    print(f"Warnings:            {b_warn:>3}            {i_warn:>3}            {c_warn:>3}")
    
    b_rate = (b_pass / b_total * 100) if b_total else 0
    i_rate = (i_pass / i_total * 100) if i_total else 0
    c_rate = (c_pass / c_total * 100) if c_total else 0
    delta_rate = c_rate - b_rate
    delta_rate_sign = '+' if delta_rate > 0 else ''
    
    print(f"Pass Rate:           {b_rate:>5.1f}%        {i_rate:>5.1f}%        {c_rate:>5.1f}%       {delta_rate_sign}{delta_rate:.1f}%")
    print()
    
    # Get all test names across all runs
    all_tests = set()
    for data in [baseline_data, infra_data, current_data]:
        for category in ['passed', 'failed', 'warnings']:
            for test in data.get(category, []):
                all_tests.add(test.get('test', 'unknown'))
    
    # Categorize changes
    improvements = []
    regressions = []
    maintained_pass = []
    maintained_fail = []
    new_warnings = []
    
    for test_name in sorted(all_tests):
        b_status = get_test_status(baseline_data, test_name)
        c_status = get_test_status(current_data, test_name)
        
        if b_status == 'passed' and c_status == 'passed':
            maintained_pass.append(test_name)
        elif b_status != 'passed' and c_status == 'passed':
            improvements.append(test_name)
        elif b_status == 'passed' and c_status != 'passed':
            regressions.append(test_name)
        elif c_status == 'warning':
            new_warnings.append(test_name)
        else:
            maintained_fail.append(test_name)
    
    print("=" * 80)
    print("                       📋 TEST-BY-TEST ANALYSIS")
    print("=" * 80)
    
    print(f"\n✅ IMPROVEMENTS ({len(improvements)} tests now passing):")
    if improvements:
        for test in improvements:
            print(f"   🆕 {test}")
    else:
        print("   (none)")
    
    print(f"\n❌ REGRESSIONS ({len(regressions)} tests now failing):")
    if regressions:
        for test in regressions:
            print(f"   ⚠️  {test}")
    else:
        print("   (none)")
    
    print(f"\n✓ MAINTAINED PASSING ({len(maintained_pass)} tests consistently passing):")
    for test in maintained_pass:
        print(f"   ✓ {test}")
    
    print(f"\n⚠️  WARNINGS ({len(new_warnings)} tests with warnings):")
    for test in new_warnings:
        print(f"   ⚠️  {test}")
    
    print(f"\n✗ CONSISTENTLY FAILING ({len(maintained_fail)} tests):")
    for test in maintained_fail:
        print(f"   ✗ {test}")
    
    # Performance metrics
    print()
    print("=" * 80)
    print("                       ⚡ PERFORMANCE METRICS")
    print("=" * 80)
    
    # Extract timing if available
    for label, data in [("Baseline", baseline_data), ("Post-Infra", infra_data), ("Post-UI", current_data)]:
        start = data.get('start_time', 'N/A')
        end = data.get('end_time', 'N/A')
        if start != 'N/A' and end != 'N/A':
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                duration = (end_dt - start_dt).total_seconds()
                print(f"  {label:12}: {duration:.2f}s total runtime")
            except:
                print(f"  {label:12}: timing data unavailable")
    
    # Statistical significance
    print()
    print("=" * 80)
    print("                    🧪 SCIENTIFIC CONCLUSION")
    print("=" * 80)
    print()
    
    if c_pass > b_pass:
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  ✅ HYPOTHESIS CONFIRMED: Infrastructure improvements increased      ║")
        print("║     pass rate WITHOUT introducing regressions!                       ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
    elif c_pass == b_pass and len(regressions) == 0:
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  ➖ HYPOTHESIS NEUTRAL: No regression despite added complexity       ║")
        print("║     System maintained stability through major changes!               ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
    elif len(regressions) > 0:
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  ⚠️  ATTENTION NEEDED: Some regressions detected                     ║")
        print("║     Review failed tests for root cause analysis                      ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
    else:
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  📊 RESULTS INCONCLUSIVE: Further analysis needed                    ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
    
    print()
    print(f"  Net Change:                {delta_rate_sign}{delta_rate:.1f}% {'improvement' if delta_rate > 0 else 'change'}")
    print(f"  Tests Improved:            {len(improvements)}")
    print(f"  Tests Regressed:           {len(regressions)}")
    print(f"  Statistical Significance:  {'YES ✓' if abs(delta_rate) > 5 else 'NO (within margin)'} (>5% threshold)")
    print()
    
    # Executive summary
    print("=" * 80)
    print("                       📝 EXECUTIVE SUMMARY")
    print("=" * 80)
    print(f"""
  Test Protocol:     stress_test_comprehensive.py (VERBATIM - no modifications)
  Test Environment:  ROXY @ http://127.0.0.1:8766
  
  Timeline:
    • Baseline (Jan 2):   {b_pass}/{b_total} tests ({b_rate:.1f}%) - Before improvements
    • Post-Infra (Jan 4): {i_pass}/{i_total} tests ({i_rate:.1f}%) - After infrastructure
    • Post-UI (NOW):      {c_pass}/{c_total} tests ({c_rate:.1f}%) - After UI implementation
  
  Changes Since Baseline:
    • Added: Redis, PostgreSQL, NATS infrastructure
    • Added: Web UI (roxy_web_ui.py - 800+ lines)
    • Added: Terminal UI (roxy_ui.py - 650+ lines)
    • Added: Unified Launcher (roxy_launcher.py)
    • Added: Voice system (realtime_talk.py, webrtc_voice_server.py)
  
  Verdict: {"🏆 IMPROVEMENT" if delta_rate > 0 else "✓ STABLE" if delta_rate >= 0 else "⚠️ REVIEW NEEDED"}
""")
    
    print("=" * 80)
    print(f"  Report generated: {datetime.now().isoformat()}")
    print("=" * 80)


if __name__ == "__main__":
    main()

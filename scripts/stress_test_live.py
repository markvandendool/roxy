#!/usr/bin/env python3
"""
Live Stress Test for ROXY - Tests all capabilities under load
"""
import asyncio
import sys
import os
import time
from pathlib import Path
from datetime import datetime

ROXY_ROOT = os.environ.get("ROXY_ROOT", os.path.expanduser("~/.roxy"))
LEGACY_ROOT = os.environ.get("ROXY_LEGACY_ROOT", "/opt/roxy")
sys.path.insert(0, str(Path(ROXY_ROOT) / "services"))
sys.path.insert(0, str(Path(LEGACY_ROOT) / "services.LEGACY.20260101_200448"))

from roxy_interface import RoxyInterface

class RoxyStressTester:
    def __init__(self):
        self.interface = RoxyInterface()
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'response_times': [],
            'categories': {}
        }
    
    async def test_query(self, category: str, question: str, expected_indicators: list = None):
        """Test a single query"""
        self.results['total'] += 1
        if category not in self.results['categories']:
            self.results['categories'][category] = {'passed': 0, 'failed': 0}
        
        start_time = time.time()
        try:
            response = await self.interface.chat_terminal(question)
            response_time = time.time() - start_time
            self.results['response_times'].append(response_time)
            
            # Check response quality
            has_source = '📌 Source:' in response or '📌' in response
            has_content = len(response.strip()) > 20
            no_generic = 'Tool A' not in response and 'Tool B' not in response
            
            # Check for expected indicators
            indicators_met = True
            if expected_indicators:
                indicators_met = any(indicator.lower() in response.lower() for indicator in expected_indicators)
            
            passed = has_source and has_content and no_generic and indicators_met
            
            if passed:
                self.results['passed'] += 1
                self.results['categories'][category]['passed'] += 1
                status = "✅ PASS"
            else:
                self.results['failed'] += 1
                self.results['categories'][category]['failed'] += 1
                status = "❌ FAIL"
            
            print(f"{status} [{response_time:.2f}s] {category}: {question[:60]}...")
            if not passed:
                print(f"   Issues: source={has_source}, content={has_content}, no_generic={no_generic}, indicators={indicators_met}")
            
            return response
            
        except Exception as e:
            self.results['errors'] += 1
            self.results['categories'][category]['failed'] += 1
            print(f"❌ ERROR [{time.time() - start_time:.2f}s] {category}: {question[:60]}...")
            print(f"   Error: {str(e)[:100]}")
            return None
    
    async def run_stress_test(self):
        """Run comprehensive stress test"""
        print("=" * 80)
        print("🔥 ROXY LIVE STRESS TEST")
        print("=" * 80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test 1: Knowledge Questions
        print("📚 TEST 1: Knowledge Questions")
        print("-" * 80)
        knowledge_tests = [
            ("What is Python?", ["python", "programming"]),
            ("Explain recursion", ["recursion", "function"]),
            ("What is REST API?", ["rest", "api", "http"]),
            ("What is Docker?", ["docker", "container"]),
            ("Explain async/await", ["async", "await", "asynchronous"]),
        ]
        for question, indicators in knowledge_tests:
            await self.test_query("Knowledge", question, indicators)
            await asyncio.sleep(0.5)  # Small delay between queries
        
        print()
        
        # Test 2: Repository Questions
        print("📁 TEST 2: Repository Questions (RAG)")
        print("-" * 80)
        repo_tests = [
            ("What pages are in the mindsong-juke-hub project?", ["page", "file", "mindsong"]),
            ("List files in the repository", ["file", "list"]),
            ("What is the mindsong-juke-hub project about?", ["mindsong", "project"]),
            ("What components are in the codebase?", ["component", "code"]),
        ]
        for question, indicators in repo_tests:
            await self.test_query("Repository", question, indicators)
            await asyncio.sleep(0.5)
        
        print()
        
        # Test 3: File Operations
        print("📂 TEST 3: File Operations")
        print("-" * 80)
        file_tests = [
            ("list pages in mindsong-juke-hub", ["page", "file", "list"]),
            ("list all files in the project", ["file", "list"]),
            ("show me the pages", ["page", "file"]),
        ]
        for question, indicators in file_tests:
            await self.test_query("FileOps", question, indicators)
            await asyncio.sleep(0.5)
        
        print()
        
        # Test 4: Memory & Context
        print("🧠 TEST 4: Memory & Context")
        print("-" * 80)
        memory_tests = [
            ("What do you know?", ["remember", "know", "fact"]),
            ("What have we discussed?", ["conversation", "discuss"]),
            ("How are you?", ["well", "good", "help"]),
        ]
        for question, indicators in memory_tests:
            await self.test_query("Memory", question, indicators)
            await asyncio.sleep(0.5)
        
        print()
        
        # Test 5: Error Handling
        print("⚠️  TEST 5: Error Handling")
        print("-" * 80)
        error_tests = [
            ("list files in /nonexistent/path", ["error", "not found", "unable"]),
            ("what is this nonexistent thing?", ["understand", "help"]),
        ]
        for question, indicators in error_tests:
            await self.test_query("ErrorHandling", question, indicators)
            await asyncio.sleep(0.5)
        
        print()
        
        # Test 6: Rapid Fire (Stress Test)
        print("⚡ TEST 6: Rapid Fire (10 queries in 5 seconds)")
        print("-" * 80)
        rapid_queries = [
            "hello",
            "what is Python?",
            "list pages",
            "how are you?",
            "what do you know?",
            "explain recursion",
            "what is Docker?",
            "list files",
            "what is REST?",
            "hello again",
        ]
        
        start_rapid = time.time()
        tasks = []
        for query in rapid_queries:
            tasks.append(self.test_query("RapidFire", query))
        
        await asyncio.gather(*tasks)
        rapid_time = time.time() - start_rapid
        
        print()
        print("=" * 80)
        print("📊 STRESS TEST RESULTS")
        print("=" * 80)
        
        total_time = sum(self.results['response_times'])
        avg_time = total_time / len(self.results['response_times']) if self.results['response_times'] else 0
        min_time = min(self.results['response_times']) if self.results['response_times'] else 0
        max_time = max(self.results['response_times']) if self.results['response_times'] else 0
        
        print(f"Total Queries: {self.results['total']}")
        print(f"✅ Passed: {self.results['passed']} ({self.results['passed']/self.results['total']*100:.1f}%)")
        print(f"❌ Failed: {self.results['failed']} ({self.results['failed']/self.results['total']*100:.1f}%)")
        print(f"⚠️  Errors: {self.results['errors']}")
        print()
        print(f"Response Times:")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Min: {min_time:.2f}s")
        print(f"  Max: {max_time:.2f}s")
        print(f"  Rapid Fire: {rapid_time:.2f}s for {len(rapid_queries)} queries")
        print()
        print("Category Breakdown:")
        for category, stats in self.results['categories'].items():
            total_cat = stats['passed'] + stats['failed']
            if total_cat > 0:
                pass_rate = stats['passed'] / total_cat * 100
                print(f"  {category}: {stats['passed']}/{total_cat} ({pass_rate:.1f}%)")
        
        print()
        overall_pass_rate = self.results['passed'] / self.results['total'] * 100 if self.results['total'] > 0 else 0
        print(f"🎯 Overall Pass Rate: {overall_pass_rate:.1f}%")
        
        if overall_pass_rate >= 90:
            print("✅ STRESS TEST PASSED - ROXY is performing excellently!")
        elif overall_pass_rate >= 75:
            print("⚠️  STRESS TEST WARNING - Some issues detected")
        else:
            print("❌ STRESS TEST FAILED - Significant issues detected")
        
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

async def main():
    roxy_root = os.environ.get('ROXY_ROOT', os.path.expanduser('~/.roxy'))
    legacy_root = os.environ.get('ROXY_LEGACY_ROOT', '/opt/roxy')
    tester = RoxyStressTester()
    await tester.run_stress_test()

if __name__ == "__main__":
    asyncio.run(main())











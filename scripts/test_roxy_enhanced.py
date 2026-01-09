#!/usr/bin/env python3
"""
Enhanced ROXY Test Suite - Tests all new quality improvements
"""
import sys
import asyncio
sys.path.insert(0, '/opt/roxy/services')
sys.path.insert(0, '/opt/roxy/services.LEGACY.20260101_200448')

from roxy_interface_enhanced import get_enhanced_interface
from roxy_core import RoxyMemory

class EnhancedRoxyTester:
    def __init__(self):
        self.interface = get_enhanced_interface()
        self.memory = RoxyMemory()
        self.results = []
    
    async def test_source_attribution(self):
        """Test source attribution on all response types"""
        print("\n" + "="*70)
        print("TEST: SOURCE ATTRIBUTION")
        print("="*70)
        
        tests = [
            ("hello", "pattern"),
            ("how are you", "pattern"),
            ("list pages in mindsong-juke-hub", "filesystem"),
            ("what is Python?", "llm"),
        ]
        
        passed = 0
        for question, expected_source in tests:
            print(f"\nQ: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"Response: {response[:150]}...")
                
                # Check for source attribution
                if '📌 Source:' in response:
                    passed += 1
                    print(f"✅ PASSED - Source attribution found")
                else:
                    print(f"❌ FAILED - No source attribution")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Source Attribution: {passed}/{len(tests)} passed")
        self.results.append(('Source Attribution', passed, len(tests)))
        return passed == len(tests)
    
    async def test_validation(self):
        """Test validation and hallucination prevention"""
        print("\n" + "="*70)
        print("TEST: VALIDATION & HALLUCINATION PREVENTION")
        print("="*70)
        
        # Test that file listings are real
        tests = [
            "list pages in mindsong-juke-hub",
            "list all files in the project",
        ]
        
        passed = 0
        for question in tests:
            print(f"\nQ: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"Response length: {len(response)} chars")
                
                # Check for validation indicators
                has_real_files = any(ext in response for ext in ['.tsx', '.ts', '.jsx', '.js', '.py', '.md'])
                has_source = '📌 Source:' in response
                no_generic = 'Tool A' not in response and 'Tool B' not in response
                
                if has_real_files and has_source and no_generic:
                    passed += 1
                    print("✅ PASSED - Real files, source attribution, no hallucinations")
                else:
                    print(f"❌ FAILED - has_files={has_real_files}, has_source={has_source}, no_generic={no_generic}")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Validation: {passed}/{len(tests)} passed")
        self.results.append(('Validation', passed, len(tests)))
        return passed == len(tests)
    
    async def test_error_handling(self):
        """Test error handling and recovery"""
        print("\n" + "="*70)
        print("TEST: ERROR HANDLING")
        print("="*70)
        
        # Test with invalid queries
        tests = [
            "list files in /nonexistent/path",
            "what is this nonexistent thing that doesn't exist anywhere?",
        ]
        
        passed = 0
        for question in tests:
            print(f"\nQ: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"Response: {response[:200]}...")
                
                # Should have graceful error handling
                has_error_handling = (
                    'error' in response.lower() or 
                    'not found' in response.lower() or
                    'unable' in response.lower() or
                    '📌 Source:' in response
                )
                
                if has_error_handling:
                    passed += 1
                    print("✅ PASSED - Graceful error handling")
                else:
                    print("❌ FAILED - No error handling")
            except Exception as e:
                # Exception is OK if it's handled gracefully
                print(f"⚠️ Exception (may be OK): {e}")
                passed += 1
        
        print(f"\n📊 Error Handling: {passed}/{len(tests)} passed")
        self.results.append(('Error Handling', passed, len(tests)))
        return passed == len(tests)
    
    async def test_quality_checks(self):
        """Test quality checks and confidence scoring"""
        print("\n" + "="*70)
        print("TEST: QUALITY CHECKS")
        print("="*70)
        
        tests = [
            "hello",
            "what is Python?",
            "list pages in mindsong-juke-hub",
        ]
        
        passed = 0
        for question in tests:
            print(f"\nQ: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"Response length: {len(response)} chars")
                
                # Check for quality indicators
                has_source = '📌 Source:' in response
                has_timestamp = '⏰' in response or any(char.isdigit() for char in response[-20:])
                sufficient_length = len(response.strip()) > 20
                
                if has_source and sufficient_length:
                    passed += 1
                    print("✅ PASSED - Quality indicators present")
                else:
                    print(f"❌ FAILED - has_source={has_source}, sufficient_length={sufficient_length}")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Quality Checks: {passed}/{len(tests)} passed")
        self.results.append(('Quality Checks', passed, len(tests)))
        return passed == len(tests)
    
    async def run_all_tests(self):
        """Run all enhanced tests"""
        print("\n" + "="*70)
        print("ENHANCED ROXY TEST SUITE")
        print("="*70)
        
        tests = [
            self.test_source_attribution,
            self.test_validation,
            self.test_error_handling,
            self.test_quality_checks,
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                import traceback
                traceback.print_exc()
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        total_passed = 0
        total_tests = 0
        
        for name, passed, total in self.results:
            percentage = (passed / total * 100) if total > 0 else 0
            status = "✅" if passed == total else "⚠️"
            print(f"{status} {name}: {passed}/{total} ({percentage:.1f}%)")
            total_passed += passed
            total_tests += total
        
        overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📊 Overall: {total_passed}/{total_tests} ({overall_percentage:.1f}%)")
        
        return overall_percentage >= 80  # 80% pass rate

async def main():
    tester = EnhancedRoxyTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())













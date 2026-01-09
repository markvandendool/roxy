#!/usr/bin/env python3
"""
Comprehensive ROXY Test Suite
Tests knowledge, coding ability, and agent functionality
"""
import sys
import asyncio
sys.path.insert(0, '/opt/roxy/services')

from roxy_interface import RoxyInterface
from roxy_core import RoxyMemory

class RoxyTester:
    def __init__(self):
        self.interface = RoxyInterface()
        self.memory = RoxyMemory()
        self.results = []
    
    async def test_knowledge(self):
        """Test 1: Knowledge Tests"""
        print("\n" + "="*70)
        print("TEST 1: KNOWLEDGE TESTS")
        print("="*70)
        
        knowledge_tests = [
            "What is Python?",
            "Explain recursion in programming",
            "What is the difference between REST and GraphQL?",
            "What is F# programming language?",
            "Explain the concept of dependency injection",
            "What is a neural network?",
            "What is the difference between SQL and NoSQL databases?",
            "Explain what Docker containers are",
            "What is the purpose of a reverse proxy?",
            "What is the difference between synchronous and asynchronous programming?"
        ]
        
        passed = 0
        for i, question in enumerate(knowledge_tests, 1):
            print(f"\n[{i}/{len(knowledge_tests)}] Q: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"ROXY: {response[:200]}...")
                
                # Check if response is intelligent (not fallback)
                if len(response) > 50 and "I understand you said" not in response:
                    passed += 1
                    print("✅ PASSED")
                else:
                    print("❌ FAILED - Generic response")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Knowledge Test Results: {passed}/{len(knowledge_tests)} passed")
        self.results.append(('Knowledge', passed, len(knowledge_tests)))
        return passed == len(knowledge_tests)
    
    async def test_coding_ability(self):
        """Test 2: Coding Ability Tests"""
        print("\n" + "="*70)
        print("TEST 2: CODING ABILITY TESTS")
        print("="*70)
        
        coding_tests = [
            {
                "question": "Write a Python function to calculate fibonacci numbers",
                "check": ["def", "fibonacci", "return"]
            },
            {
                "question": "How do you implement a binary search in Python?",
                "check": ["def", "binary", "search", "mid"]
            },
            {
                "question": "Write a function to reverse a linked list",
                "check": ["def", "reverse", "node", "next"]
            },
            {
                "question": "How do you handle exceptions in Python?",
                "check": ["try", "except", "Exception"]
            },
            {
                "question": "Write a Python decorator example",
                "check": ["def", "decorator", "@"]
            }
        ]
        
        passed = 0
        for i, test in enumerate(coding_tests, 1):
            print(f"\n[{i}/{len(coding_tests)}] Q: {test['question']}")
            try:
                response = await self.interface.chat_terminal(test['question'])
                print(f"ROXY: {response[:300]}...")
                
                # Check if response contains code concepts
                response_lower = response.lower()
                checks_passed = sum(1 for check in test['check'] if check.lower() in response_lower)
                
                if checks_passed >= len(test['check']) * 0.7:  # 70% of keywords
                    passed += 1
                    print(f"✅ PASSED ({checks_passed}/{len(test['check'])} keywords)")
                else:
                    print(f"❌ FAILED ({checks_passed}/{len(test['check'])} keywords)")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Coding Test Results: {passed}/{len(coding_tests)} passed")
        self.results.append(('Coding', passed, len(coding_tests)))
        return passed >= len(coding_tests) * 0.7  # 70% pass rate
    
    async def test_memory(self):
        """Test 3: Memory Tests"""
        print("\n" + "="*70)
        print("TEST 3: MEMORY TESTS")
        print("="*70)
        
        # Store some facts
        test_facts = [
            "My favorite color is blue",
            "I work on the mindsong-juke-hub project",
            "I prefer Python over JavaScript"
        ]
        
        print("\nStoring test facts...")
        for fact in test_facts:
            await self.interface.chat_terminal(fact)
        
        # Test recall
        print("\nTesting recall...")
        questions = [
            "What is my favorite color?",
            "What project do I work on?",
            "What programming language do I prefer?"
        ]
        
        passed = 0
        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Q: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"ROXY: {response[:200]}...")
                
                # Check if response references the fact
                if any(keyword.lower() in response.lower() for keyword in ["blue", "mindsong", "python"]):
                    passed += 1
                    print("✅ PASSED - Memory recalled")
                else:
                    print("❌ FAILED - Memory not recalled")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Memory Test Results: {passed}/{len(questions)} passed")
        self.results.append(('Memory', passed, len(questions)))
        return passed == len(questions)
    
    async def test_conversation_context(self):
        """Test 4: Conversation Context"""
        print("\n" + "="*70)
        print("TEST 4: CONVERSATION CONTEXT")
        print("="*70)
        
        # Have a conversation
        conversation = [
            "Hi ROXY, I'm working on a new feature",
            "It's a music player with real-time collaboration",
            "I need help with WebSocket connections"
        ]
        
        print("\nHaving conversation...")
        for msg in conversation:
            await self.interface.chat_terminal(msg)
        
        # Test context understanding
        context_questions = [
            "What am I working on?",
            "What technology do I need help with?",
            "What did we discuss just now?"
        ]
        
        passed = 0
        for i, question in enumerate(context_questions, 1):
            print(f"\n[{i}/{len(context_questions)}] Q: {question}")
            try:
                response = await self.interface.chat_terminal(question)
                print(f"ROXY: {response[:200]}...")
                
                # Check if response references conversation
                keywords = ["music", "player", "websocket", "collaboration", "feature"]
                if any(keyword.lower() in response.lower() for keyword in keywords):
                    passed += 1
                    print("✅ PASSED - Context understood")
                else:
                    print("❌ FAILED - Context not understood")
            except Exception as e:
                print(f"❌ ERROR: {e}")
        
        print(f"\n📊 Context Test Results: {passed}/{len(context_questions)} passed")
        self.results.append(('Context', passed, len(context_questions)))
        return passed >= len(context_questions) * 0.7
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE ROXY TEST SUITE")
        print("="*70)
        
        tests = [
            ("Knowledge", self.test_knowledge),
            ("Coding", self.test_coding_ability),
            ("Memory", self.test_memory),
            ("Context", self.test_conversation_context)
        ]
        
        all_passed = True
        for name, test_func in tests:
            try:
                result = await test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Test {name} crashed: {e}")
                all_passed = False
        
        # Print summary
        print("\n" + "="*70)
        print("📊 FINAL RESULTS")
        print("="*70)
        for name, passed, total in self.results:
            percentage = (passed / total) * 100
            status = "✅ PASS" if percentage >= 70 else "❌ FAIL"
            print(f"{name:15} {status:6} {passed:2}/{total:2} ({percentage:5.1f}%)")
        
        overall = sum(p for _, p, _ in self.results) / sum(t for _, _, t in self.results) * 100
        print(f"\nOverall: {overall:.1f}%")
        
        if overall >= 70:
            print("\n✅ ROXY PASSED COMPREHENSIVE TESTS!")
            return True
        else:
            print("\n❌ ROXY FAILED - Needs improvement")
            return False

async def main():
    tester = RoxyTester()
    passed = await tester.run_all_tests()
    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    asyncio.run(main())




















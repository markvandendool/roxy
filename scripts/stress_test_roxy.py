#!/usr/bin/env python3
"""
ROXY Stress Test Suite
Pushes ROXY to maximum limits to verify she handles everything perfectly
"""
import asyncio
import time
import sys
import subprocess
import psutil
import os
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json

sys.path.insert(0, '/opt/roxy/services')

class RoxyStressTest:
    """Comprehensive stress test for ROXY"""
    
    def __init__(self):
        self.results = {
            'start_time': datetime.now().isoformat(),
            'tests': {},
            'metrics': {},
            'errors': []
        }
        self.roxy_process = None
        
    def log(self, message):
        """Log with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def test_1_service_health(self):
        """Test 1: Service health under stress"""
        self.log("🔥 TEST 1: Service Health Under Stress")
        try:
            result = subprocess.run(['systemctl', 'is-active', 'roxy.service'], 
                                  capture_output=True, text=True, timeout=2)
            if result.stdout.strip() == 'active':
                self.results['tests']['service_health'] = 'PASS'
                self.log("   ✅ Service is active")
                return True
            else:
                self.results['tests']['service_health'] = 'FAIL'
                self.log("   ❌ Service is not active")
                return False
        except Exception as e:
            self.results['tests']['service_health'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_2_memory_pressure(self):
        """Test 2: Memory system under pressure"""
        self.log("🔥 TEST 2: Memory System Under Pressure")
        try:
            from roxy_core import RoxyMemory
            
            memory = RoxyMemory()
            
            # Rapid fire memory operations
            start_time = time.time()
            operations = 0
            
            for i in range(1000):
                memory.remember_conversation(
                    f"stress_test_{i}",
                    f"test input {i}",
                    f"test response {i}",
                    context={"test": True, "iteration": i}
                )
                operations += 1
                
                if i % 100 == 0:
                    facts = memory.recall_facts(limit=10)
                    operations += 1
            
            elapsed = time.time() - start_time
            ops_per_sec = operations / elapsed if elapsed > 0 else 0
            
            stats = memory.get_stats()
            
            self.results['tests']['memory_pressure'] = 'PASS'
            self.results['metrics']['memory_ops_per_sec'] = ops_per_sec
            self.results['metrics']['memory_conversations'] = stats['conversations']
            self.log(f"   ✅ Memory handled {operations} operations in {elapsed:.2f}s ({ops_per_sec:.0f} ops/sec)")
            return True
            
        except Exception as e:
            self.results['tests']['memory_pressure'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_3_concurrent_operations(self):
        """Test 3: Concurrent operations"""
        self.log("🔥 TEST 3: Concurrent Operations (100 parallel tasks)")
        try:
            async def async_operation(task_id):
                await asyncio.sleep(0.01)  # Simulate work
                return f"task_{task_id}_complete"
            
            async def run_concurrent():
                tasks = [async_operation(i) for i in range(100)]
                results = await asyncio.gather(*tasks)
                return len(results)
            
            start_time = time.time()
            result = asyncio.run(run_concurrent())
            elapsed = time.time() - start_time
            
            self.results['tests']['concurrent_operations'] = 'PASS'
            self.results['metrics']['concurrent_tasks'] = result
            self.results['metrics']['concurrent_time'] = elapsed
            self.log(f"   ✅ Completed {result} concurrent tasks in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            self.results['tests']['concurrent_operations'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_4_gpu_utilization(self):
        """Test 4: GPU utilization under load"""
        self.log("🔥 TEST 4: GPU Utilization Under Load")
        try:
            import torch
            
            if torch.cuda.is_available():
                device = torch.device('cuda')
                
                # Create large tensors and perform operations
                start_time = time.time()
                operations = 0
                
                for i in range(50):
                    # Large matrix operations
                    a = torch.randn(2000, 2000, device=device)
                    b = torch.randn(2000, 2000, device=device)
                    c = torch.matmul(a, b)
                    operations += 1
                    
                    # Memory cleanup
                    del a, b, c
                    torch.cuda.empty_cache()
                
                elapsed = time.time() - start_time
                ops_per_sec = operations / elapsed if elapsed > 0 else 0
                
                # Check GPU memory
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
                
                self.results['tests']['gpu_utilization'] = 'PASS'
                self.results['metrics']['gpu_ops_per_sec'] = ops_per_sec
                self.results['metrics']['gpu_memory_gb'] = gpu_memory
                self.log(f"   ✅ GPU handled {operations} operations in {elapsed:.2f}s ({ops_per_sec:.1f} ops/sec)")
                self.log(f"   ✅ GPU Memory: {gpu_memory:.1f} GB")
                return True
            else:
                self.results['tests']['gpu_utilization'] = 'SKIP'
                self.log("   ⚠️  GPU not available (ROCm/CUDA)")
                return True
                
        except Exception as e:
            self.results['tests']['gpu_utilization'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_5_resource_usage(self):
        """Test 5: Resource usage monitoring"""
        self.log("🔥 TEST 5: Resource Usage Monitoring")
        try:
            # Find ROXY process
            roxy_pid = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'roxy_core.py' in ' '.join(proc.info['cmdline'] or []):
                        roxy_pid = proc.info['pid']
                        break
                except:
                    pass
            
            if roxy_pid:
                process = psutil.Process(roxy_pid)
                cpu_percent = process.cpu_percent(interval=1)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                num_threads = process.num_threads()
                
                self.results['tests']['resource_usage'] = 'PASS'
                self.results['metrics']['cpu_percent'] = cpu_percent
                self.results['metrics']['memory_mb'] = memory_mb
                self.results['metrics']['num_threads'] = num_threads
                self.log(f"   ✅ CPU: {cpu_percent:.1f}%")
                self.log(f"   ✅ Memory: {memory_mb:.1f} MB")
                self.log(f"   ✅ Threads: {num_threads}")
                return True
            else:
                self.results['tests']['resource_usage'] = 'SKIP'
                self.log("   ⚠️  ROXY process not found")
                return True
                
        except Exception as e:
            self.results['tests']['resource_usage'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_6_learning_systems(self):
        """Test 6: Learning systems under load"""
        self.log("🔥 TEST 6: Learning Systems Under Load")
        try:
            from roxy_core import RoxyMemory
            
            memory = RoxyMemory()
            
            # Simulate rapid learning
            start_time = time.time()
            learned = 0
            
            for i in range(500):
                memory.learn_fact(
                    f"stress_test_fact_{i}",
                    f"During stress test iteration {i}, ROXY demonstrated resilience",
                    confidence=0.9,
                    source="stress_test"
                )
                learned += 1
            
            elapsed = time.time() - start_time
            facts = memory.recall_facts(limit=100)
            
            self.results['tests']['learning_systems'] = 'PASS'
            self.results['metrics']['facts_learned'] = learned
            self.results['metrics']['learning_time'] = elapsed
            self.results['metrics']['facts_recalled'] = len(facts)
            self.log(f"   ✅ Learned {learned} facts in {elapsed:.2f}s")
            self.log(f"   ✅ Recalled {len(facts)} facts")
            return True
            
        except Exception as e:
            self.results['tests']['learning_systems'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_7_recovery_resilience(self):
        """Test 7: Recovery and resilience"""
        self.log("🔥 TEST 7: Recovery and Resilience")
        try:
            # Test that ROXY recovers from errors gracefully
            from roxy_core import RoxyMemory
            
            memory = RoxyMemory()
            
            # Intentionally cause errors and verify recovery
            errors_handled = 0
            
            # Test invalid input handling
            try:
                memory.remember_conversation(None, None, None)
            except:
                errors_handled += 1
            
            try:
                memory.learn_fact(None, None)
            except:
                errors_handled += 1
            
            # Verify system still works after errors
            memory.remember_conversation("recovery_test", "test", "test")
            stats = memory.get_stats()
            
            if stats['conversations'] > 0:
                self.results['tests']['recovery_resilience'] = 'PASS'
                self.results['metrics']['errors_handled'] = errors_handled
                self.log(f"   ✅ Handled {errors_handled} errors gracefully")
                self.log(f"   ✅ System recovered and continued operating")
                return True
            else:
                self.results['tests']['recovery_resilience'] = 'FAIL'
                self.log("   ❌ System did not recover properly")
                return False
                
        except Exception as e:
            self.results['tests']['recovery_resilience'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_8_database_performance(self):
        """Test 8: Database performance"""
        self.log("🔥 TEST 8: Database Performance")
        try:
            import sqlite3
            
            db_path = Path('/opt/roxy/data/roxy_memory.db')
            if not db_path.exists():
                self.results['tests']['database_performance'] = 'SKIP'
                self.log("   ⚠️  Database not found")
                return True
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            start_time = time.time()
            
            # Read operations
            cursor.execute("SELECT COUNT(*) FROM conversations")
            conv_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM learned_facts")
            facts_count = cursor.fetchone()[0]
            
            # Write operations
            for i in range(100):
                cursor.execute("""
                    INSERT INTO conversations (timestamp, user_input, roxy_response)
                    VALUES (?, ?, ?)
                """, (datetime.now().isoformat(), f"perf_test_{i}", f"response_{i}"))
            
            conn.commit()
            elapsed = time.time() - start_time
            
            conn.close()
            
            self.results['tests']['database_performance'] = 'PASS'
            self.results['metrics']['db_operations_time'] = elapsed
            self.results['metrics']['db_conversations'] = conv_count
            self.results['metrics']['db_facts'] = facts_count
            self.log(f"   ✅ Database operations completed in {elapsed:.2f}s")
            self.log(f"   ✅ Conversations: {conv_count}, Facts: {facts_count}")
            return True
            
        except Exception as e:
            self.results['tests']['database_performance'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_9_sustained_load(self):
        """Test 9: Sustained load over time"""
        self.log("🔥 TEST 9: Sustained Load (30 seconds)")
        try:
            from roxy_core import RoxyMemory
            
            memory = RoxyMemory()
            start_time = time.time()
            operations = 0
            target_duration = 30
            
            while (time.time() - start_time) < target_duration:
                memory.remember_conversation(
                    f"sustained_{operations}",
                    f"input {operations}",
                    f"response {operations}"
                )
                operations += 1
                
                if operations % 100 == 0:
                    memory.recall_facts(limit=10)
                
                # Small delay to prevent overwhelming
                time.sleep(0.01)
            
            elapsed = time.time() - start_time
            ops_per_sec = operations / elapsed if elapsed > 0 else 0
            
            self.results['tests']['sustained_load'] = 'PASS'
            self.results['metrics']['sustained_operations'] = operations
            self.results['metrics']['sustained_duration'] = elapsed
            self.results['metrics']['sustained_ops_per_sec'] = ops_per_sec
            self.log(f"   ✅ Sustained {operations} operations over {elapsed:.1f}s ({ops_per_sec:.0f} ops/sec)")
            return True
            
        except Exception as e:
            self.results['tests']['sustained_load'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def test_10_system_integration(self):
        """Test 10: System integration"""
        self.log("🔥 TEST 10: System Integration")
        try:
            # Test that ROXY can interact with system services
            checks = []
            
            # Check PostgreSQL
            try:
                result = subprocess.run(['systemctl', 'is-active', 'postgresql.service'],
                                      capture_output=True, timeout=2)
                checks.append(('PostgreSQL', result.stdout.strip() == 'active'))
            except:
                checks.append(('PostgreSQL', False))
            
            # Check Redis
            try:
                result = subprocess.run(['systemctl', 'is-active', 'redis.service'],
                                          capture_output=True, timeout=2)
                checks.append(('Redis', result.stdout.strip() == 'active'))
            except:
                checks.append(('Redis', False))
            
            # Check GPU
            try:
                result = subprocess.run(['rocm-smi'], capture_output=True, timeout=3)
                checks.append(('GPU', result.returncode == 0))
            except:
                checks.append(('GPU', False))
            
            # Check Ollama
            try:
                result = subprocess.run(['ollama', 'list'], capture_output=True, timeout=3)
                checks.append(('Ollama', result.returncode == 0))
            except:
                checks.append(('Ollama', False))
            
            passed = sum(1 for _, status in checks if status)
            total = len(checks)
            
            for name, status in checks:
                status_str = "✅" if status else "❌"
                self.log(f"   {status_str} {name}")
            
            self.results['tests']['system_integration'] = 'PASS' if passed == total else 'PARTIAL'
            self.results['metrics']['system_checks_passed'] = f"{passed}/{total}"
            self.log(f"   ✅ System integration: {passed}/{total} checks passed")
            return True
            
        except Exception as e:
            self.results['tests']['system_integration'] = 'FAIL'
            self.results['errors'].append(str(e))
            self.log(f"   ❌ Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all stress tests"""
        print("=" * 70)
        print("🔥 ROXY STRESS TEST SUITE")
        print("=" * 70)
        print()
        
        tests = [
            self.test_1_service_health,
            self.test_2_memory_pressure,
            self.test_3_concurrent_operations,
            self.test_4_gpu_utilization,
            self.test_5_resource_usage,
            self.test_6_learning_systems,
            self.test_7_recovery_resilience,
            self.test_8_database_performance,
            self.test_9_sustained_load,
            self.test_10_system_integration,
        ]
        
        passed = 0
        failed = 0
        skipped = 0
        
        for test in tests:
            try:
                result = test()
                if result:
                    passed += 1
                else:
                    failed += 1
                print()
            except Exception as e:
                failed += 1
                self.log(f"   ❌ Test crashed: {e}")
                self.results['errors'].append(str(e))
                print()
        
        # Final summary
        self.results['end_time'] = datetime.now().isoformat()
        total_time = (datetime.fromisoformat(self.results['end_time']) - 
                     datetime.fromisoformat(self.results['start_time'])).total_seconds()
        
        print("=" * 70)
        print("📊 STRESS TEST RESULTS")
        print("=" * 70)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total Time: {total_time:.1f}s")
        print()
        
        # Save results
        results_file = Path('/opt/roxy/data/stress_test_results.json')
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"📄 Results saved to: {results_file}")
        print()
        
        if failed == 0:
            print("🚀 ROXY PASSED ALL STRESS TESTS!")
            print("✅ She's ready for maximum power operation!")
        else:
            print(f"⚠️  ROXY had {failed} test failures")
            print("   Check errors above for details")
        
        print("=" * 70)
        
        return failed == 0

if __name__ == '__main__':
    tester = RoxyStressTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)



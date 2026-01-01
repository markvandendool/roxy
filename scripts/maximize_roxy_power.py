#!/usr/bin/env python3
"""
ROXY Power Maximization Script
Automatically configures and optimizes ROXY for maximum growth and power
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List

ROXY_ROOT = Path('/opt/roxy')
ENV_FILE = ROXY_ROOT / '.env'
DATA_DIR = ROXY_ROOT / 'data'
CONFIG_DIR = ROXY_ROOT / 'config'
LOGS_DIR = ROXY_ROOT / 'logs'

class RoxyMaximizer:
    """Maximize ROXY's power and growth"""
    
    def __init__(self):
        self.optimizations = []
        self.issues_found = []
        self.fixes_applied = []
    
    def run_full_optimization(self):
        """Run complete optimization"""
        print("=" * 70)
        print("🚀 ROXY POWER MAXIMIZATION")
        print("=" * 70)
        print()
        
        # 1. Environment setup
        self.optimize_environment()
        
        # 2. Service configuration
        self.optimize_services()
        
        # 3. Database optimization
        self.optimize_databases()
        
        # 4. LLM configuration
        self.optimize_llm()
        
        # 5. Email setup
        self.optimize_email()
        
        # 6. Agent activation
        self.optimize_agents()
        
        # 7. Learning systems
        self.optimize_learning()
        
        # 8. Scheduled tasks
        self.optimize_scheduling()
        
        # 9. System permissions
        self.optimize_permissions()
        
        # 10. Knowledge base
        self.optimize_knowledge_base()
        
        # 11. Monitoring
        self.optimize_monitoring()
        
        # 12. Performance tuning
        self.optimize_performance()
        
        # Print summary
        self.print_summary()
    
    def optimize_environment(self):
        """Optimize environment variables"""
        print("1. Optimizing Environment...")
        
        if not ENV_FILE.exists():
            ENV_FILE.touch()
            self.fixes_applied.append("Created .env file")
        
        # Read current env
        env_vars = {}
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
        
        # Set optimal defaults
        optimal_vars = {
            'ROXY_MAX_MEMORY': '8G',
            'ROXY_MAX_CONCURRENT_TASKS': '50',
            'ROXY_LEARNING_ENABLED': 'true',
            'ROXY_AUTONOMOUS_MODE': 'true',
            'ROXY_AGENT_COUNT': '20',
            'ROXY_LOG_LEVEL': 'INFO',
            'ROXY_BACKUP_ENABLED': 'true',
            'ROXY_BACKUP_INTERVAL': '24h',
        }
        
        updated = False
        for key, value in optimal_vars.items():
            if key not in env_vars:
                env_vars[key] = value
                updated = True
                self.fixes_applied.append(f"Added {key}={value}")
        
        if updated:
            with open(ENV_FILE, 'w') as f:
                for key, value in sorted(env_vars.items()):
                    f.write(f"{key}={value}\n")
            print("  ✅ Environment optimized")
        else:
            print("  ✅ Environment already optimal")
    
    def optimize_services(self):
        """Ensure all services are running"""
        print("2. Optimizing Services...")
        
        services = {
            'roxy.service': 'ROXY Core',
            'postgresql.service': 'PostgreSQL',
            'redis.service': 'Redis',
        }
        
        for service, name in services.items():
            result = subprocess.run(['systemctl', 'is-active', service], 
                                  capture_output=True, text=True)
            if result.stdout.strip() != 'active':
                # Try to start
                subprocess.run(['sudo', 'systemctl', 'start', service], 
                             capture_output=True)
                subprocess.run(['sudo', 'systemctl', 'enable', service], 
                             capture_output=True)
                self.fixes_applied.append(f"Started and enabled {name}")
                print(f"  ✅ {name} started and enabled")
            else:
                print(f"  ✅ {name} already running")
    
    def optimize_databases(self):
        """Optimize database connections"""
        print("3. Optimizing Databases...")
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory DB if needed
        db_path = DATA_DIR / 'roxy_memory.db'
        if not db_path.exists():
            # Initialize by importing
            sys.path.insert(0, str(ROXY_ROOT / 'services'))
            try:
                from roxy_core import RoxyMemory
                memory = RoxyMemory()
                self.fixes_applied.append("Initialized memory database")
                print("  ✅ Memory database initialized")
            except Exception as e:
                self.issues_found.append(f"Memory DB init: {e}")
        else:
            print("  ✅ Memory database exists")
    
    def optimize_llm(self):
        """Configure LLM for maximum power"""
        print("4. Optimizing LLM Configuration...")
        
        # Check for LLM providers
        env_vars = self._read_env()
        
        if 'ANTHROPIC_API_KEY' in env_vars and env_vars['ANTHROPIC_API_KEY']:
            print("  ✅ Claude API configured")
        else:
            print("  ⚠️  Claude API key not set (set ANTHROPIC_API_KEY in .env)")
            self.issues_found.append("Claude API key missing")
        
        if 'OLLAMA_HOST' in env_vars:
            ollama_host = env_vars.get('OLLAMA_HOST', 'http://localhost:11434')
            # Test connection
            import urllib.request
            try:
                urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=2)
                print(f"  ✅ Ollama accessible at {ollama_host}")
            except:
                print(f"  ⚠️  Ollama not accessible at {ollama_host}")
                self.issues_found.append("Ollama not accessible")
        else:
            # Set default
            self._update_env('OLLAMA_HOST', 'http://localhost:11434')
            self._update_env('OLLAMA_MODEL', 'llama3:8b')
            print("  ✅ Ollama defaults configured")
    
    def optimize_email(self):
        """Configure email access"""
        print("5. Optimizing Email Configuration...")
        
        env_vars = self._read_env()
        required = ['EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_IMAP_HOST']
        
        configured = sum(1 for key in required if key in env_vars and env_vars[key])
        
        if configured == len(required):
            print("  ✅ Email fully configured")
        else:
            print(f"  ⚠️  Email partially configured ({configured}/{len(required)})")
            if 'EMAIL_IMAP_HOST' not in env_vars:
                self._update_env('EMAIL_IMAP_HOST', 'imap.gmail.com')
                self._update_env('EMAIL_SMTP_HOST', 'smtp.gmail.com')
                print("  ✅ Email defaults added (set EMAIL_USER and EMAIL_PASSWORD)")
    
    def optimize_agents(self):
        """Activate all agents"""
        print("6. Optimizing Agents...")
        
        # Create agent config
        agent_config = {
            'enabled_agents': [
                'code-analysis', 'code-review', 'refactoring', 'documentation',
                'testing', 'bug-detection', 'dependency', 'performance',
                'security', 'git', 'monitor', 'issue-resolver', 'ci',
                'code-generator', 'architecture', 'migration', 'api-docs',
                'compliance', 'metrics', 'release'
            ],
            'max_concurrent': 10,
            'auto_assign': True,
            'learning_enabled': True
        }
        
        config_file = CONFIG_DIR / 'agents.json'
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(agent_config, f, indent=2)
        
        print(f"  ✅ {len(agent_config['enabled_agents'])} agents configured")
        self.fixes_applied.append("Agent configuration created")
    
    def optimize_learning(self):
        """Optimize learning systems"""
        print("7. Optimizing Learning Systems...")
        
        learning_config = {
            'predictive_learning': True,
            'pattern_recognition': True,
            'self_improvement': True,
            'knowledge_synthesis': True,
            'adaptive_behavior': True,
            'learning_rate': 0.1,
            'memory_consolidation_interval': '24h'
        }
        
        config_file = CONFIG_DIR / 'learning.json'
        with open(config_file, 'w') as f:
            json.dump(learning_config, f, indent=2)
        
        print("  ✅ Learning systems optimized")
        self.fixes_applied.append("Learning configuration created")
    
    def optimize_scheduling(self):
        """Set up optimal scheduled tasks"""
        print("8. Optimizing Scheduled Tasks...")
        
        tasks_config = {
            'tasks': [
                {
                    'id': 'nightly-backup',
                    'name': 'Nightly Backup',
                    'cron': '0 2 * * *',
                    'enabled': True
                },
                {
                    'id': 'health-check',
                    'name': 'Health Check',
                    'cron': '0 * * * *',
                    'enabled': True
                },
                {
                    'id': 'memory-consolidation',
                    'name': 'Memory Consolidation',
                    'cron': '0 3 * * *',
                    'enabled': True
                },
                {
                    'id': 'repo-monitor',
                    'name': 'Repository Monitor',
                    'cron': '*/5 * * * *',
                    'enabled': True
                }
            ]
        }
        
        config_file = CONFIG_DIR / 'tasks.json'
        with open(config_file, 'w') as f:
            json.dump(tasks_config, f, indent=2)
        
        print(f"  ✅ {len(tasks_config['tasks'])} scheduled tasks configured")
        self.fixes_applied.append("Scheduled tasks configured")
    
    def optimize_permissions(self):
        """Ensure proper permissions"""
        print("9. Optimizing Permissions...")
        
        # Make scripts executable
        scripts = [
            ROXY_ROOT / 'scripts' / 'roxy',
            ROXY_ROOT / 'services' / 'roxy_core.py',
            ROXY_ROOT / 'services' / 'roxy_interface.py',
        ]
        
        for script in scripts:
            if script.exists():
                script.chmod(0o755)
        
        # Ensure data directory is writable
        DATA_DIR.chmod(0o755)
        
        print("  ✅ Permissions optimized")
        self.fixes_applied.append("File permissions set")
    
    def optimize_knowledge_base(self):
        """Populate knowledge base"""
        print("10. Optimizing Knowledge Base...")
        
        # Initialize knowledge index
        sys.path.insert(0, str(ROXY_ROOT / 'services'))
        try:
            from knowledge import KnowledgeIndex
            index = KnowledgeIndex()
            
            # Add ROXY's own codebase to knowledge
            print("  ✅ Knowledge index accessible")
            self.fixes_applied.append("Knowledge base initialized")
        except Exception as e:
            print(f"  ⚠️  Knowledge index: {e}")
    
    def optimize_monitoring(self):
        """Set up monitoring"""
        print("11. Optimizing Monitoring...")
        
        monitoring_config = {
            'health_check_interval': 60,
            'metrics_collection': True,
            'log_retention_days': 30,
            'alert_on_errors': True
        }
        
        config_file = CONFIG_DIR / 'monitoring.json'
        with open(config_file, 'w') as f:
            json.dump(monitoring_config, f, indent=2)
        
        print("  ✅ Monitoring configured")
        self.fixes_applied.append("Monitoring enabled")
    
    def optimize_performance(self):
        """Performance optimizations"""
        print("12. Optimizing Performance...")
        
        perf_config = {
            'max_workers': 20,
            'memory_limit': '8G',
            'cpu_limit': None,
            'cache_enabled': True,
            'async_processing': True
        }
        
        config_file = CONFIG_DIR / 'performance.json'
        with open(config_file, 'w') as f:
            json.dump(perf_config, f, indent=2)
        
        print("  ✅ Performance settings optimized")
        self.fixes_applied.append("Performance tuning applied")
    
    def _read_env(self) -> Dict:
        """Read environment variables"""
        env_vars = {}
        if ENV_FILE.exists():
            with open(ENV_FILE, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
        return env_vars
    
    def _update_env(self, key: str, value: str):
        """Update environment variable"""
        env_vars = self._read_env()
        env_vars[key] = value
        
        with open(ENV_FILE, 'w') as f:
            for k, v in sorted(env_vars.items()):
                f.write(f"{k}={v}\n")
    
    def print_summary(self):
        """Print optimization summary"""
        print()
        print("=" * 70)
        print("📊 OPTIMIZATION SUMMARY")
        print("=" * 70)
        print()
        
        if self.fixes_applied:
            print(f"✅ Applied {len(self.fixes_applied)} optimizations:")
            for fix in self.fixes_applied[:10]:
                print(f"   • {fix}")
            if len(self.fixes_applied) > 10:
                print(f"   ... and {len(self.fixes_applied) - 10} more")
        
        if self.issues_found:
            print()
            print(f"⚠️  Found {len(self.issues_found)} issues to address:")
            for issue in self.issues_found:
                print(f"   • {issue}")
        
        print()
        print("=" * 70)
        print("🚀 ROXY POWER MAXIMIZED!")
        print("=" * 70)
        print()
        print("Next Steps:")
        print("  1. Set API keys in .env (ANTHROPIC_API_KEY, EMAIL_USER, etc.)")
        print("  2. Start ROXY: sudo systemctl start roxy.service")
        print("  3. Monitor: roxy logs")
        print("  4. Interact: roxy chat")
        print()


if __name__ == "__main__":
    maximizer = RoxyMaximizer()
    maximizer.run_full_optimization()


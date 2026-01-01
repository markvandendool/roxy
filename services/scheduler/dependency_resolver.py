#!/usr/bin/env python3
"""
ROXY Task Dependency Resolver - Handle task dependencies
"""
import logging
from typing import Dict, List, Set
from collections import defaultdict, deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('roxy.scheduler.dependency')

class DependencyResolver:
    """Resolve task dependencies"""
    
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = defaultdict(list)
        self.dependents: Dict[str, List[str]] = defaultdict(list)
    
    def add_dependency(self, task_id: str, depends_on: List[str]):
        """Add task dependencies"""
        self.dependencies[task_id] = depends_on
        for dep in depends_on:
            self.dependents[dep].append(task_id)
        logger.info(f"Task {task_id} depends on: {depends_on}")
    
    def get_execution_order(self, task_ids: List[str]) -> List[str]:
        """Get execution order respecting dependencies (topological sort)"""
        # Build graph
        in_degree = {task: 0 for task in task_ids}
        graph = defaultdict(list)
        
        for task in task_ids:
            for dep in self.dependencies.get(task, []):
                if dep in task_ids:
                    graph[dep].append(task)
                    in_degree[task] += 1
        
        # Topological sort
        queue = deque([task for task in task_ids if in_degree[task] == 0])
        result = []
        
        while queue:
            task = queue.popleft()
            result.append(task)
            
            for dependent in graph[task]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Check for cycles
        if len(result) != len(task_ids):
            logger.warning("Circular dependency detected!")
            return task_ids  # Return original order if cycle detected
        
        return result
    
    def can_run(self, task_id: str, completed_tasks: Set[str]) -> bool:
        """Check if task can run (all dependencies completed)"""
        deps = self.dependencies.get(task_id, [])
        return all(dep in completed_tasks for dep in deps)











"""
DEPENDENCY GRAPH ENGINE
Maps relationships between scripts, scenes, and resources.
Enables safe refactoring and impact analysis.
"""

import os
import re
from typing import Dict, Set, List, Optional, Tuple
from collections import defaultdict
import json

class DependencyGraph:
    def __init__(self):
        # script_path -> set of scripts that import/preload it
        self.dependents: Dict[str, Set[str]] = defaultdict(set)
        # script_path -> set of scripts/resources it depends on
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        # scene_path -> set of scripts attached to nodes in this scene
        self.scene_scripts: Dict[str, Set[str]] = defaultdict(set)
        # script_path -> set of scenes that use this script
        self.script_scenes: Dict[str, Set[str]] = defaultdict(set)
        # All known files
        self.all_files: Set[str] = set()
        
    def load_project(self, project_path: str) -> int:
        """Scan entire project and build dependency graph."""
        self.clear()
        file_count = 0
        
        for root, _, files in os.walk(project_path):
            # Skip hidden folders and imports
            if '.godot' in root or 'imports' in root:
                continue
                
            for file in files:
                filepath = os.path.join(root, file)
                self.all_files.add(filepath)
                
                if file.endswith('.gd'):
                    self._parse_script(filepath)
                    file_count += 1
                elif file.endswith('.tscn'):
                    self._parse_scene(filepath)
                    file_count += 1
                    
        return file_count
        
    def clear(self):
        """Reset the graph."""
        self.dependents.clear()
        self.dependencies.clear()
        self.scene_scripts.clear()
        self.script_scenes.clear()
        self.all_files.clear()
        
    def _parse_script(self, filepath: str):
        """Parse a .gd file to find dependencies."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return
            
        # Pattern 1: extends "res://path/to/script.gd"
        extends_match = re.search(r'extends\s+["\']?(res://[^"\'\s]+)["\']?', content)
        if extends_match:
            dep_path = self._resolve_path(extends_match.group(1), filepath)
            if dep_path:
                self.dependencies[filepath].add(dep_path)
                self.dependents[dep_path].add(filepath)
                
        # Pattern 2: preload("res://...")
        for match in re.finditer(r'preload\s*\(\s*["\'](res://[^"\']+)["\']\s*\)', content):
            dep_path = self._resolve_path(match.group(1), filepath)
            if dep_path:
                self.dependencies[filepath].add(dep_path)
                self.dependents[dep_path].add(filepath)
                
        # Pattern 3: load("res://...") - dynamic but still a dependency
        for match in re.finditer(r'load\s*\(\s*["\'](res://[^"\']+)["\']\s*\)', content):
            dep_path = self._resolve_path(match.group(1), filepath)
            if dep_path:
                self.dependencies[filepath].add(dep_path)
                # Don't add to dependents for load() as it's dynamic
                
        # Pattern 4: Signal connections (basic detection)
        # Looks for: node.connect("signal", self, "_method")
        # This is hard to resolve statically, so we skip for now
        
    def _parse_scene(self, filepath: str):
        """Parse a .tscn file to find attached scripts."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return
            
        # Pattern: script = "res://path/to/script.gd"
        for match in re.finditer(r'script\s*=\s*["\'](res://[^"\']+)["\']', content):
            script_path = self._resolve_path(match.group(1), filepath)
            if script_path:
                self.scene_scripts[filepath].add(script_path)
                self.script_scenes[script_path].add(filepath)
                
    def _resolve_path(self, res_path: str, source_file: str) -> Optional[str]:
        """Convert res:// path to absolute filesystem path."""
        if not res_path.startswith('res://'):
            return None
            
        # Find project root (folder containing .godot folder or based on source)
        # Simple approach: assume res:// is relative to some common root
        # In practice, we need the actual project root passed in
        
        # For now, we'll store the res:// path and resolve later if needed
        # Or assume the user loaded a project where res:// maps to root
        return res_path  # Return as-is for now, can be resolved later
        
    def get_impact_analysis(self, file_path: str) -> Dict:
        """Analyze what breaks if this file changes."""
        direct_dependents = self.dependents.get(file_path, set())
        scenes_using = self.script_scenes.get(file_path, set())
        
        # Recursive dependents (files that depend on files that depend on this)
        all_affected = set(direct_dependents)
        queue = list(direct_dependents)
        visited = set(direct_dependents)
        
        while queue:
            current = queue.pop(0)
            for dependent in self.dependents.get(current, set()):
                if dependent not in visited:
                    visited.add(dependent)
                    all_affected.add(dependent)
                    queue.append(dependent)
                    
        return {
            'file': file_path,
            'direct_dependents': list(direct_dependents),
            'scenes_affected': list(scenes_using),
            'total_affected': len(all_affected),
            'all_affected_files': list(all_affected),
            'risk_level': 'HIGH' if len(all_affected) > 5 else 'MEDIUM' if len(all_affected) > 2 else 'LOW'
        }
        
    def get_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies (A->B->A)."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependencies.get(node, set()):
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
                    
            path.pop()
            rec_stack.remove(node)
            return None
            
        for node in self.all_files:
            if node.endswith('.gd') and node not in visited:
                cycle = dfs(node)
                if cycle:
                    cycles.append(cycle)
                    
        return cycles
        
    def export_to_json(self, output_path: str):
        """Export graph data for external tools."""
        data = {
            'dependencies': {k: list(v) for k, v in self.dependencies.items()},
            'dependents': {k: list(v) for k, v in self.dependents.items()},
            'scene_scripts': {k: list(v) for k, v in self.scene_scripts.items()},
            'script_scenes': {k: list(v) for k, v in self.script_scenes.items()},
            'circular_deps': self.get_circular_dependencies()
        }
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
            
    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            'total_files': len(self.all_files),
            'scripts': sum(1 for f in self.all_files if f.endswith('.gd')),
            'scenes': sum(1 for f in self.all_files if f.endswith('.tscn')),
            'total_dependencies': sum(len(deps) for deps in self.dependencies.values()),
            'circular_dependencies': len(self.get_circular_dependencies()),
            'most_depended_on': self._get_most_depended_on()
        }
        
    def _get_most_depended_on(self) -> List[Tuple[str, int]]:
        """Find the top 5 most imported scripts."""
        counts = [(f, len(deps)) for f, deps in self.dependents.items()]
        counts.sort(key=lambda x: x[1], reverse=True)
        return counts[:5]

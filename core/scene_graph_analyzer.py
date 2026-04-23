"""
Scene Graph Analyzer for Godot Projects
Parses .tscn files to understand node hierarchies, script attachments, and connections.
Provides deep insight into how scenes are structured and connected.
"""

import re
import os
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NodeInfo:
    """Represents a single node in a scene."""
    name: str
    type: str
    parent: Optional[str] = None
    script_path: Optional[str] = None
    children: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    signals: List[Dict[str, str]] = field(default_factory=list)
    connections: List[Dict[str, str]] = field(default_factory=list)
    
    def get_full_path(self, path_map: Dict[str, str]) -> str:
        """Get the full node path (e.g., 'Root/Player/Sprite')."""
        if self.parent is None:
            return self.name
        
        parts = [self.name]
        current = self.parent
        while current:
            parts.append(current)
            # Find parent's parent
            parent_info = path_map.get(current)
            if parent_info and hasattr(parent_info, 'parent'):
                current = parent_info.parent
            else:
                break
        
        return '/'.join(reversed(parts))


@dataclass
class SceneInfo:
    """Represents a complete scene file."""
    path: str
    root_node_type: str
    nodes: Dict[str, NodeInfo] = field(default_factory=dict)
    scripts: Dict[str, str] = field(default_factory=dict)  # node_name -> script_path
    resources: Dict[str, str] = field(default_factory=dict)  # resource_id -> path
    missing_resources: List[str] = field(default_factory=list)
    orphaned_nodes: List[str] = field(default_factory=list)
    
    @property
    def node_count(self) -> int:
        return len(self.nodes)
    
    @property
    def script_count(self) -> int:
        return len(self.scripts)


class SceneGraphAnalyzer:
    """
    Analyzes Godot scene files (.tscn) to build a complete graph of:
    - Node hierarchies
    - Script attachments
    - Resource dependencies
    - Signal connections
    
    Works alongside DependencyGraph for full project awareness.
    """
    
    def __init__(self):
        self.scenes: Dict[str, SceneInfo] = {}
        self.node_to_scene: Dict[str, str] = {}  # node_name -> scene_path
        self.script_to_nodes: Dict[str, List[Tuple[str, str]]] = {}  # script_path -> [(scene_path, node_name)]
        
    def analyze_project(self, project_path: str) -> Dict[str, SceneInfo]:
        """
        Analyze all .tscn files in a project.
        
        Args:
            project_path: Root path of the Godot project
            
        Returns:
            Dictionary mapping scene paths to SceneInfo objects
        """
        self.scenes.clear()
        self.node_to_scene.clear()
        self.script_to_nodes.clear()
        
        # Find all .tscn files
        tscn_files = []
        project_root = Path(project_path)
        for root, dirs, files in os.walk(project_path):
            # Skip common non-essential directories
            dirs[:] = [d for d in dirs if d not in ['.git', '.godot', 'addons']]
            for file in files:
                if file.endswith('.tscn'):
                    tscn_files.append(str(Path(root) / file))
        
        # Parse each scene
        for tscn_path in tscn_files:
            try:
                scene_info = self._parse_scene_file(tscn_path)
                if scene_info:
                    self.scenes[tscn_path] = scene_info
                    
                    # Build reverse mappings
                    for node_name, node_info in scene_info.nodes.items():
                        self.node_to_scene[node_name] = tscn_path
                        
                        if node_info.script_path:
                            if node_info.script_path not in self.script_to_nodes:
                                self.script_to_nodes[node_info.script_path] = []
                            self.script_to_nodes[node_info.script_path].append((tscn_path, node_name))
                    
                    # Track resources
                    for res_id, res_path in scene_info.resources.items():
                        # Resources might be used by multiple scenes
                        pass
                        
            except Exception as e:
                print(f"[WARN] Failed to parse scene {tscn_path}: {e}")
        
        # Post-process: detect issues
        self._detect_issues()
        
        return self.scenes
    
    def _parse_scene_file(self, tscn_path: str) -> Optional[SceneInfo]:
        """Parse a single .tscn file."""
        try:
            with open(tscn_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"[ERROR] Cannot read {tscn_path}: {e}")
            return None
        
        scene_info = SceneInfo(
            path=tscn_path,
            root_node_type="Unknown"
        )
        
        lines = content.split('\n')
        current_section = None
        current_node = None
        node_path_map: Dict[str, NodeInfo] = {}
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith('[gd_scene'):
                current_section = 'header'
                # Extract root node type
                match = re.search(r'root_type="([^"]+)"', line)
                if match:
                    scene_info.root_node_type = match.group(1)
                    
            elif line.startswith('[node'):
                current_section = 'node'
                current_node = self._parse_node_header(line)
                if current_node:
                    scene_info.nodes[current_node.name] = current_node
                    node_path_map[current_node.name] = current_node
                    
                    # Update parent-child relationships
                    if current_node.parent:
                        parent_node = scene_info.nodes.get(current_node.parent)
                        if parent_node:
                            parent_node.children.append(current_node.name)
                    
                    # Track script attachment
                    if current_node.script_path:
                        scene_info.scripts[current_node.name] = current_node.script_path
            
            elif line.startswith('[resource'):
                current_section = 'resource'
                res_info = self._parse_resource_header(line)
                if res_info:
                    res_id, res_path = res_info
                    scene_info.resources[res_id] = res_path
            
            elif line.startswith('[') and '=' not in line:
                # New section we don't handle specifically
                current_section = line[1:-1] if line.startswith('[') and line.endswith(']') else line
                current_node = None
            
            elif current_section == 'node' and current_node and '=' in line:
                # Node property
                self._parse_node_property(line, current_node, scene_info)
            
            elif current_section == 'connection' and current_node:
                # Connection definition
                conn_info = self._parse_connection(line)
                if conn_info:
                    current_node.connections.append(conn_info)
        
        # Build parent references using path_map
        for node_name, node_info in scene_info.nodes.items():
            node_info.get_full_path(node_path_map)
        
        return scene_info
    
    def _parse_node_header(self, line: str) -> Optional[NodeInfo]:
        """Parse a [node ...] header line."""
        # Example: [node name="Player" type="CharacterBody2D" parent="."]
        # Example: [node name="Sprite" type="Sprite2D" parent="Player"]
        
        name_match = re.search(r'name="([^"]+)"', line)
        type_match = re.search(r'type="([^"]+)"', line)
        parent_match = re.search(r'parent="([^"]+)"', line)
        script_match = re.search(r'instance=ExtResource\("([^"]+)"\)', line)
        
        if not name_match or not type_match:
            return None
        
        node = NodeInfo(
            name=name_match.group(1),
            type=type_match.group(1),
            parent=None if parent_match and parent_match.group(1) == '.' else parent_match.group(1) if parent_match else None,
            script_path=script_match.group(1) if script_match else None
        )
        
        # Also check for script property in the line
        if not node.script_path:
            script_match2 = re.search(r'script=ExtResource\("([^"]+)"\)', line)
            if script_match2:
                node.script_path = script_match2.group(1)
        
        return node
    
    def _parse_resource_header(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse a [resource ...] header line."""
        # Example: [resource type="Script" id="1"]
        # Followed by: path = "res://scripts/player.gd"
        
        id_match = re.search(r'id="([^"]+)"', line)
        if id_match:
            return (id_match.group(1), "")
        return None
    
    def _parse_node_property(self, line: str, node: NodeInfo, scene_info: SceneInfo):
        """Parse a node property line."""
        # Example: transform = Transform2D(1, 0, 0, 1, 0, 0)
        # Example: script = ExtResource("1")
        # Example: texture = ExtResource("2")
        
        if '=' not in line:
            return
        
        key_value = line.split('=', 1)
        if len(key_value) != 2:
            return
        
        key = key_value[0].strip()
        value = key_value[1].strip()
        
        node.properties[key] = value
        
        # Check for resource references
        if 'ExtResource' in value or 'SubResource' in value:
            res_match = re.search(r'\("([^"]+)"\)', value)
            if res_match:
                res_id = res_match.group(1)
                # This property references a resource
                if key == 'script' and res_id in scene_info.resources:
                    node.script_path = scene_info.resources[res_id]
        
        # Check for missing resources
        if value.startswith('Null(') or 'missing' in value.lower():
            scene_info.missing_resources.append(f"{node.name}.{key}")
    
    def _parse_connection(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a signal connection line."""
        # Example: "button_pressed" :: "on_button_pressed()" : "TargetNode"
        
        # Simplified parsing - real format varies
        parts = line.split('::')
        if len(parts) >= 2:
            return {
                'signal': parts[0].strip().strip('"'),
                'method': parts[1].split(':')[0].strip().strip('"'),
                'target': parts[1].split(':')[-1].strip().strip('"') if ':' in parts[1] else ''
            }
        return None
    
    def _detect_issues(self):
        """Detect common scene issues after parsing."""
        for scene_path, scene_info in self.scenes.items():
            # Detect orphaned nodes (nodes with no parent reference but aren't root)
            root_found = False
            for node_name, node_info in scene_info.nodes.items():
                if node_info.parent is None and not root_found:
                    root_found = True
                elif node_info.parent is None and root_found:
                    # Multiple root-level nodes might indicate an issue
                    scene_info.orphaned_nodes.append(node_name)
            
            # Detect missing script references
            for node_name, script_path in scene_info.scripts.items():
                if script_path:
                    # Convert res:// to actual path using pathlib
                    scene_dir = Path(scene_path).parent
                    actual_path = script_path.replace('res://', str(scene_dir) + '/')
                    if not Path(actual_path).exists():
                        # Script file doesn't exist
                        pass  # Could add to a missing_scripts list
    
    def get_scene_stats(self) -> Dict[str, Any]:
        """Get statistics about all analyzed scenes."""
        total_nodes = sum(s.node_count for s in self.scenes.values())
        total_scripts = sum(s.script_count for s in self.scenes.values())
        
        # Find most complex scenes
        scenes_by_complexity = sorted(
            self.scenes.items(),
            key=lambda x: x[1].node_count,
            reverse=True
        )[:5]
        
        # Find scripts used in most scenes
        script_usage = {}
        for script_path, occurrences in self.script_to_nodes.items():
            script_usage[script_path] = len(set([s[0] for s in occurrences]))  # Unique scenes
        
        most_used_scripts = sorted(script_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_scenes': len(self.scenes),
            'total_nodes': total_nodes,
            'total_script_attachments': total_scripts,
            'most_complex_scenes': [(s[0], s[1].node_count) for s in scenes_by_complexity],
            'most_used_scripts': most_used_scripts,
            'scenes_with_missing_resources': sum(1 for s in self.scenes.values() if s.missing_resources),
            'scenes_with_orphans': sum(1 for s in self.scenes.values() if s.orphaned_nodes)
        }
    
    def get_node_hierarchy(self, scene_path: str, root_node: Optional[str] = None) -> List[str]:
        """
        Get a visual representation of the node hierarchy.
        
        Returns:
            List of strings representing the tree structure
        """
        if scene_path not in self.scenes:
            return ["[ERROR] Scene not found"]
        
        scene = self.scenes[scene_path]
        result = []
        
        # Find root node
        if root_node:
            if root_node not in scene.nodes:
                return [f"[ERROR] Node '{root_node}' not found in scene"]
            root = scene.nodes[root_node]
        else:
            # Find node with no parent (root)
            roots = [n for n in scene.nodes.values() if n.parent is None]
            if not roots:
                return ["[ERROR] No root node found"]
            root = roots[0]
        
        def traverse(node: NodeInfo, indent: int = 0):
            prefix = "  " * indent
            script_marker = " 📜" if node.script_path else ""
            result.append(f"{prefix}├─ {node.name} ({node.type}){script_marker}")
            
            for child_name in node.children:
                if child_name in scene.nodes:
                    traverse(scene.nodes[child_name], indent + 1)
        
        traverse(root)
        return result
    
    def find_script_usage(self, script_path: str) -> List[Dict[str, str]]:
        """
        Find all places where a script is used in scenes.
        
        Returns:
            List of dicts with scene_path and node_name
        """
        if script_path not in self.script_to_nodes:
            return []
        
        return [
            {'scene_path': scene_path, 'node_name': node_name}
            for scene_path, node_name in self.script_to_nodes[script_path]
        ]
    
    def validate_scene_script_bindings(self) -> List[Dict[str, str]]:
        """
        Validate that all attached scripts exist and match expected types.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for scene_path, scene_info in self.scenes.items():
            for node_name, script_path in scene_info.scripts.items():
                # Check if script file exists
                if script_path:
                    # Convert res:// to actual path using pathlib
                    scene_dir = Path(scene_path).parent
                    actual_path = script_path.replace('res://', str(scene_dir) + '/')
                    if not Path(actual_path).exists():
                        errors.append({
                            'type': 'missing_script',
                            'scene': scene_path,
                            'node': node_name,
                            'script': script_path,
                            'message': f"Script file not found: {script_path}"
                        })
        
        return errors
    
    def get_scene_summary(self, scene_path: str) -> str:
        """Get a human-readable summary of a scene."""
        if scene_path not in self.scenes:
            return f"[ERROR] Scene not found: {scene_path}"
        
        scene = self.scenes[scene_path]
        lines = [
            f"📄 Scene: {Path(scene_path).name}",
            f"   Type: {scene.root_node_type}",
            f"   Nodes: {scene.node_count}",
            f"   Scripts: {scene.script_count}",
        ]
        
        if scene.missing_resources:
            lines.append(f"   ⚠ Missing Resources: {len(scene.missing_resources)}")
        
        if scene.orphaned_nodes:
            lines.append(f"   ⚠ Orphaned Nodes: {len(scene.orphaned_nodes)}")
        
        # Show hierarchy preview
        lines.append("\n🌳 Node Hierarchy:")
        hierarchy = self.get_node_hierarchy(scene_path)
        for line in hierarchy[:10]:  # First 10 levels
            lines.append(f"   {line}")
        
        if len(hierarchy) > 10:
            lines.append(f"   ... and {len(hierarchy) - 10} more nodes")
        
        return '\n'.join(lines)


def create_scene_analyzer() -> SceneGraphAnalyzer:
    """Factory function to create a SceneGraphAnalyzer instance."""
    return SceneGraphAnalyzer()

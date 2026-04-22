"""
Godot Expert Engine - Deep GDScript & TSCN Intelligence
Transforms Ether from a text-fixer into a true Godot architect.
"""

import re
import os
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path


class GodotExpert:
    """
    The "Master" Module for Godot-specific knowledge.
    Combines AST analysis with Godot pattern matching for deep refactoring.
    """

    def __init__(self):
        self.project_path: Optional[str] = None
        self.known_signals: Dict[str, List[str]] = {}
        self.autoloads: List[str] = []
        
        # Godot-specific anti-patterns
        self.performance_patterns = {
            'process_heavy': r'def\s+_process\s*\([^)]*\):\s*.*?(?:for\s+.*?in\s+.*?|while\s+.*?:|\.load\(|\.import\()',
            'get_node_string': r'get_node\s*\(\s*["\']\/?*.*?["\']\s*\)',
            'unsafe_connect': r'connect\s*\(\s*["\'].*?["\']\s*,\s*self',
            'missing_exit_cleanup': r'connect\s*\([^)]+\)\s*(?!.*_exit_tree)',
        }
        
        # Refactoring templates
        self.refactor_templates = {
            'node_cache': "var {name} = ${path}",
            'signal_disconnect': "if {signal_name}.is_connected({callback}): {signal_name}.disconnect({callback})",
            'export_var': "@export var {name}: {type} = {default}",
        }

    def load_project_context(self, project_path: str) -> None:
        """Load project-specific context (autoloads, global signals)."""
        self.project_path = project_path
        
        # Parse project.godot for autoloads
        godot_file = Path(project_path) / "project.godot"
        if godot_file.exists():
            content = godot_file.read_text(encoding='utf-8')
            # Extract autoload names
            autoload_matches = re.findall(r'resource/name="(\w+)"', content)
            self.autoloads = autoload_matches
            
        print(f"[GodotExpert] Loaded context: {len(self.autoloads)} autoloads found")

    def analyze_script(self, code: str, file_path: str) -> Dict[str, Any]:
        """
        Perform deep Godot-specific analysis on a script.
        Returns issues, suggestions, and refactoring opportunities.
        """
        issues = []
        suggestions = []
        refactors = []
        
        lines = code.split('\n')
        
        # 1. Check for _process vs _physics_process misuse
        if '_process(' in code and ('velocity' in code or 'physics' in code or 'collision' in code):
            issues.append({
                'type': 'PERFORMANCE',
                'severity': 'HIGH',
                'message': "Use `_physics_process()` instead of `_process()` for physics-related logic.",
                'line': self._find_line_number(code, '_process(')
            })
            suggestions.append("Replace `_process` with `_physics_process` for consistent physics stepping.")

        # 2. Detect unsafe string-based get_node() calls
        unsafe_nodes = re.finditer(self.performance_patterns['get_node_string'], code)
        for match in unsafe_nodes:
            node_path = match.group(0)
            if '/' in node_path or node_path.count('/') > 1:
                issues.append({
                    'type': 'MAINTAINABILITY',
                    'severity': 'MEDIUM',
                    'message': f"Avoid hardcoded paths like {node_path}. Use @export var or cache in _ready().",
                    'line': self._find_line_number(code, node_path)
                })
                refactors.append({
                    'type': 'CACHE_NODE',
                    'original': node_path,
                    'suggestion': f"Add '@export var node_ref: NodePath' and use 'get_node(node_ref)'"
                })

        # 3. Check for missing signal disconnections (memory leak risk)
        if 'connect(' in code and '_exit_tree' not in code:
            # Only warn for dynamic connections
            if 'self.' in code or 'func ' in code:
                issues.append({
                    'type': 'MEMORY_LEAK',
                    'severity': 'MEDIUM',
                    'message': "Signals connected but not disconnected in `_exit_tree()`. May cause memory leaks.",
                    'line': -1
                })
                refactors.append({
                    'type': 'ADD_CLEANUP',
                    'suggestion': "Add `_exit_tree()` method to disconnect signals."
                })

        # 4. Detect bloated _ready() methods
        ready_match = re.search(r'func\s+_ready\s*\(\).*?:\s*\n((?:\s+.+\n)*?)\s*func\s+', code)
        if ready_match:
            ready_body = ready_match.group(1)
            line_count = len([l for l in ready_body.split('\n') if l.strip()])
            if line_count > 15:
                issues.append({
                    'type': 'COMPLEXITY',
                    'severity': 'LOW',
                    'message': f"_ready() method is too long ({line_count} lines). Consider extracting helper functions.",
                    'line': self._find_line_number(code, 'func _ready')
                })

        # 5. Check for hardcoded magic numbers
        magic_numbers = re.findall(r'(?<!\w)(\d{2,})(?!\w)', code)
        if len(magic_numbers) > 3:
            suggestions.append("Consider defining constants for magic numbers found in the code.")

        return {
            'issues': issues,
            'suggestions': suggestions,
            'refactors': refactors,
            'score': max(0, 100 - len(issues) * 10 - len(suggestions) * 5)
        }

    def apply_godot_refactor(self, code: str, refactor_type: str, context: Dict) -> str:
        """
        Apply a specific Godot refactor to the code.
        """
        if refactor_type == 'CACHE_NODE':
            # Extract node path and name
            path = context.get('path', '')
            name = context.get('name', 'node_ref')
            
            # Add export variable at top of class
            export_line = f"@export var {name}: NodePath = @\"{path}\""
            
            # Replace get_node calls
            old_call = f'get_node("{path}")'
            new_call = f'get_node({name})'
            
            code = code.replace(old_call, new_call)
            
            # Insert export after class declaration
            if 'extends' in code:
                parts = code.split('\n', 1)
                if len(parts) > 1:
                    code = parts[0] + '\n' + export_line + '\n' + parts[1]
                else:
                    code = export_line + '\n' + code
                    
        elif refactor_type == 'ADD_CLEANUP':
            # Generate _exit_tree method
            cleanup_code = """
func _exit_tree() -> void:
\t# Disconnect signals to prevent memory leaks
\t# TODO: Add specific disconnect calls here
\tpass
"""
            if '_exit_tree' not in code:
                code = code.rstrip() + '\n' + cleanup_code
                
        return code

    def validate_scene_binding(self, script_path: str, scene_content: str) -> Dict[str, Any]:
        """
        Validate that a script is correctly bound to a scene.
        """
        issues = []
        
        # Extract script path from scene
        script_match = re.search(r'script\s*=\s*ExtResource\(\s*"([\w_/]+)"\s*\)', scene_content)
        if not script_match:
            # Check for internal script
            if 'script =' not in scene_content:
                return {'valid': True, 'issues': []} # No script attached is valid
                
        # Check for UID consistency (Godot 4+)
        if 'uid://' not in scene_content and 'uid://' in script_path:
            issues.append("Scene missing UID reference for script.")
            
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def _find_line_number(self, code: str, target: str) -> int:
        """Find line number of a target string."""
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if target in line:
                return i + 1
        return -1


class SemanticSceneEditor:
    """
    Object-oriented parser and editor for .tscn files.
    Handles semantic transformations without breaking format.
    """

    def __init__(self):
        self.scene_data: Dict[str, Any] = {}
        self.nodes: Dict[str, Dict] = {}
        self.connections: List[Dict] = []
        self.resources: Dict[str, str] = {}

    def parse(self, tscn_content: str) -> bool:
        """
        Parse .tscn content into structured data.
        """
        self.scene_data = {
            'header': '',
            'nodes': {},
            'connections': [],
            'resources': {},
            'editable': []
        }
        
        lines = tscn_content.split('\n')
        current_section = None
        current_node_name = None
        current_node_data = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Header
            if line.startswith('[gd_scene'):
                self.scene_data['header'] = line
                current_section = 'header'
                
            # Resources
            elif line.startswith('[resource'):
                current_section = 'resource'
                # Parse resource ID
                res_match = re.match(r'\[resource(?:_name="([^"]+)")?\s*(?:id="([^"]+)")?', line)
                if res_match:
                    res_id = res_match.group(2) or f"res_{i}"
                    self.scene_data['resources'][res_id] = line
                    
            # Nodes
            elif line.startswith('[node'):
                if current_node_name:
                    self.scene_data['nodes'][current_node_name] = '\n'.join(current_node_data)
                
                current_node_name = self._extract_node_name(line)
                current_node_data = [line]
                current_section = 'node'
                
            # Connections
            elif line.startswith('[connection'):
                conn = self._parse_connection(line)
                if conn:
                    self.scene_data['connections'].append(conn)
                    
            # Editable hints
            elif line.startswith('[editable'):
                self.scene_data['editable'].append(line)
                
            # Content lines
            elif current_section == 'node' and current_node_name:
                if line.startswith('[') and not line.startswith('[node'):
                    # New section started
                    self.scene_data['nodes'][current_node_name] = '\n'.join(current_node_data)
                    current_node_name = None
                    current_node_data = []
                    # Re-process this line
                    continue
                current_node_data.append(lines[i]) # Keep original indentation
            
            i += 1
            
        # Save last node
        if current_node_name:
            self.scene_data['nodes'][current_node_name] = '\n'.join(current_node_data)
            
        return True

    def _extract_node_name(self, line: str) -> Optional[str]:
        """Extract node name from [node ...] line."""
        # Pattern: [node name="MyNode" type="Control" parent="."]
        match = re.search(r'name="([^"]+)"', line)
        if match:
            return match.group(1)
        # Fallback to type if no name
        match = re.search(r'type="([^"]+)"', line)
        if match:
            return f"unnamed_{match.group(1)}"
        return None

    def _parse_connection(self, line: str) -> Optional[Dict]:
        """Parse a [connection] line into structured data."""
        # [connection signal="pressed" from="Button" to="." method="_on_button_pressed"]
        signal_match = re.search(r'signal="([^"]+)"', line)
        from_match = re.search(r'from="([^"]+)"', line)
        to_match = re.search(r'to="([^"]+)"', line)
        method_match = re.search(r'method="([^"]+)"', line)
        
        if signal_match and from_match and to_match and method_match:
            return {
                'signal': signal_match.group(1),
                'from': from_match.group(1),
                'to': to_match.group(1),
                'method': method_match.group(1),
                'raw': line
            }
        return None

    def add_node(self, parent: str, node_type: str, name: str, properties: Dict = None) -> bool:
        """
        Add a new node to the scene semantically.
        """
        node_id = f"{parent}/{name}"
        
        # Construct node block
        props_str = ""
        if properties:
            for key, value in properties.items():
                if isinstance(value, str):
                    props_str += f'\n{key} = "{value}"'
                else:
                    props_str += f'\n{key} = {value}'
        
        node_block = f'[node name="{name}" type="{node_type}" parent="{parent}"]{props_str}'
        
        # Insert after parent node
        if parent in self.scene_data['nodes']:
            # Find insertion point (after parent block)
            self.scene_data['nodes'][node_id] = node_block
            return True
            
        # If root, add to end
        self.scene_data['nodes'][node_id] = node_block
        return True

    def remove_node(self, node_name: str) -> bool:
        """
        Remove a node and its children safely.
        """
        if node_name in self.scene_data['nodes']:
            del self.scene_data['nodes'][node_name]
            # Also remove children
            to_remove = [k for k in self.scene_data['nodes'] if k.startswith(node_name + "/")]
            for k in to_remove:
                del self.scene_data['nodes'][k]
            # Remove connections involving this node
            self.scene_data['connections'] = [
                c for c in self.scene_data['connections'] 
                if c['from'] != node_name and c['to'] != node_name
            ]
            return True
        return False

    def connect_signal(self, from_node: str, signal_name: str, to_node: str, method_name: str) -> bool:
        """
        Add a signal connection.
        """
        conn = {
            'signal': signal_name,
            'from': from_node,
            'to': to_node,
            'method': method_name,
            'raw': f'[connection signal="{signal_name}" from="{from_node}" to="{to_node}" method="{method_name}"]'
        }
        
        # Check for duplicates
        for existing in self.scene_data['connections']:
            if (existing['from'] == from_node and 
                existing['signal'] == signal_name and 
                existing['to'] == to_node and 
                existing['method'] == method_name):
                return False # Already exists
                
        self.scene_data['connections'].append(conn)
        return True

    def disconnect_signal(self, from_node: str, signal_name: str, to_node: str, method_name: str) -> bool:
        """
        Remove a specific signal connection.
        """
        initial_count = len(self.scene_data['connections'])
        self.scene_data['connections'] = [
            c for c in self.scene_data['connections']
            if not (c['from'] == from_node and 
                    c['signal'] == signal_name and 
                    c['to'] == to_node and 
                    c['method'] == method_name)
        ]
        return len(self.scene_data['connections']) < initial_count

    def set_property(self, node_name: str, property_name: str, value: Any) -> bool:
        """
        Set or update a node property.
        """
        if node_name not in self.scene_data['nodes']:
            return False
            
        node_block = self.scene_data['nodes'][node_name]
        lines = node_block.split('\n')
        
        updated = False
        new_lines = []
        
        for line in lines:
            if line.strip().startswith(f'{property_name} ='):
                # Update existing
                if isinstance(value, str):
                    new_lines.append(f'{property_name} = "{value}"')
                else:
                    new_lines.append(f'{property_name} = {value}')
                updated = True
            else:
                new_lines.append(line)
                
        if not updated:
            # Add new property
            if isinstance(value, str):
                new_lines.append(f'{property_name} = "{value}"')
            else:
                new_lines.append(f'{property_name} = {value}')
                
        self.scene_data['nodes'][node_name] = '\n'.join(new_lines)
        return True

    def serialize(self) -> str:
        """
        Reconstruct .tscn content from structured data.
        """
        output = []
        
        # Header
        if self.scene_data.get('header'):
            output.append(self.scene_data['header'])
            output.append("")
            
        # Resources
        for res_id, res_line in self.scene_data.get('resources', {}).items():
            output.append(res_line)
        if self.scene_data.get('resources'):
            output.append("")
            
        # Nodes (maintain order roughly)
        # Sort by depth to ensure parents come before children
        sorted_nodes = sorted(self.scene_data['nodes'].keys(), key=lambda x: x.count('/'))
        
        for node_name in sorted_nodes:
            node_block = self.scene_data['nodes'][node_name]
            output.append(node_block)
            output.append("")
            
        # Connections
        if self.scene_data.get('connections'):
            output.append("[connections]")
            for conn in self.scene_data['connections']:
                output.append(conn['raw'])
                
        # Editable
        for edit_line in self.scene_data.get('editable', []):
            output.append(edit_line)
            
        return '\n'.join(output)

    def validate_integrity(self) -> List[str]:
        """
        Check for common TSCN integrity issues.
        """
        errors = []
        
        # Check for orphaned connections
        node_names = set(self.scene_data['nodes'].keys())
        # Add root "."
        node_names.add(".")
        
        for conn in self.scene_data['connections']:
            if conn['from'] not in node_names:
                # Check if it's a child of an existing node
                parent_exists = any(n for n in node_names if conn['from'].startswith(n + "/"))
                if not parent_exists:
                    errors.append(f"Connection source '{conn['from']}' does not exist.")
            if conn['to'] not in node_names:
                parent_exists = any(n for n in node_names if conn['to'].startswith(n + "/"))
                if not parent_exists:
                    errors.append(f"Connection target '{conn['to']}' does not exist.")
                    
        return errors

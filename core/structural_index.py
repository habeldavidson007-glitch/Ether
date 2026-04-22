"""
Structural RAG Module (structural_index.py)
-------------------------------------------
Implements "Document Tree" indexing instead of vector embeddings.
Uses Godot's Scene Tree and GDScript AST to preserve code hierarchy.
Allows LLMs to reason over structure (Class -> Method -> Line) rather than keywords.

Key Features:
- No Chunking: Preserves full context of classes/functions.
- No Embeddings: Uses deterministic tree paths for retrieval.
- Godot Native: Understands Nodes, Scenes, and GDScript structure.
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Assuming existing Ether imports
try:
    from core.godot_expert import GodotExpert
    from core.dependency_graph import DependencyGraph
except ImportError:
    # Fallback for standalone testing
    GodotExpert = None
    DependencyGraph = None


class StructuralNode:
    """Represents a node in the Document Tree."""
    
    def __init__(self, node_id: str, node_type: str, name: str, path: str, 
                 content: str = "", metadata: Optional[Dict] = None):
        self.node_id = node_id
        self.node_type = node_type  # e.g., 'Scene', 'Class', 'Function', 'Signal'
        self.name = name
        self.path = path  # Logical path: /root/Player/Scripts/player.gd::Player::_ready
        self.content = content
        self.metadata = metadata or {}
        self.children: List['StructuralNode'] = []
        self.parent: Optional['StructuralNode'] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "name": self.name,
            "path": self.path,
            "content_preview": self.content[:200] if self.content else "",
            "children_count": len(self.children),
            "metadata": self.metadata
        }

    def get_full_context(self) -> str:
        """Recursively gather context from parent and children."""
        context_parts = []
        
        # Add parent context (signature only)
        if self.parent:
            context_parts.append(f"# Parent Context: {self.parent.path}")
            
        # Add self signature
        context_parts.append(f"# Current Node: {self.path}")
        if self.content:
            context_parts.append(self.content)
            
        # Add children signatures (structure map)
        if self.children:
            context_parts.append("\n# Structure Map:")
            for child in self.children:
                context_parts.append(f"#   - {child.node_type}: {child.name}")
                
        return "\n".join(context_parts)


class StructuralIndex:
    """
    Main Index Manager. Builds and queries the Document Tree.
    Replaces traditional Vector Store with a Hierarchical Tree Store.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.index: Dict[str, StructuralNode] = {}  # ID -> Node
        self.root_nodes: List[StructuralNode] = []
        self.godot_expert = GodotExpert() if GodotExpert else None
        
        # Cache for fast lookups
        self.path_map: Dict[str, StructuralNode] = {}
        self.type_map: Dict[str, List[StructuralNode]] = {}

    def build_index(self, force_rebuild: bool = False):
        """
        Scans the project and builds the structural tree.
        1. Scan .tscn files for Scene Trees.
        2. Scan .gd files for AST Class/Function Trees.
        3. Link them together.
        """
        print(f"[StructuralIndex] Building document tree for {self.project_root}...")
        self.index.clear()
        self.root_nodes.clear()
        
        # 1. Process GDScript Files (AST Based)
        gd_files = list(self.project_root.rglob("*.gd"))
        for file_path in gd_files:
            self._index_gdscript(file_path)
            
        # 2. Process Scene Files (Tree Based)
        tscn_files = list(self.project_root.rglob("*.tscn"))
        for file_path in tscn_files:
            self._index_scene(file_path)
            
        print(f"[StructuralIndex] Indexed {len(self.index)} structural nodes.")

    def _generate_id(self, path: str, content: str) -> str:
        return hashlib.md5(f"{path}:{content[:100]}".encode()).hexdigest()[:12]

    def _index_gdscript(self, file_path: Path):
        """Parses GDScript into a class/function tree."""
        relative_path = file_path.relative_to(self.project_root)
        
        # Use existing GodotExpert if available for robust parsing
        if self.godot_expert:
            try:
                structure = self.godot_expert.analyze_file(str(file_path))
                # Structure expected: {'classes': [...], 'functions': [...]}
                
                root_node = StructuralNode(
                    node_id=self._generate_id(str(relative_path), "file"),
                    node_type="File",
                    name=file_path.name,
                    path=str(relative_path),
                    metadata={"line_count": len(file_path.read_text().splitlines())}
                )
                self._add_node(root_node)
                
                # Parse Classes
                if isinstance(structure, dict) and 'classes' in structure:
                    for cls in structure.get('classes', []):
                        cls_node = StructuralNode(
                            node_id=self._generate_id(str(relative_path), cls.get('name', '')),
                            node_type="Class",
                            name=cls.get('name', 'Anonymous'),
                            path=f"{relative_path}::{cls.get('name', 'Global')}",
                            content=cls.get('source', ''),
                            metadata=cls
                        )
                        cls_node.parent = root_node
                        root_node.children.append(cls_node)
                        self._add_node(cls_node)
                        
                        # Parse Functions within Classes
                        for func in cls.get('functions', []):
                            self._add_function_node(func, cls_node, relative_path)
                            
                # Parse Global Functions (if not in class)
                if isinstance(structure, dict) and 'functions' in structure:
                    for func in structure.get('functions', []):
                        # Check if already added via class
                        if not any(func.get('name') == c.name for c in root_node.children):
                            self._add_function_node(func, root_node, relative_path)
                            
            except Exception as e:
                print(f"[StructuralIndex] Error parsing {file_path}: {e}")
                # Fallback: Simple line-based indexing
                self._fallback_index_file(file_path, relative_path)
        else:
            self._fallback_index_file(file_path, relative_path)

    def _add_function_node(self, func_data: Dict, parent_node: StructuralNode, file_path: Path):
        func_name = func_data.get('name', 'unknown')
        func_node = StructuralNode(
            node_id=self._generate_id(str(file_path), func_name),
            node_type="Function",
            name=func_name,
            path=f"{parent_node.path}::{func_name}",
            content=func_data.get('source', ''),
            metadata=func_data
        )
        func_node.parent = parent_node
        parent_node.children.append(func_node)
        self._add_node(func_node)

    def _fallback_index_file(self, file_path: Path, relative_path: Path):
        """Simple fallback if AST parser fails."""
        content = file_path.read_text()
        root_node = StructuralNode(
            node_id=self._generate_id(str(relative_path), "file"),
            node_type="File",
            name=file_path.name,
            path=str(relative_path),
            content=content
        )
        self._add_node(root_node)

    def _index_scene(self, file_path: Path):
        """Parses .tscn into a node tree."""
        relative_path = file_path.relative_to(self.project_root)
        content = file_path.read_text()
        
        root_node = StructuralNode(
            node_id=self._generate_id(str(relative_path), "scene"),
            node_type="Scene",
            name=file_path.stem,
            path=str(relative_path),
            metadata={"type": "tscn"}
        )
        self._add_node(root_node)
        
        # Simple parsing of [node] blocks
        current_parent = root_node
        for line in content.split('\n'):
            if line.startswith("[node"):
                # Extract node name and type roughly
                parts = line.split("name=")
                name = "Unknown"
                if len(parts) > 1:
                    name = parts[1].split('"')[1].split('"')[0]
                
                node_type = "Node"
                if "type=" in line:
                    node_type = line.split("type=")[1].split('"')[1].split('"')[0]
                
                child = StructuralNode(
                    node_id=self._generate_id(str(relative_path), name),
                    node_type=f"SceneNode ({node_type})",
                    name=name,
                    path=f"{relative_path}::{name}",
                    metadata={"raw_header": line[:100]}
                )
                child.parent = current_parent
                current_parent.children.append(child)
                self._add_node(child)
                # In a real tree, we'd track indentation, but this suffices for flat list + parent link

    def _add_node(self, node: StructuralNode):
        self.index[node.node_id] = node
        self.path_map[node.path] = node
        
        if node.node_type not in self.type_map:
            self.type_map[node.node_type] = []
        self.type_map[node.node_type].append(node)

    def query_structure(self, query_type: str, target_name: Optional[str] = None, 
                        context_depth: int = 2) -> List[Dict]:
        """
        Retrieves nodes based on structural queries, not keyword similarity.
        
        Args:
            query_type: 'class', 'function', 'scene_node', 'file'
            target_name: Specific name to match (optional)
            context_depth: How many levels of children/parents to include
            
        Returns:
            List of context dictionaries ready for LLM prompt injection.
        """
        results = []
        
        candidates = []
        if target_name:
            # Direct lookup by name in path
            candidates = [n for n in self.index.values() if target_name.lower() in n.name.lower()]
        else:
            # Type lookup
            candidates = self.type_map.get(query_type, [])
            
        for node in candidates[:10]: # Limit results
            context = {
                "path": node.path,
                "type": node.node_type,
                "content": node.get_full_context(),
                "structure_map": [c.to_dict() for c in node.children[:5]] # Preview children
            }
            results.append(context)
            
        return results

    def get_context_for_path(self, path: str, include_siblings: bool = True) -> Optional[str]:
        """Gets the full structural context for a specific file/path."""
        node = self.path_map.get(path)
        if not node:
            return None
            
        context_lines = [f"# Structural Context for: {path}"]
        
        # Add Parent Chain
        curr = node.parent
        while curr:
            context_lines.append(f"# Located inside: {curr.path} ({curr.node_type})")
            curr = curr.parent
            
        # Add Siblings
        if include_siblings and node.parent:
            context_lines.append("# Sibling Elements:")
            for sib in node.parent.children:
                if sib != node:
                    context_lines.append(f"#   - {sib.name} ({sib.node_type})")
                    
        context_lines.append("\n# Content:")
        context_lines.append(node.content if node.content else "# Binary or Empty")
        
        return "\n".join(context_lines)

    def export_tree_json(self, output_path: str):
        """Exports the full tree for debugging or external analysis."""
        data = [n.to_dict() for n in self.root_nodes]
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

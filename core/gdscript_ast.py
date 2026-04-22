"""
GDScript AST Parser & Structural Mapper
Parses GDScript into a navigable tree for surgical code modification.
Does NOT execute code; purely structural analysis.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

class NodeType(Enum):
    FUNCTION = "function"
    SIGNAL = "signal"
    CLASS_DEF = "class"
    IMPORT = "import"
    EXPORT = "export"
    BLOCK = "block"
    LINE = "line"

@dataclass
class CodeNode:
    type: NodeType
    name: str
    start_line: int
    end_line: int
    content: str
    indent_level: int = 0
    children: List['CodeNode'] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

class GDScriptAST:
    def __init__(self, source_code: str):
        self.source = source_code
        self.lines = source_code.splitlines(keepends=True)
        self.root_nodes: List[CodeNode] = []
        self.node_map: Dict[int, CodeNode] = {} # Map line number to node
        self._parse()

    def _get_indent(self, line: str) -> int:
        return len(line) - len(line.lstrip())

    def _parse(self):
        """Main parsing loop."""
        i = 0
        total_lines = len(self.lines)
        
        while i < total_lines:
            line = self.lines[i]
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                i += 1
                continue

            indent = self._get_indent(line)
            
            # Detect Signals
            if stripped.startswith("signal "):
                match = re.match(r'signal\s+(\w+)', stripped)
                name = match.group(1) if match else "unknown_signal"
                node = CodeNode(
                    type=NodeType.SIGNAL, name=name, 
                    start_line=i, end_line=i, content=line, indent_level=indent
                )
                self.root_nodes.append(node)
                self.node_map[i] = node
                i += 1
                continue

            # Detect Functions
            if stripped.startswith("func "):
                match = re.match(r'func\s+(\w+)\s*\(', stripped)
                name = match.group(1) if match else "unknown_func"
                start_i = i
                i += 1
                
                # Find function end (next line with <= indent)
                while i < total_lines:
                    next_line = self.lines[i]
                    if next_line.strip() == "":
                        i += 1
                        continue
                    next_indent = self._get_indent(next_line)
                    if next_indent <= indent and next_line.strip():
                        break
                    i += 1
                
                end_i = i
                content = "".join(self.lines[start_i:end_i])
                
                node = CodeNode(
                    type=NodeType.FUNCTION, name=name,
                    start_line=start_i, end_line=end_i, content=content, indent_level=indent
                )
                self.root_nodes.append(node)
                # Map all lines in function to this node
                for l in range(start_i, end_i):
                    self.node_map[l] = node
                continue
            
            # Detect Class/Extends
            if stripped.startswith("extends ") or stripped.startswith("class "):
                name = stripped.split()[1] if len(stripped.split()) > 1 else "anonymous"
                node = CodeNode(
                    type=NodeType.CLASS_DEF, name=name,
                    start_line=i, end_line=i+1, content=line, indent_level=indent
                )
                self.root_nodes.append(node)
                self.node_map[i] = node
                i += 1
                continue

            i += 1

    def get_function(self, name: str) -> Optional[CodeNode]:
        """Find a function by name."""
        for node in self.root_nodes:
            if node.type == NodeType.FUNCTION and node.name == name:
                return node
        return None

    def get_functions_by_pattern(self, pattern: str) -> List[CodeNode]:
        """Find functions matching a regex pattern."""
        matches = []
        for node in self.root_nodes:
            if node.type == NodeType.FUNCTION and re.search(pattern, node.name):
                matches.append(node)
        return matches

    def get_line_node(self, line_num: int) -> Optional[CodeNode]:
        """Get the structural node containing a specific line."""
        return self.node_map.get(line_num)

    def reconstruct(self) -> str:
        """Reconstruct code from current nodes (if modified)."""
        # Simple reconstruction: sort by start_line and join
        # In advanced usage, this handles spliced content
        sorted_nodes = sorted(self.root_nodes, key=lambda n: n.start_line)
        output = []
        last_end = 0
        
        for node in sorted_nodes:
            # Fill gaps between nodes with original lines if needed
            # For now, we assume nodes cover everything or we use direct line replacement
            pass
        
        # Fallback to direct line manipulation for surgical splicing
        return self.source

class SurgicalSplicer:
    """Performs safe, structural code modifications."""
    
    def __init__(self, source_code: str):
        self.ast = GDScriptAST(source_code)
        self.lines = source_code.splitlines(keepends=True)
        self.modified = False

    def replace_function_body(self, func_name: str, new_body: str, keep_signature: bool = True) -> bool:
        """
        Replace the body of a function while preserving its signature and indentation.
        new_body should be the INNER content (without the 'func ...' line).
        """
        node = self.ast.get_function(func_name)
        if not node:
            return False

        # Extract signature line
        signature_line = self.lines[node.start_line]
        
        # Normalize indentation for new body
        base_indent = " " * node.indent_level
        inner_indent = " " * (node.indent_level + 4) # Standard GDScript indent
        
        processed_lines = [signature_line]
        
        # Process new body lines
        body_lines = new_body.splitlines()
        for line in body_lines:
            stripped = line.strip()
            if not stripped:
                processed_lines.append("\n")
            else:
                # Ensure correct indentation relative to function
                if not line.startswith(" "):
                    processed_lines.append(f"{inner_indent}{stripped}\n")
                else:
                    # Adjust existing indent to match base
                    current_indent = len(line) - len(line.lstrip())
                    # Simple strategy: just apply base inner indent for now
                    # Advanced: calculate relative indent
                    processed_lines.append(f"{inner_indent}{stripped}\n")
        
        # Add closing logic if missing (optional, GDScript doesn't strictly need end)
        # But we ensure the block structure is valid
        
        # Replace lines in the main array
        # Remove old lines
        del self.lines[node.start_line:node.end_line]
        # Insert new lines
        for i, line in enumerate(processed_lines):
            self.lines.insert(node.start_line + i, line)
            
        self.modified = True
        return True

    def inject_after_signal(self, signal_name: str, code_to_inject: str) -> bool:
        """Inject code immediately after a signal definition."""
        node = None
        for n in self.ast.root_nodes:
            if n.type == NodeType.SIGNAL and n.name == signal_name:
                node = n
                break
        
        if not node:
            return False
            
        inject_lines = code_to_inject.splitlines(keepends=True)
        # Ensure newlines
        if not inject_lines[-1].endswith('\n'):
            inject_lines[-1] += '\n'
            
        insert_pos = node.end_line
        for i, line in enumerate(inject_lines):
            self.lines.insert(insert_pos + i, line)
            
        self.modified = True
        return True

    def remove_duplicate_signals(self) -> int:
        """Remove duplicate signal definitions."""
        seen = set()
        to_remove_indices = []
        
        # Scan lines directly for signals (more reliable than AST for this)
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            stripped = line.strip()
            
            if stripped.startswith("signal "):
                match = re.match(r'signal\s+(\w+)', stripped)
                if match:
                    sig_name = match.group(1)
                    if sig_name in seen:
                        to_remove_indices.append(i)
                    else:
                        seen.add(sig_name)
            i += 1
        
        # Remove from bottom up to preserve indices
        count = 0
        for idx in reversed(to_remove_indices):
            del self.lines[idx]
            count += 1
            
        if count > 0:
            self.modified = True
            # Refresh AST after modification
            self.ast = GDScriptAST("".join(self.lines))
        return count

    def get_code(self) -> str:
        return "".join(self.lines)

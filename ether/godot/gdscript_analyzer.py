"""
GDScript Analyzer - Unified analysis tool for Godot scripts.
Merges functionality from gdscript_ast.py, static_analyzer.py, 
godot_validator.py, and godot_expert.py.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import re


@dataclass
class Finding:
    """A code analysis finding."""
    line: int
    column: int
    severity: str  # 'error', 'warning', 'info'
    category: str
    description: str
    suggestion: str = ""


@dataclass
class ScriptNode:
    """Represents a parsed GDScript structure."""
    name: str
    node_type: str
    line_start: int
    line_end: int
    children: List['ScriptNode'] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)


class GDScriptAnalyzer:
    """
    Unified GDScript analysis engine.
    
    Replaces separate gdscript_ast.py, static_analyzer.py,
    godot_validator.py, and godot_expert.py implementations.
    
    Provides:
    - Tokenization and parsing
    - Pattern analysis
    - Convention validation
    - Anti-pattern detection
    """
    
    def __init__(self):
        self._cache: Dict[str, ScriptNode] = {}
        self._findings: List[Finding] = []
        
        # Godot API patterns
        self.godot_lifecycle_methods = {
            '_ready', '_process', '_physics_process', '_input', 
            '_notification', '_exit_tree', '_enter_tree'
        }
        
        self.godot_signal_pattern = re.compile(r'^signal\s+(\w+)')
        self.export_pattern = re.compile(r'@export(?:\([^)]*\))?\s+var\s+(\w+)')
        self.func_pattern = re.compile(r'^func\s+(\w+)\s*\(')
        
    def tokenize(self, source_code: str) -> List[Dict[str, Any]]:
        """
        Tokenize GDScript source code into structured tokens.
        
        Args:
            source_code: GDScript source code string
            
        Returns:
            List of token dictionaries with type, value, line, column
        """
        tokens = []
        lines = source_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            col = 0
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Detect keywords and structures
            if stripped.startswith('func '):
                tokens.append({
                    'type': 'function_def',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('var '):
                tokens.append({
                    'type': 'variable_def',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('class_name '):
                tokens.append({
                    'type': 'class_def',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('signal '):
                tokens.append({
                    'type': 'signal_def',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('@export'):
                tokens.append({
                    'type': 'export_decorator',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('extends '):
                tokens.append({
                    'type': 'extends_clause',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            elif stripped.startswith('const '):
                tokens.append({
                    'type': 'constant_def',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
            else:
                tokens.append({
                    'type': 'statement',
                    'value': stripped,
                    'line': line_num,
                    'column': indent,
                    'indent': indent
                })
        
        return tokens
    
    def analyze_patterns(self, source_code: str, file_path: str = "") -> List[Finding]:
        """
        Analyze code for common patterns and best practices.
        
        Args:
            source_code: GDScript source code
            file_path: Optional file path for context
            
        Returns:
            List of Finding objects
        """
        findings = []
        lines = source_code.split('\n')
        
        has_extends = False
        has_ready = False
        variables = set()
        signals = set()
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for extends clause
            if stripped.startswith('extends '):
                has_extends = True
            
            # Check for _ready method
            if stripped.startswith('func _ready'):
                has_ready = True
            
            # Collect variable names
            var_match = re.match(r'^var\s+(\w+)', stripped)
            if var_match:
                variables.add(var_match.group(1))
            
            # Collect signal names
            signal_match = self.godot_signal_pattern.match(stripped)
            if signal_match:
                signals.add(signal_match.group(1))
            
            # Check for emit_signal usage
            if 'emit_signal(' in stripped:
                signal_name_match = re.search(r'emit_signal\(["\'](\w+)["\']', stripped)
                if signal_name_match:
                    signal_name = signal_name_match.group(1)
                    if signal_name not in signals:
                        findings.append(Finding(
                            line=line_num,
                            column=0,
                            severity='warning',
                            category='signals',
                            description=f"Emitting undefined signal '{signal_name}'",
                            suggestion=f"Declare 'signal {signal_name}' at the top of the script"
                        ))
        
        # Check for missing extends
        if not has_extends and source_code.strip():
            findings.append(Finding(
                line=1,
                column=0,
                severity='warning',
                category='structure',
                description="Missing 'extends' declaration",
                suggestion="Add 'extends Node', 'extends Control', or appropriate base class"
            ))
        
        # Check for unused variables (basic check)
        for var_name in variables:
            if var_name.startswith('_'):
                continue
            count = source_code.count(var_name)
            if count == 1:  # Only appears in declaration
                findings.append(Finding(
                    line=1,
                    column=0,
                    severity='info',
                    category='optimization',
                    description=f"Variable '{var_name}' is declared but never used",
                    suggestion="Remove unused variable or use it in the code"
                ))
        
        return findings
    
    def validate_conventions(self, source_code: str, file_path: str = "") -> List[Finding]:
        """
        Validate code against GDScript conventions and style guide.
        
        Args:
            source_code: GDScript source code
            file_path: Optional file path for context
            
        Returns:
            List of Finding objects for convention violations
        """
        findings = []
        lines = source_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check function naming (snake_case)
            func_match = self.func_pattern.match(stripped)
            if func_match:
                func_name = func_match.group(1)
                if func_name != func_name.lower().replace('_', func_name[0]):
                    if not func_name.startswith('_'):
                        # Allow camelCase for some Godot callbacks
                        if func_name not in self.godot_lifecycle_methods:
                            if any(c.isupper() for c in func_name[1:]):
                                findings.append(Finding(
                                    line=line_num,
                                    column=0,
                                    severity='warning',
                                    category='style',
                                    description=f"Function '{func_name}' should use snake_case",
                                    suggestion=f"Rename to '{func_name.lower()}'"
                                ))
            
            # Check for tabs (should use spaces)
            if '\t' in line:
                findings.append(Finding(
                    line=line_num,
                    column=line.index('\t'),
                    severity='warning',
                    category='style',
                    description="Tab character found",
                    suggestion="Use 4 spaces for indentation instead of tabs"
                ))
            
            # Check line length
            if len(stripped) > 120:
                findings.append(Finding(
                    line=line_num,
                    column=120,
                    severity='info',
                    category='style',
                    description=f"Line exceeds 120 characters ({len(stripped)} chars)",
                    suggestion="Break long lines into multiple statements"
                ))
            
            # Check for print statements in production code
            if stripped.startswith('print(') or stripped.startswith('printt('):
                findings.append(Finding(
                    line=line_num,
                    column=0,
                    severity='info',
                    category='debugging',
                    description="Debug print statement found",
                    suggestion="Remove print statements before production"
                ))
        
        return findings
    
    def detect_anti_patterns(self, source_code: str, file_path: str = "") -> List[Finding]:
        """
        Detect common anti-patterns and potential bugs.
        
        Args:
            source_code: GDScript source code
            file_path: Optional file path for context
            
        Returns:
            List of Finding objects for detected anti-patterns
        """
        findings = []
        lines = source_code.split('\n')
        
        in_function = None
        function_lines = 0
        function_start = 0
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track function boundaries
            func_match = self.func_pattern.match(stripped)
            if func_match:
                if in_function and function_lines > 50:
                    findings.append(Finding(
                        line=function_start,
                        column=0,
                        severity='warning',
                        category='complexity',
                        description=f"Function '{in_function}' is too long ({function_lines} lines)",
                        suggestion="Consider breaking into smaller functions"
                    ))
                in_function = func_match.group(1)
                function_lines = 0
                function_start = line_num
            
            if in_function:
                function_lines += 1
            
            # Check for _process doing heavy work
            if stripped.startswith('func _process'):
                # Look ahead for heavy operations
                for i in range(line_num, min(line_num + 20, len(lines))):
                    next_line = lines[i].strip()
                    if 'load(' in next_line or 'ResourceLoader' in next_line:
                        findings.append(Finding(
                            line=i+1,
                            column=0,
                            severity='error',
                            category='performance',
                            description="Heavy operation in _process()",
                            suggestion="Move resource loading to _ready() or use background loading"
                        ))
            
            # Check for direct scene instantiation in loops
            if 'while ' in stripped or 'for ' in stripped:
                # Look for instancing in loop body
                indent = len(line) - len(line.lstrip())
                for i in range(line_num, min(line_num + 10, len(lines))):
                    next_line = lines[i]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent and next_line.strip():
                        break
                    if 'instance()' in next_line or 'instantiate()' in next_line:
                        findings.append(Finding(
                            line=i+1,
                            column=0,
                            severity='warning',
                            category='performance',
                            description="Scene instantiation inside loop",
                            suggestion="Pre-instantiate scenes outside the loop"
                        ))
            
            # Check for missing null checks
            if 'get_node(' in stripped or '$' in stripped:
                if not ('if ' in stripped or '?. ' in stripped):
                    # Check if result is used without null check
                    for i in range(line_num, min(line_num + 3, len(lines))):
                        next_line = lines[i].strip()
                        if next_line and not next_line.startswith('#'):
                            if re.search(r'\w+\.', next_line):
                                findings.append(Finding(
                                    line=line_num,
                                    column=0,
                                    severity='info',
                                    category='safety',
                                    description="Node access without null check",
                                    suggestion="Use 'if node:' check or '?. ' safe navigation"
                                ))
                            break
        
        # Check last function
        if in_function and function_lines > 50:
            findings.append(Finding(
                line=function_start,
                column=0,
                severity='warning',
                category='complexity',
                description=f"Function '{in_function}' is too long ({function_lines} lines)",
                suggestion="Consider breaking into smaller functions"
            ))
        
        return findings
    
    def analyze_file(self, file_path: str) -> List[Finding]:
        """
        Perform complete analysis on a GDScript file.
        
        Args:
            file_path: Path to the .gd file
            
        Returns:
            Combined list of all findings
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            return [Finding(
                line=0,
                column=0,
                severity='error',
                category='io',
                description=f"Failed to read file: {e}"
            )]
        
        all_findings = []
        all_findings.extend(self.analyze_patterns(source_code, file_path))
        all_findings.extend(self.validate_conventions(source_code, file_path))
        all_findings.extend(self.detect_anti_patterns(source_code, file_path))
        
        return all_findings
    
    def get_summary(self, findings: List[Finding]) -> Dict[str, Any]:
        """Get summary statistics for findings."""
        by_severity = {'error': 0, 'warning': 0, 'info': 0}
        by_category = {}
        
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_category[f.category] = by_category.get(f.category, 0) + 1
        
        return {
            'total': len(findings),
            'by_severity': by_severity,
            'by_category': by_category
        }


# Convenience function for quick analysis
def analyze_gdscript(file_path: str) -> Dict[str, Any]:
    """
    Quick analysis of a GDScript file.
    
    Args:
        file_path: Path to .gd file
        
    Returns:
        Dictionary with findings and summary
    """
    analyzer = GDScriptAnalyzer()
    findings = analyzer.analyze_file(file_path)
    return {
        'findings': [
            {
                'line': f.line,
                'severity': f.severity,
                'category': f.category,
                'description': f.description,
                'suggestion': f.suggestion
            }
            for f in findings
        ],
        'summary': analyzer.get_summary(findings)
    }

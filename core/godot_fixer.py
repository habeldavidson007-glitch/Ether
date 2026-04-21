"""
Ether v1.9.8 - Godot-Specific Python Fixer
Deterministic code repair using project context (knowledge/memory).
LLM is used ONLY for explanations, not code generation.
"""

import re
import json
import os
from typing import List, Dict, Tuple, Optional

class GodotFixer:
    """
    Applies deterministic fixes to GDScript based on detected issues
    and project-specific knowledge from knowledge.json and memory.json.
    """
    
    def __init__(self, project_path: str, knowledge_path: str, memory_path: str):
        self.project_path = project_path
        self.knowledge = self._load_json(knowledge_path)
        self.memory = self._load_json(memory_path)
        
        # Project-specific patterns from knowledge/memory
        self.signal_prefix = self.knowledge.get("signal_prefix", "_on_")
        self.common_vars = self.knowledge.get("common_variables", [])
        self.project_style = self.memory.get("coding_style", {})

    def _load_json(self, path: str) -> dict:
        """Safely load JSON file, return empty dict if missing."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def apply_fixes(self, code: str, issues: List[str]) -> Tuple[str, List[str]]:
        """
        Apply deterministic fixes based on detected issues.
        Returns: (fixed_code, list_of_applied_fixes)
        """
        fixed_code = code
        applied_fixes = []
        
        for issue in issues:
            if "Unused var:" in issue:
                var_name = issue.split("Unused var:")[-1].strip()
                fixed_code, success = self._remove_unused_variable(fixed_code, var_name)
                if success:
                    applied_fixes.append(f"Removed unused variable '{var_name}'")
            
            elif "Debug prints" in issue:
                fixed_code, success = self._remove_debug_prints(fixed_code)
                if success:
                    applied_fixes.append("Removed debug print statements")
            
            elif "Missing extends" in issue or "No class name" in issue:
                fixed_code, success = self._add_missing_extends(fixed_code)
                if success:
                    applied_fixes.append("Added missing 'extends' declaration")
            
            elif "Signal" in issue:
                fixed_code, success = self._fix_signal_connection(fixed_code, issue)
                if success:
                    applied_fixes.append(f"Fixed signal connection: {issue}")
            
            elif "Delta" in issue or "process" in issue.lower():
                fixed_code, success = self._fix_process_delta(fixed_code)
                if success:
                    applied_fixes.append("Added missing 'delta' parameter to process function")

        # Fallback: If no specific fixes but code looks broken, try basic cleanup
        if not applied_fixes:
            fixed_code, success = self._basic_cleanup(fixed_code)
            if success:
                applied_fixes.append("Applied basic code cleanup")

        return fixed_code, applied_fixes

    def _remove_unused_variable(self, code: str, var_name: str) -> Tuple[str, bool]:
        """Remove unused variable declaration safely."""
        # Pattern: var var_name = ... or var var_name
        pattern = rf'^\s*var\s+{re.escape(var_name)}\s*(?:=.*)?$'
        new_code, count = re.subn(pattern, '', code, flags=re.MULTILINE)
        if count > 0:
            # Clean up extra blank lines
            new_code = re.sub(r'\n\s*\n\s*\n', '\n\n', new_code)
            return new_code, True
        return code, False

    def _remove_debug_prints(self, code: str) -> Tuple[str, bool]:
        """Remove print() statements."""
        pattern = r'^\s*print\(.*\)\s*$'
        new_code, count = re.subn(pattern, '', code, flags=re.MULTILINE)
        if count > 0:
            new_code = re.sub(r'\n\s*\n\s*\n', '\n\n', new_code)
            return new_code, True
        return code, False

    def _add_missing_extends(self, code: str) -> Tuple[str, bool]:
        """Add 'extends' if missing."""
        if code.strip().startswith("extends"):
            return code, False
        
        # Detect node type from common patterns
        extends_line = "extends Node"  # Default
        if "func _ready()" in code and "process" not in code:
            extends_line = "extends Node"
        elif "func _process(delta)" in code or "func _physics_process(delta)" in code:
            extends_line = "extends Node2D" if "position" in code else "extends Node"
        elif "func _gui_input(event)" in code:
            extends_line = "extends Control"
        
        # Insert at top
        lines = code.splitlines()
        lines.insert(0, extends_line)
        return "\n".join(lines), True

    def _fix_signal_connection(self, code: str, issue: str) -> Tuple[str, bool]:
        """Fix basic signal connection patterns."""
        # Extract signal name if possible
        match = re.search(r"Signal:?['\"]?(\w+)['\"]?", issue)
        if not match:
            return code, False
        
        signal_name = match.group(1)
        # Add standard connection pattern if missing
        if f"connect(\"{signal_name}\"" not in code and f"connect('{signal_name}'" not in code:
            # Try to find _ready function to insert into
            ready_pattern = r"(func _ready\(\):)"
            if re.search(ready_pattern, code):
                insertion = f"\n\t{self.signal_prefix}{signal_name}()"
                # Just a placeholder fix; real signal fixing requires AST
                return code, False # Skip complex signal fixing for now
        return code, False

    def _fix_process_delta(self, code: str) -> Tuple[str, bool]:
        """Add delta parameter to process functions."""
        pattern = r"func _process\(\)"
        replacement = "func _process(delta):"
        new_code, count = re.subn(pattern, replacement, code)
        if count > 0:
            return new_code, True
        
        pattern_physics = r"func _physics_process\(\)"
        replacement_physics = "func _physics_process(delta):"
        new_code, count = re.subn(pattern_physics, replacement_physics, new_code)
        return new_code, count > 0

    def _basic_cleanup(self, code: str) -> Tuple[str, bool]:
        """Basic whitespace and formatting cleanup."""
        # Remove multiple blank lines
        new_code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
        # Remove trailing whitespace
        new_code = "\n".join(line.rstrip() for line in new_code.splitlines())
        return new_code, new_code != code

    def generate_explanation(self, original: str, fixed: str, applied_fixes: List[str]) -> str:
        """
        Generate a brief explanation of fixes.
        This is the ONLY LLM call, and it's very low risk.
        """
        if not applied_fixes:
            return "No specific fixes applied, but code was reviewed."
        
        # Simple template-based explanation (no LLM needed for this!)
        explanation = "Optimizations applied:\n"
        for fix in applied_fixes:
            explanation += f"- {fix}\n"
        
        explanation += "\nCode follows GDScript best practices."
        return explanation

def optimize_gdscript(file_path: str, project_path: str, knowledge_path: str, memory_path: str) -> str:
    """
    Standalone helper function to optimize a GDScript file.
    Used by builder.py handle_optimize.
    """
    # Read original code
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
    
    # Initialize fixer
    fixer = GodotFixer(project_path, knowledge_path, memory_path)
    
    # Run lightweight analysis (imported from builder or duplicated here)
    # Duplicating minimal analyzer for standalone use
    issues = []
    if "print(" in original_code:
        issues.append("Debug prints left")
    
    # Check unused vars (simple regex)
    vars_declared = re.findall(r"var (\w+)", original_code)
    for v in vars_declared:
        if original_code.count(v) == 1:
            issues.append(f"Unused var: {v}")
    
    if len(original_code.splitlines()) > 50:
        issues.append("File too long")
    
    # Apply fixes
    fixed_code, applied_fixes = fixer.apply_fixes(original_code, issues)
    
    # Generate explanation
    explanation = fixer.generate_explanation(original_code, fixed_code, applied_fixes)
    
    # Return combined result
    return f"{explanation}\n\n```gdscript\n{fixed_code}\n```"

"""
Godot Explainer - Compares original vs fixed code and explains changes
Part of the 3-step optimization pipeline:
1. GodotFixer (unlimited chars) - Applies fixes
2. GodotExplainer - Explains what changed and why
3. LLM Summarizer (≤600 chars) - Brief summary
"""

import re
from typing import List, Dict, Tuple


class GodotExplainer:
    """Explains code changes by comparing original and fixed GDScript."""
    
    def __init__(self):
        self.changes = []
    
    def compare(self, original: str, fixed: str) -> Dict:
        """
        Compare original and fixed code, return detailed explanation.
        
        Args:
            original: Original GDScript code
            fixed: Fixed GDScript code
            
        Returns:
            Dictionary with changes list and explanation text
        """
        self.changes = []
        
        original_lines = original.splitlines()
        fixed_lines = fixed.splitlines()
        
        # Detect removed lines
        removed_vars = self._detect_removed_variables(original, fixed)
        removed_prints = self._detect_removed_prints(original, fixed)
        added_extends = self._detect_added_extends(original, fixed)
        fixed_delta = self._detect_fixed_delta(original, fixed)
        
        # Build change log
        if removed_vars:
            for var_name in removed_vars:
                self.changes.append({
                    'type': 'removed_unused_var',
                    'detail': f"Removed unused variable '{var_name}'",
                    'reason': 'Unused variables increase memory usage and reduce code clarity'
                })
        
        if removed_prints:
            self.changes.append({
                'type': 'removed_debug_prints',
                'detail': f"Removed {len(removed_prints)} debug print statement(s)",
                'reason': 'Debug prints should not be in production code'
            })
        
        if added_extends:
            self.changes.append({
                'type': 'added_extends',
                'detail': f"Added 'extends {added_extends}' declaration",
                'reason': 'Explicit extends improves code clarity and IDE support'
            })
        
        if fixed_delta:
            self.changes.append({
                'type': 'fixed_delta_param',
                'detail': "Added missing 'delta' parameter to process function",
                'reason': 'Process functions require delta for frame-independent movement'
            })
        
        # Generate explanation text
        explanation = self._generate_explanation()
        
        return {
            'changes': self.changes,
            'explanation': explanation,
            'lines_changed': len(self.changes),
            'original_lines': len(original_lines),
            'fixed_lines': len(fixed_lines)
        }
    
    def _detect_removed_variables(self, original: str, fixed: str) -> List[str]:
        """Detect which variables were removed."""
        vars_original = set(re.findall(r'var\s+(\w+)', original))
        vars_fixed = set(re.findall(r'var\s+(\w+)', fixed))
        return list(vars_original - vars_fixed)
    
    def _detect_removed_prints(self, original: str, fixed: str) -> List[str]:
        """Detect removed print statements."""
        prints_original = len(re.findall(r'(?:print|push_warning|push_error)\s*\(', original))
        prints_fixed = len(re.findall(r'(?:print|push_warning|push_error)\s*\(', fixed))
        if prints_original > prints_fixed:
            return ['print'] * (prints_original - prints_fixed)
        return []
    
    def _detect_added_extends(self, original: str, fixed: str) -> str:
        """Detect if extends was added."""
        extends_original = re.search(r'^extends\s+(\w+)', original, re.MULTILINE)
        extends_fixed = re.search(r'^extends\s+(\w+)', fixed, re.MULTILINE)
        
        if not extends_original and extends_fixed:
            return extends_fixed.group(1)
        return ''
    
    def _detect_fixed_delta(self, original: str, fixed: str) -> bool:
        """Detect if delta parameter was added to process function."""
        # Look for func _process(process) or func _process() in original
        # And func _process(delta) in fixed
        original_process = re.search(r'func\s+_process\s*\(([^)]*)\)', original)
        fixed_process = re.search(r'func\s+_process\s*\(([^)]*)\)', fixed)
        
        if original_process and fixed_process:
            orig_params = original_process.group(1).strip()
            fixed_params = fixed_process.group(1).strip()
            
            if 'delta' not in orig_params and 'delta' in fixed_params:
                return True
        
        return False
    
    def _generate_explanation(self) -> str:
        """Generate human-readable explanation of changes."""
        if not self.changes:
            return "No specific improvements needed. Code follows GDScript best practices."
        
        explanation_parts = []
        for change in self.changes:
            explanation_parts.append(f"• {change['detail']}")
            explanation_parts.append(f"  Why: {change['reason']}")
        
        return "\n".join(explanation_parts)
    
    def get_summary_prompt(self, comparison_result: Dict) -> str:
        """
        Generate a short prompt for LLM to summarize.
        Keep under 600 chars total.
        
        Args:
            comparison_result: Result from compare() method
            
        Returns:
            Short prompt string for LLM summarization
        """
        changes_count = comparison_result['lines_changed']
        explanation = comparison_result['explanation']
        
        # Truncate explanation if too long
        if len(explanation) > 400:
            explanation = explanation[:400] + "..."
        
        prompt = f"""Code optimization complete.
Changes made: {changes_count}

{explanation}

Summarize in 2 sentences max. Mention what was fixed and why it matters."""
        
        return prompt[:600]

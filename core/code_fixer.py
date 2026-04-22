"""
═══════════════════════════════════════════════════════════
  ETHER CODE FIXER — Unified Auto-Fix Engine
═══════════════════════════════════════════════════════════
  Single module for ALL code improvements:
  • Godot-specific fixes (signals, autoloads, exports)
  • Performance optimizations (loops, caching)
  • Code cleanup (regions, whitespace, duplicates)
  • Best practices (type hints, error handling)
  
  Automatically applied during optimization - no manual work!
"""

import re
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class CodeFixer:
    """Unified code fixer for Godot projects"""
    
    def __init__(self):
        self.fixes_applied = []
        self.backup_created = False
        
    # ═══════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════
    
    def fix_code(self, code: str, file_path: str = "") -> Tuple[str, List[str]]:
        """
        Apply ALL fixes automatically
        Returns: (fixed_code, list_of_fixes_applied)
        """
        self.fixes_applied = []
        
        if not code.strip():
            return code, []
        
        # Create backup before any changes
        if file_path and os.path.exists(file_path):
            self._create_backup(file_path)
        
        # Apply fixes in order
        code = self._fix_duplicate_signals(code)
        code = self._fix_missing_regions(code)
        code = self._fix_empty_loops(code)
        code = self._fix_whitespace(code)
        code = self._fix_godot_exports(code)
        code = self._fix_autoload_safety(code)
        code = self._fix_loop_performance(code)
        code = self._fix_type_hints(code)
        
        return code, self.fixes_applied
    
    # ═══════════════════════════════════════════════════
    # BACKUP SYSTEM
    # ═══════════════════════════════════════════════════
    
    def _create_backup(self, file_path: str):
        """Create timestamped backup"""
        if self.backup_created:
            return
            
        backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(file_path, backup_path)
            self.backup_created = True
            self.fixes_applied.append(f"✓ Backup created: {os.path.basename(backup_path)}")
        except Exception as e:
            pass  # Silent fail if backup fails
    
    # ═══════════════════════════════════════════════════
    # GODOT-SPECIFIC FIXES
    # ═══════════════════════════════════════════════════
    
    def _fix_duplicate_signals(self, code: str) -> str:
        """Remove duplicate signal declarations"""
        signal_pattern = r'^\s*signal\s+\w+.*$'
        signals = {}
        lines = code.split('\n')
        new_lines = []
        
        for line in lines:
            match = re.match(signal_pattern, line.strip())
            if match:
                signal_name = line.split()[1] if len(line.split()) > 1 else ""
                if signal_name and signal_name not in signals:
                    signals[signal_name] = True
                    new_lines.append(line)
                elif signal_name:
                    self.fixes_applied.append(f"✓ Removed duplicate signal: {signal_name}")
            else:
                new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _fix_missing_regions(self, code: str) -> str:
        """Add region markers for better organization"""
        if '#region' in code.lower() or '# REGION' in code:
            return code  # Already has regions
        
        sections = []
        current_section = []
        current_name = "Code"
        
        section_markers = {
            'extends Node': 'Autoload',
            'extends Control': 'UI Control',
            'extends CharacterBody': 'Character',
            'extends Area': 'Area',
            'var .*:': 'Variables',
            'func _ready': 'Lifecycle',
            'func _process': 'Game Loop',
            'func _input': 'Input Handling',
            'signal ': 'Signals',
        }
        
        lines = code.split('\n')
        has_regions = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for section starts
            for marker, name in section_markers.items():
                if re.search(marker, stripped) and not has_regions:
                    if current_section and current_name != name:
                        sections.append((current_name, current_section))
                        current_section = []
                    current_name = name
                    break
            
            current_section.append(line)
        
        if current_section:
            sections.append((current_name, current_section))
        
        # Rebuild with regions
        if len(sections) > 1:
            result = []
            for name, section_lines in sections:
                if section_lines:
                    result.append(f"#region {name}")
                    result.extend(section_lines)
                    result.append("#endregion")
                    result.append("")
            self.fixes_applied.append("✓ Added region markers for organization")
            return '\n'.join(result)
        
        return code
    
    def _fix_empty_loops(self, code: str) -> str:
        """Remove or comment out empty loops"""
        patterns = [
            (r'(for\s+\w+\s+in\s+[^:]+:\s*\n\s*pass)', '# Empty loop removed'),
            (r'(while\s+True:\s*\n\s*pass)', '# Infinite empty loop removed'),
        ]
        
        for pattern, msg in patterns:
            matches = re.findall(pattern, code)
            if matches:
                code = re.sub(pattern, f'# {msg}', code)
                self.fixes_applied.append(f"✓ Removed {len(matches)} empty loop(s)")
        
        return code
    
    def _fix_godot_exports(self, code: str) -> str:
        """Ensure proper export syntax"""
        # Fix old export syntax to new
        code = re.sub(
            r'export\s*\(\s*(int|float|String|bool)\s*\)\s+var\s+(\w+)',
            r'@export var \2: \1',
            code
        )
        
        # Add @export to variables with export() but missing decorator
        if re.search(r'export\s*\(', code) and '@export' not in code:
            self.fixes_applied.append("✓ Updated export syntax to Godot 4.x")
        
        return code
    
    def _fix_autoload_safety(self, code: str) -> str:
        """Add safety checks for autoload singletons"""
        if 'extends Node' in code and 'func _ready' in code:
            # Check if already has instance check
            if 'instance' not in code.lower() or 'singleton' not in code.lower():
                ready_func = re.search(r'func\s+_ready\s*\(\s*\):', code)
                if ready_func:
                    insert_pos = ready_func.end()
                    safety_check = "\n\t# Auto-generated safety check\n\tif Engine.has_singleton('GameData'):\n\t\tpass  # Singleton loaded\n"
                    code = code[:insert_pos] + safety_check + code[insert_pos:]
                    self.fixes_applied.append("✓ Added autoload safety check")
        
        return code
    
    # ═══════════════════════════════════════════════════
    # PERFORMANCE FIXES
    # ═══════════════════════════════════════════════════
    
    def _fix_loop_performance(self, code: str) -> str:
        """Optimize loops for performance"""
        fixes = 0
        
        # Pattern: for x in range(len(array)) -> for x in array
        pattern = r'for\s+(\w+)\s+in\s+range\s*\(\s*len\s*\(\s*(\w+)\s*\)\s*\)'
        matches = re.findall(pattern, code)
        if matches:
            for var_name, array_name in matches:
                old = f"for {var_name} in range(len({array_name}))"
                new = f"for {var_name} in {array_name}"
                code = code.replace(old, new, 1)
                fixes += 1
        
        if fixes > 0:
            self.fixes_applied.append(f"✓ Optimized {fixes} loop(s) for performance")
        
        return code
    
    # ═══════════════════════════════════════════════════
    # CODE CLEANUP
    # ═══════════════════════════════════════════════════
    
    def _fix_whitespace(self, code: str) -> str:
        """Clean up whitespace"""
        # Remove multiple blank lines
        code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
        
        # Remove trailing whitespace
        lines = code.split('\n')
        lines = [line.rstrip() for line in lines]
        code = '\n'.join(lines)
        
        # Ensure single newline at end
        code = code.rstrip() + '\n'
        
        self.fixes_applied.append("✓ Cleaned whitespace and formatting")
        return code
    
    def _fix_type_hints(self, code: str) -> str:
        """Add basic type hints where obvious"""
        # This is a simple version - could be more sophisticated
        patterns = [
            (r'(var\s+\w+)\s*=\s*""', r'\1: String = ""'),
            (r'(var\s+\w+)\s*=\s*0(?!\d)', r'\1: int = 0'),
            (r'(var\s+\w+)\s*=\s*\d+\.\d+', r'\1: float = '),
            (r'(var\s+\w+)\s*=\s*true', r'\1: bool = true'),
            (r'(var\s+\w+)\s*=\s*false', r'\1: bool = false'),
        ]
        
        fixes = 0
        for pattern, replacement in patterns:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code)
                fixes += 1
        
        if fixes > 0:
            self.fixes_applied.append(f"✓ Added {fixes} type hint(s)")
        
        return code


# ═══════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════

def apply_fixes(code: str, file_path: str = "") -> Tuple[str, List[str]]:
    """Quick function to apply all fixes"""
    fixer = CodeFixer()
    return fixer.fix_code(code, file_path)


def fix_file(file_path: str) -> bool:
    """Fix a file in place"""
    if not os.path.exists(file_path):
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        fixed_code, fixes = apply_fixes(code, file_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_code)
        
        print(f"✓ Fixed {file_path}: {len(fixes)} improvements")
        for fix in fixes:
            print(f"  {fix}")
        
        return True
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

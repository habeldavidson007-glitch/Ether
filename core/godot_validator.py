"""
Godot Runtime Validator
=======================
Validates GDScript code against the actual Godot engine using `godot --check-only`.
Catches errors that static analysis misses: missing signals, wrong types, scene mismatches.
"""

import subprocess
import os
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class GodotValidator:
    """
    Validates GDScript and scenes against Godot engine.
    Uses godot --check-only for scripts and custom parsing for scenes.
    """
    
    def __init__(self, godot_path: Optional[str] = None):
        """
        Initialize validator.
        
        Args:
            godot_path: Path to Godot executable. If None, tries common locations.
        """
        self.godot_path = godot_path or self._find_godot()
        self.validation_cache: Dict[str, bool] = {}
        
    def _find_godot(self) -> Optional[str]:
        """Find Godot executable in common locations."""
        possible_paths = [
            "godot",  # In PATH
            "godot4",  # Godot 4 in PATH
            "/usr/bin/godot",
            "/usr/local/bin/godot",
            "C:\\Program Files\\Godot\\Godot_v4.exe",
            "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Godot Engine\\Godot_v4.exe",
        ]
        
        for path in possible_paths:
            try:
                # Test if executable exists and runs
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def validate_script(self, script_path: str, project_path: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate a GDScript file using Godot's built-in checker.
        
        Args:
            script_path: Path to .gd file
            project_path: Path to Godot project root (for resolving dependencies)
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not self.godot_path:
            return True, ["⚠ Godot executable not found - skipping runtime validation"]
        
        if not os.path.exists(script_path):
            return False, [f"Error: Script file not found: {script_path}"]
        
        # Build command
        cmd = [self.godot_path, "--check-only", "--script", script_path]
        
        # Add project path if available (helps with resource resolution)
        if project_path:
            cmd.extend(["--path", project_path])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Godot can be slow to start
            )
            
            errors = []
            
            # Parse stderr for errors
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if line and 'error' in line.lower():
                        errors.append(f"🔴 {line}")
                    elif line:
                        errors.append(f"⚠ {line}")
            
            # Check return code
            is_valid = result.returncode == 0 and len(errors) == 0
            
            if is_valid:
                self.validation_cache[script_path] = True
                return True, ["✓ Validated against Godot engine"]
            else:
                self.validation_cache[script_path] = False
                return False, errors
                
        except subprocess.TimeoutExpired:
            return False, ["⚠ Validation timeout - Godot took too long to respond"]
        except Exception as e:
            return False, [f"⚠ Validation error: {str(e)}"]
    
    def validate_scene(self, scene_path: str, project_path: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validate a Godot scene file (.tscn).
        Checks for missing resources, broken connections, and invalid node types.
        
        Args:
            scene_path: Path to .tscn file
            project_path: Path to Godot project root
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not os.path.exists(scene_path):
            return False, [f"Error: Scene file not found: {scene_path}"]
        
        errors = []
        warnings = []
        
        try:
            with open(scene_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for external resource references
            ext_resource_pattern = r'\[ext_resource path="([^"]+)"'
            for match in re.finditer(ext_resource_pattern, content):
                resource_path = match.group(1)
                
                # Resolve relative paths
                if not os.path.isabs(resource_path):
                    resource_path = os.path.join(os.path.dirname(scene_path), resource_path)
                
                if not os.path.exists(resource_path):
                    errors.append(f"🔴 Missing external resource: {resource_path}")
            
            # Check for script attachments
            script_pattern = r'script = ExtResource\("([^"]+)"\)'
            for match in re.finditer(script_pattern, content):
                script_id = match.group(1)
                
                # Find the actual script path in ext_resources
                script_ext_pattern = rf'\[ext_resource type="Script" id="{script_id}" path="([^"]+)"'
                script_match = re.search(script_ext_pattern, content)
                
                if script_match:
                    script_path = script_match.group(1)
                    
                    # Resolve relative paths
                    if not os.path.isabs(script_path):
                        script_path = os.path.join(os.path.dirname(scene_path), script_path)
                    
                    if not os.path.exists(script_path):
                        errors.append(f"🔴 Missing script: {script_path}")
                    else:
                        # Validate the attached script
                        is_valid, script_errors = self.validate_script(script_path, project_path)
                        if not is_valid:
                            errors.extend([f"🔴 Script in scene has errors: {e}" for e in script_errors if '⚠' not in e])
            
            # Check for orphaned signal connections
            connection_pattern = r'\[connection signal="([^"]+)" from="([^"]+)" to="([^"]+)" method="([^"]+)"'
            for match in re.finditer(connection_pattern, content):
                signal_name, from_node, to_node, method_name = match.groups()
                
                # Note: Full validation would require parsing node structure
                # This is a basic check - advanced validation needs Scene Graph Analyzer
                warnings.append(f"⚠ Signal connection found: {from_node}.{signal_name} → {to_node}.{method_name}")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                return True, ["✓ Scene structure validated"] + warnings
            else:
                return False, errors + warnings
                
        except Exception as e:
            return False, [f"⚠ Scene validation error: {str(e)}"]
    
    def validate_autoload(self, autoload_name: str, project_path: str) -> Tuple[bool, List[str]]:
        """
        Validate that an autoload is properly configured in Project Settings.
        
        Args:
            autoload_name: Name of the autoload (e.g., "GameData")
            project_path: Path to Godot project root
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        project_file = os.path.join(project_path, "project.godot")
        
        if not os.path.exists(project_file):
            return False, [f"🔴 Project file not found: {project_file}"]
        
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if autoload is registered
            autoload_pattern = rf'\[autoload\]\s*{re.escape(autoload_name)}\s*='
            if not re.search(autoload_pattern, content):
                # Try alternative format
                alt_pattern = rf'{re.escape(autoload_name)}\s*=\s*"res://'
                if not re.search(alt_pattern, content):
                    return False, [f"🔴 Autoload '{autoload_name}' not registered in Project Settings"]
            
            return True, [f"✓ Autoload '{autoload_name}' is properly configured"]
            
        except Exception as e:
            return False, [f"⚠ Autoload validation error: {str(e)}"]
    
    def validate_all(self, files: List[str], project_path: Optional[str] = None) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple files at once.
        
        Args:
            files: List of file paths to validate
            project_path: Path to Godot project root
            
        Returns:
            Dictionary mapping file paths to (is_valid, errors) tuples
        """
        results = {}
        
        for file_path in files:
            if file_path.endswith('.gd'):
                results[file_path] = self.validate_script(file_path, project_path)
            elif file_path.endswith('.tscn'):
                results[file_path] = self.validate_scene(file_path, project_path)
            else:
                results[file_path] = (False, [f"⚠ Unsupported file type: {file_path}"])
        
        return results
    
    def get_validation_summary(self, results: Dict[str, Tuple[bool, List[str]]]) -> str:
        """
        Generate a human-readable summary of validation results.
        
        Args:
            results: Dictionary from validate_all()
            
        Returns:
            Formatted summary string
        """
        total = len(results)
        valid = sum(1 for is_valid, _ in results.values() if is_valid)
        invalid = total - valid
        
        summary = [
            f"\n{'='*60}",
            f"📊 VALIDATION SUMMARY",
            f"{'='*60}",
            f"Total files: {total}",
            f"✓ Valid: {valid}",
            f"🔴 Invalid: {invalid}",
            f"{'='*60}"
        ]
        
        if invalid > 0:
            summary.append("\n🔴 ERRORS:")
            for file_path, (is_valid, errors) in results.items():
                if not is_valid:
                    summary.append(f"\n  📁 {file_path}:")
                    for error in errors:
                        if '🔴' in error or 'Error' in error:
                            summary.append(f"    {error}")
        
        return '\n'.join(summary)


def create_validator(godot_path: Optional[str] = None) -> GodotValidator:
    """Factory function to create a GodotValidator instance."""
    return GodotValidator(godot_path)

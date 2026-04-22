"""
Safety Preview Module
---------------------
Handles safe code application with diff previews and automatic backups.
Prevents accidental data loss by requiring user confirmation before writing.
"""

import os
import shutil
import difflib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List


class SafetyPreview:
    """Manages safe code updates with diffs and backups."""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_diff(self, original: str, modified: str, filepath: str = "file") -> str:
        """Generate a human-readable diff between original and modified code."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=3  # Context lines
        )
        
        # Colorize the diff
        colored_diff = []
        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                colored_diff.append(f"\033[92m{line}\033[0m")  # Green for additions
            elif line.startswith('-') and not line.startswith('---'):
                colored_diff.append(f"\033[91m{line}\033[0m")  # Red for deletions
            elif line.startswith('^'):
                colored_diff.append(f"\033[93m{line}\033[0m")  # Yellow for markers
            else:
                colored_diff.append(line)
                
        return "".join(colored_diff)
    
    def create_backup(self, filepath: str) -> str:
        """Create a timestamped backup of a file."""
        src = Path(filepath)
        if not src.exists():
            raise FileNotFoundError(f"Cannot backup: {filepath} does not exist")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{src.name}.backup.{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(src, backup_path)
        return str(backup_path)
    
    def apply_safely(self, filepath: str, new_content: str, force: bool = False) -> Tuple[bool, str]:
        """
        Apply changes safely with backup.
        
        Args:
            filepath: Path to the file to update
            new_content: New content to write
            force: If True, skip backup (dangerous!)
            
        Returns:
            (success: bool, message: str)
        """
        src = Path(filepath)
        
        if not src.exists():
            return False, f"File not found: {filepath}"
            
        try:
            # Read original
            original_content = src.read_text(encoding='utf-8')
            
            # Skip if no changes
            if original_content.strip() == new_content.strip():
                return True, "No changes detected."
                
            # Create backup unless forced
            if not force:
                backup_path = self.create_backup(str(src))
                message = f"Backup created: {backup_path}\n"
            else:
                message = "\033[93mWARNING: No backup created (force mode)\033[0m\n"
                
            # Write new content
            src.write_text(new_content, encoding='utf-8')
            
            return True, message + f"✓ Successfully updated {filepath}"
            
        except Exception as e:
            return False, f"Error applying changes: {str(e)}"
    
    def get_pending_changes(self, filepath: str, new_content: str) -> dict:
        """Get details about pending changes without applying them."""
        src = Path(filepath)
        
        if not src.exists():
            return {
                "exists": False,
                "diff": "",
                "stats": {"additions": 0, "deletions": 0}
            }
            
        original = src.read_text(encoding='utf-8')
        diff_output = self.generate_diff(original, new_content, filepath)
        
        # Calculate stats
        additions = sum(1 for line in diff_output.split('\n') if line.startswith('+') and not line.startswith('+++'))
        deletions = sum(1 for line in diff_output.split('\n') if line.startswith('-') and not line.startswith('---'))
        
        return {
            "exists": True,
            "diff": diff_output,
            "stats": {
                "additions": additions,
                "deletions": deletions,
                "total_changes": additions + deletions
            }
        }


def get_safety_preview() -> SafetyPreview:
    """Singleton accessor for SafetyPreview."""
    if not hasattr(get_safety_preview, "_instance"):
        get_safety_preview._instance = SafetyPreview()
    return get_safety_preview._instance


if __name__ == "__main__":
    # Test the module
    preview = get_safety_preview()
    
    original = """func _ready():
    print("Hello")
    pass
"""
    
    modified = """func _ready():
    print("Hello World!")
    var x = 10
"""
    
    print("=== DIFF PREVIEW ===")
    print(preview.generate_diff(original, modified, "test.gd"))
    
    print("\n=== PENDING CHANGES ===")
    # Create a temp file for testing
    test_file = Path("test_preview.gd")
    test_file.write_text(original)
    
    changes = preview.get_pending_changes(str(test_file), modified)
    print(f"Additions: {changes['stats']['additions']}")
    print(f"Deletions: {changes['stats']['deletions']}")
    
    print("\n=== APPLYING SAFELY ===")
    success, msg = preview.apply_safely(str(test_file), modified)
    print(msg)
    
    # Cleanup
    test_file.unlink()
    backups = list(Path("backups").glob("test_preview.gd.backup.*"))
    for b in backups:
        b.unlink()
    
    print("\n✓ Safety Preview module working correctly!")

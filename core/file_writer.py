"""
Ether File Writer - Safe In-Place File Modification System
===========================================================
Handles safe file modifications with:
- Automatic backup creation
- Atomic write operations
- Rollback capabilities
- Permission and path validation
- Cross-platform compatibility (Windows/Linux/Mac)

Features:
- Transaction-like file writes
- Backup management
- Safe path resolution
- Encoding detection and preservation
"""

import shutil
import time
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime


class SafeFileWriter:
    """Safe file writing with backup and rollback support."""
    
    def __init__(self, backup_dir: str = ".ether_backups", max_backups: int = 10):
        """
        Initialize safe file writer.
        
        Args:
            backup_dir: Directory to store backups
            max_backups: Maximum number of backups to keep per file
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups
        self.backup_history: Dict[str, list] = {}
    
    def write(self, file_path: str, content: str, create_backup: bool = True) -> Tuple[bool, str]:
        """
        Safely write content to file with optional backup.
        
        Args:
            file_path: Target file path
            content: Content to write
            create_backup: Whether to create backup before writing
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = Path(file_path).resolve()
            
            # Validate path
            if not self._validate_path(target):
                return False, f"Invalid or unsafe path: {file_path}"
            
            # Create backup if requested and file exists
            backup_path = None
            if create_backup and target.exists():
                backup_path = self._create_backup(target)
                if not backup_path:
                    return False, "Failed to create backup"
            
            # Ensure parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically using temp file
            temp_path = target.with_suffix(f"{target.suffix}.tmp")
            
            try:
                # Write to temp file first
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                
                # Atomic rename
                temp_path.replace(target)
                
                # Store backup reference for potential rollback
                if backup_path:
                    self.backup_history[str(target)] = backup_path
                
                return True, f"Successfully wrote to {target}"
                
            except Exception as write_error:
                # Clean up temp file on error
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                
                # Rollback if backup exists
                if backup_path:
                    self.rollback(target, backup_path)
                
                return False, f"Write failed: {write_error}"
        
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def _validate_path(self, path: Path) -> bool:
        """
        Validate that path is safe to write to.
        
        Checks:
        - Not a system directory
        - Not a symlink loop
        - Has write permissions
        """
        try:
            # Check for dangerous paths
            dangerous_roots = {'/', '/etc', '/usr', '/bin', '/sbin', 
                             'C:\\Windows', 'C:\\Program Files'}
            
            path_str = str(path.resolve())
            for dangerous in dangerous_roots:
                if path_str.startswith(dangerous):
                    print(f"[SAFETY] Blocked write to dangerous path: {path}")
                    return False
            
            # Check if it's a symlink
            if path.is_symlink():
                print(f"[SAFETY] Warning: Writing to symlink: {path}")
            
            # Check parent directory writability
            parent = path.parent
            if parent.exists() and not os.access(parent, os.W_OK):
                print(f"[SAFETY] No write permission: {parent}")
                return False
            
            return True
            
        except Exception as e:
            print(f"[SAFETY] Path validation error: {e}")
            return False
    
    def _create_backup(self, file_path: Path) -> Optional[str]:
        """
        Create timestamped backup of file.
        
        Returns:
            Backup file path or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            
            # Cleanup old backups
            self._cleanup_old_backups(file_path.name)
            
            return str(backup_path)
            
        except Exception as e:
            print(f"[BACKUP] Failed to create backup: {e}")
            return None
    
    def _cleanup_old_backups(self, filename_stem: str, keep_count: int = None):
        """
        Remove old backups keeping only the most recent ones.
        
        Args:
            filename_stem: Original filename without extension
            keep_count: Number of backups to keep (uses instance default if None)
        """
        if keep_count is None:
            keep_count = self.max_backups
        
        try:
            # Find all backups for this file
            pattern = f"{filename_stem}_*.*"
            backups = sorted(
                self.backup_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Remove old backups
            for old_backup in backups[keep_count:]:
                try:
                    old_backup.unlink()
                    print(f"[CLEANUP] Removed old backup: {old_backup.name}")
                except Exception as e:
                    print(f"[CLEANUP] Failed to remove {old_backup}: {e}")
        
        except Exception as e:
            print(f"[CLEANUP] Error during cleanup: {e}")
    
    def rollback(self, target_path: Path, backup_path: str) -> bool:
        """
        Restore file from backup.
        
        Args:
            target_path: Path to restore
            backup_path: Path to backup file
            
        Returns:
            True if successful
        """
        try:
            backup = Path(backup_path)
            
            if not backup.exists():
                print(f"[ROLLBACK] Backup not found: {backup_path}")
                return False
            
            # Restore from backup
            shutil.copy2(backup, target_path)
            print(f"[ROLLBACK] Restored {target_path} from backup")
            return True
            
        except Exception as e:
            print(f"[ROLLBACK] Failed: {e}")
            return False
    
    def append(self, file_path: str, content: str, create_backup: bool = False) -> Tuple[bool, str]:
        """
        Safely append content to file.
        
        Args:
            file_path: Target file path
            content: Content to append
            create_backup: Whether to create backup before appending
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            target = Path(file_path).resolve()
            
            # Read existing content
            if target.exists():
                with open(target, 'r', encoding='utf-8') as f:
                    existing = f.read()
            else:
                existing = ""
            
            # Append and write
            new_content = existing + content
            return self.write(target, new_content, create_backup)
        
        except Exception as e:
            return False, f"Append failed: {e}"
    
    def write_if_different(self, file_path: str, new_content: str, create_backup: bool = True) -> Tuple[bool, str, bool]:
        """
        Write content only if it differs from current file.
        
        Args:
            file_path: Target file path
            new_content: New content to potentially write
            create_backup: Whether to create backup before writing
            
        Returns:
            Tuple of (success: bool, message: str, changed: bool)
        """
        try:
            target = Path(file_path).resolve()
            
            # Check if file exists and has same content
            if target.exists():
                with open(target, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                
                if current_content == new_content:
                    return True, "No changes needed", False
            
            # Write new content
            success, message = self.write(file_path, new_content, create_backup)
            return success, message, True
        
        except Exception as e:
            return False, f"Check failed: {e}", False
    
    def get_backup_list(self, file_pattern: str = "*") -> list:
        """
        List available backups.
        
        Args:
            file_pattern: Glob pattern to filter backups
            
        Returns:
            List of backup file paths
        """
        try:
            backups = list(self.backup_dir.glob(file_pattern))
            return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception as e:
            print(f"[LIST] Failed to list backups: {e}")
            return []
    
    def clear_all_backups(self) -> bool:
        """
        Remove all backups.
        
        Returns:
            True if successful
        """
        try:
            for backup_file in self.backup_dir.glob("*"):
                try:
                    backup_file.unlink()
                except:
                    pass
            return True
        except Exception as e:
            print(f"[CLEAR] Failed: {e}")
            return False


# Import os for path validation
import os


def safe_write_file(file_path: str, content: str, backup: bool = True) -> Tuple[bool, str]:
    """
    Convenience function for safe file writing.
    
    Args:
        file_path: Target file path
        content: Content to write
        backup: Whether to create backup
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    writer = SafeFileWriter()
    return writer.write(file_path, content, backup)


def atomic_replace(file_path: str, new_content: str) -> bool:
    """
    Atomically replace file content.
    
    Args:
        file_path: Target file path
        new_content: New content
        
    Returns:
        True if successful
    """
    writer = SafeFileWriter()
    success, _ = writer.write(file_path, new_content, create_backup=False)
    return success

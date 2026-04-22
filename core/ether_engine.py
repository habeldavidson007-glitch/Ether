"""
Ether Engine — Unified Facade for Godot AI Development Assistant
=================================================================
A thin coordinator layer that orchestrates specialized modules
and provides a simple unified API for ether_cli.py.

Benefits:
✅ Single entry point for CLI (from ether_engine import EtherEngine)
✅ Clean separation of concerns
✅ Easy debugging and testing
✅ Memory efficient (lazy loading)
✅ Future-proof for adding new features

This is NOT a mega-file — it imports and coordinates specialized modules.
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Lazy imports — only load what we need when we need it
class EtherEngine:
    """
    Unified coordinator for all Ether AI capabilities.
    
    Provides a single interface for:
    - Project loading and management
    - Code analysis and optimization
    - Debugging and error fixing
    - RAG-enhanced context retrieval
    - Chat and explanation
    
    All heavy lifting is delegated to specialized modules.
    """
    
    def __init__(self):
        self._brain = None
        self._project_loader = None
        self._rag_engine = None
        self._static_analyzer = None
        self._dependency_graph = None  # NEW: Dependency graph engine
        
        self.project_path: Optional[str] = None
        self.project_stats: Dict[str, int] = {}
        self.chat_mode: str = "mixed"
        self.history: List[Dict[str, str]] = []
        self.last_optimized_code: Optional[str] = None
        
        # Lazy initialization flag
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy-load core components on first use."""
        if self._initialized:
            return
        
        # Import here to avoid circular dependencies and enable lazy loading
        from core.builder import EtherBrain
        from utils.project_loader import LazyProjectLoader
        
        self._brain = EtherBrain()
        self._project_loader = LazyProjectLoader()
        
        # Try to import optional components
        try:
            from core.rag_engine import RAGEngine
            self._rag_engine = RAGEngine()
        except ImportError:
            self._rag_engine = None
        
        try:
            from core.static_analyzer import StaticAnalyzer
            self._static_analyzer = StaticAnalyzer()
        except ImportError:
            self._static_analyzer = None
            
        try:
            from core.dependency_graph import DependencyGraph
            self._dependency_graph = DependencyGraph()
        except ImportError:
            self._dependency_graph = None
        
        self._initialized = True
    
    @property
    def brain(self):
        """Access the underlying EtherBrain instance."""
        self._ensure_initialized()
        return self._brain
    
    def load_project(self, path: str) -> Tuple[bool, str]:
        """
        Load a Godot project from directory.
        
        Args:
            path: Path to the Godot project folder
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        self._ensure_initialized()
        
        # Remove quotes if present
        path = path.strip('"').strip("'")
        project_dir = Path(path).expanduser().resolve()
        
        if not project_dir.exists():
            return False, f"Directory '{path}' does not exist."
        
        if not project_dir.is_dir():
            return False, f"'{path}' is not a directory."
        
        # Check for Godot project file
        project_file = project_dir / "project.godot"
        warning_msg = ""
        if not project_file.exists():
            warning_msg = "Warning: No 'project.godot' found. This might not be a Godot project."
        
        # Load using LazyProjectLoader
        success, msg = self._project_loader.load_from_folder(project_dir)
        
        if success:
            self.project_path = str(project_dir.absolute())
            self.project_stats = self._project_loader.get_stats()
            
            # Update brain with loader
            self.brain.project_loader = self._project_loader
            self.brain.project_stats = self.project_stats
            
            # NEW: Build dependency graph
            if self._dependency_graph:
                self._dependency_graph.load_project(str(project_dir))
            
            stats = self.project_stats
            message = f"✓ Project loaded: {stats['script_count']} scripts, {stats['scene_count']} scenes"
            if warning_msg:
                message += f"\n  ⚠ {warning_msg}"
            
            return True, message
        else:
            return False, f"Error loading project: {msg}"
    
    def process_query(self, query: str) -> Tuple[Any, List[str]]:
        """
        Process a user query through the appropriate pipeline.
        
        Args:
            query: User's input text
            
        Returns:
            Tuple of (result: Any, log: List[str])
        """
        self._ensure_initialized()
        return self.brain.process_query(query)
    
    def set_chat_mode(self, mode: str) -> bool:
        """
        Switch chat mode.
        
        Args:
            mode: One of 'coding', 'general', or 'mixed'
            
        Returns:
            True if mode was valid and set, False otherwise
        """
        self._ensure_initialized()
        valid_modes = ['coding', 'general', 'mixed']
        if mode.lower() in valid_modes:
            self.chat_mode = mode.lower()
            self.brain.set_chat_mode(mode.lower())
            return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current project status and engine state.
        
        Returns:
            Dictionary with project statistics and engine info
        """
        self._ensure_initialized()
        
        if not self.project_stats or self.project_stats.get('total_files', 0) == 0:
            return {
                'loaded': False,
                'message': 'No project loaded.'
            }
        
        cache_stats = self.brain.get_cache_stats() if self.brain else {}
        
        # NEW: Add dependency graph stats
        dep_graph_stats = {}
        if self._dependency_graph:
            dep_graph_stats = self._dependency_graph.get_stats()
        
        return {
            'loaded': True,
            'project_path': self.project_path,
            'script_count': self.project_stats.get('script_count', 0),
            'scene_count': self.project_stats.get('scene_count', 0),
            'resource_count': self.project_stats.get('resource_count', 0),
            'total_files': self.project_stats.get('total_files', 0),
            'loaded_files': self.project_stats.get('loaded_files', 0),
            'chat_mode': self.chat_mode,
            'cache_entries': cache_stats.get('entries', 0),
            'has_rag': self._rag_engine is not None,
            'has_static_analysis': self._static_analyzer is not None,
            'has_dependency_graph': self._dependency_graph is not None,
            'dependency_stats': dep_graph_stats,
        }
    
    def clear_history(self):
        """Clear chat history and cache."""
        self._ensure_initialized()
        self.history.clear()
        if hasattr(self.brain, 'cache') and hasattr(self.brain.cache, 'clear'):
            self.brain.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        self._ensure_initialized()
        return self.brain.get_cache_stats() if self.brain else {'entries': 0}
    
    def save_optimized_code(self, code: str, save_path: str) -> Tuple[bool, str]:
        """
        Save optimized code to a file.
        
        Args:
            code: The optimized GDScript code
            save_path: Path where to save the file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(code)
            self.last_optimized_code = code
            return True, f"✓ Code saved to: {save_path}"
        except Exception as e:
            return False, f"❌ Error saving file: {e}"
    
    def get_impact_analysis(self, file_path: str) -> Dict:
        """
        Analyze what would break if this file changes.
        
        Args:
            file_path: Path to the script file to analyze
            
        Returns:
            Dictionary with impact analysis results
        """
        self._ensure_initialized()
        
        if not self._dependency_graph:
            return {'error': 'Dependency graph not available'}
        
        # Convert to res:// path format if needed
        if not file_path.startswith('res://'):
            # Try to find in graph
            for known_file in self._dependency_graph.all_files:
                if known_file.endswith(file_path.split('/')[-1]):
                    file_path = known_file
                    break
        
        return self._dependency_graph.get_impact_analysis(file_path)
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies in the project.
        
        Returns:
            List of cycles found (each cycle is a list of file paths)
        """
        self._ensure_initialized()
        
        if not self._dependency_graph:
            return []
        
        return self._dependency_graph.get_circular_dependencies()


# Convenience function for simple imports
def create_engine() -> EtherEngine:
    """Factory function to create a new EtherEngine instance."""
    return EtherEngine()

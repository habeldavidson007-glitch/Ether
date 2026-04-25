"""
Project Scanner - Unified scanning utility for Godot projects.
Merges functionality from scanner.py and cascade_scanner.py.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass


@dataclass
class ScanResult:
    """Result of a project scan operation."""
    file_path: str
    issues: List[str]
    dependencies: List[str]
    impact_score: float = 0.0


@dataclass 
class CascadeReport:
    """Report from cascade scanning dependent files."""
    modified_file: str
    affected_files: List[str]
    potential_breakages: List[str]
    recommendations: List[str]


class ProjectScanner:
    """
    Unified project scanner with flat and dependency-aware scanning modes.
    
    Replaces separate scanner.py and cascade_scanner.py implementations.
    """
    
    def __init__(self, dependency_graph=None, static_analyzer=None, memory_core=None):
        self.dependency_graph = dependency_graph
        self.static_analyzer = static_analyzer
        self.memory_core = memory_core
        self._scan_cache: Dict[str, ScanResult] = {}
    
    def scan_flat(self, project_path: str) -> List[ScanResult]:
        """
        Perform a flat scan of all files in the project.
        
        Args:
            project_path: Path to the Godot project
            
        Returns:
            List of ScanResult objects for each file
        """
        results = []
        project_dir = Path(project_path)
        
        if not project_dir.exists():
            return results
        
        # Scan GDScript files
        for gd_file in project_dir.rglob("*.gd"):
            result = self._scan_file(str(gd_file))
            results.append(result)
        
        # Scan scene files
        for tscn_file in project_dir.rglob("*.tscn"):
            result = self._scan_scene(str(tscn_file))
            results.append(result)
        
        return results
    
    def scan_with_dependencies(self, file_path: str) -> CascadeReport:
        """
        Scan a file and analyze impact on dependent files.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            CascadeReport with impact analysis
        """
        affected_files = []
        potential_breakages = []
        recommendations = []
        
        # Get dependencies from graph
        if self.dependency_graph:
            dependents = self.dependency_graph.get_dependents(file_path)
            affected_files = list(dependents) if dependents else []
        
        # Analyze each affected file
        for dep_file in affected_files:
            if self.static_analyzer:
                try:
                    findings = self.static_analyzer.analyze_file(dep_file)
                    if findings:
                        potential_breakages.extend([
                            f"{dep_file}: {f.description}" for f in findings[:3]
                        ])
                except Exception:
                    pass
        
        # Generate recommendations
        if affected_files:
            recommendations.append(f"Review {len(affected_files)} dependent file(s)")
            recommendations.append("Run tests on affected modules")
            if self.memory_core:
                recommendations.append("Check memory for similar past changes")
        
        return CascadeReport(
            modified_file=file_path,
            affected_files=affected_files,
            potential_breakages=potential_breakages,
            recommendations=recommendations
        )
    
    def scan(self, file_path: str, changes_made: List[str]) -> Optional[CascadeReport]:
        """
        Perform a cascade scan after changes are made.
        
        Args:
            file_path: Path to the modified file
            changes_made: List of changes that were applied
            
        Returns:
            CascadeReport or None if unable to scan
        """
        if not Path(file_path).exists():
            return None
        
        report = self.scan_with_dependencies(file_path)
        
        # Record in memory if available
        if self.memory_core and changes_made:
            self.memory_core.record_fix(
                file_path, 
                changes_made, 
                success=True,
                context={'cascade_scan': True}
            )
        
        return report
    
    def _scan_file(self, file_path: str) -> ScanResult:
        """Scan a single GDScript file."""
        issues = []
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic checks
            if 'extends Node' not in content and 'extends Control' not in content:
                if 'extends' not in content:
                    issues.append("Missing 'extends' declaration")
            
            # Extract dependencies
            for line in content.split('\n'):
                if line.strip().startswith('const ') or line.strip().startswith('var '):
                    if '.gd' in line or '.tscn' in line:
                        dependencies.append(line.strip())
            
            # Run static analyzer if available
            if self.static_analyzer:
                try:
                    findings = self.static_analyzer.analyze_file(file_path)
                    if findings:
                        issues.extend([f.description for f in findings[:5]])
                except Exception:
                    pass
            
            impact_score = len(issues) * 0.1 + len(dependencies) * 0.05
            
        except Exception as e:
            issues.append(f"Scan error: {str(e)}")
            impact_score = 1.0
        
        return ScanResult(
            file_path=file_path,
            issues=issues,
            dependencies=dependencies,
            impact_score=min(impact_score, 1.0)
        )
    
    def _scan_scene(self, file_path: str) -> ScanResult:
        """Scan a TSCN scene file."""
        issues = []
        dependencies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for basic structure
            if '[gd_scene' not in content:
                issues.append("Invalid scene file format")
            
            # Extract resource dependencies
            for line in content.split('\n'):
                if 'resource =' in line or 'path =' in line:
                    dependencies.append(line.strip())
            
            impact_score = len(issues) * 0.2 + len(dependencies) * 0.03
            
        except Exception as e:
            issues.append(f"Scan error: {str(e)}")
            impact_score = 1.0
        
        return ScanResult(
            file_path=file_path,
            issues=issues,
            dependencies=dependencies,
            impact_score=min(impact_score, 1.0)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            'cached_scans': len(self._scan_cache),
            'has_dependency_graph': self.dependency_graph is not None,
            'has_static_analyzer': self.static_analyzer is not None,
            'has_memory_core': self.memory_core is not None
        }


# Legacy compatibility functions
def build_project_map(project_path: str) -> Dict[str, Any]:
    """Legacy compatibility function for build_project_map."""
    scanner = ProjectScanner()
    results = scanner.scan_flat(project_path)
    return {r.file_path: {'issues': r.issues, 'dependencies': r.dependencies} for r in results}


def extract_zip(zip_path: str, dest_path: str) -> bool:
    """Legacy compatibility function for extract_zip."""
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_path)
        return True
    except Exception:
        return False


def select_context(files: List[str], max_tokens: int = 4000) -> List[str]:
    """Legacy compatibility function for select_context."""
    # Simple selection: return files until max_tokens reached
    selected = []
    total_tokens = 0
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                tokens = len(file.read().split())
        except Exception:
            tokens = 100
        if total_tokens + tokens <= max_tokens:
            selected.append(f)
            total_tokens += tokens
        else:
            break
    return selected

"""
Cascade Scanner - Proactive Dependency Analysis & Breakage Prevention
Scans connected files to prevent ripple-effect bugs and suggest proactive optimizations.
"""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CascadeWarning:
    """Represents a potential breakage in a dependent file."""
    file_path: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    issue_type: str
    description: str
    suggested_fix: Optional[str] = None


@dataclass
class CascadeReport:
    """Complete report of cascade analysis."""
    target_file: str
    dependent_files: List[str]
    warnings: List[CascadeWarning]
    proactive_suggestions: List[str]
    safe_to_proceed: bool
    files_requiring_review: List[str]


class CascadeScanner:
    """Scans dependency chains to prevent ripple-effect bugs."""
    
    def __init__(self, dependency_graph, static_analyzer, memory_core=None):
        self.dependency_graph = dependency_graph
        self.static_analyzer = static_analyzer
        self.memory_core = memory_core
    
    def scan(self, target_file: str, changes_made: List[str]) -> CascadeReport:
        """
        Perform a complete cascade scan on a target file.
        
        Args:
            target_file: Path to the file being modified
            changes_made: List of changes applied (e.g., ["Removed signal X", "Changed function Y"])
        
        Returns:
            CascadeReport with warnings and suggestions
        """
        # Get all files that depend on the target
        dependents = self.dependency_graph.get_dependents(target_file)
        
        warnings = []
        suggestions = []
        files_needing_review = []
        
        # Analyze each dependent file
        for dependent in dependents:
            file_warnings = self._analyze_dependent(target_file, dependent, changes_made)
            warnings.extend(file_warnings)
            
            # Check for proactive optimization opportunities
            opt_suggestions = self._find_optimization_opportunities(dependent)
            suggestions.extend(opt_suggestions)
            
            # Flag files that need manual review
            if any(w.severity == "HIGH" for w in file_warnings):
                files_needing_review.append(dependent)
        
        # Determine if safe to proceed
        high_severity = any(w.severity == "HIGH" for w in warnings)
        safe_to_proceed = not high_severity
        
        return CascadeReport(
            target_file=target_file,
            dependent_files=dependents,
            warnings=warnings,
            proactive_suggestions=suggestions,
            safe_to_proceed=safe_to_proceed,
            files_requiring_review=files_needing_review
        )
    
    def _analyze_dependent(self, target_file: str, dependent_file: str, 
                          changes_made: List[str]) -> List[CascadeWarning]:
        """Analyze a single dependent file for potential breakages."""
        warnings = []
        
        try:
            if not os.path.exists(dependent_file):
                return warnings
            
            with open(dependent_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for signal usage
            for change in changes_made:
                if "signal" in change.lower():
                    # Extract signal name from change description
                    signal_name = self._extract_signal_name(change)
                    if signal_name and signal_name in content:
                        warnings.append(CascadeWarning(
                            file_path=dependent_file,
                            severity="HIGH",
                            issue_type="SIGNAL_BREAKAGE",
                            description=f"File uses signal '{signal_name}' which was modified/removed in {os.path.basename(target_file)}",
                            suggested_fix=f"Update signal connection in {os.path.basename(dependent_file)}"
                        ))
                
                if "function" in change.lower() or "method" in change.lower():
                    func_name = self._extract_function_name(change)
                    if func_name and func_name in content:
                        warnings.append(CascadeWarning(
                            file_path=dependent_file,
                            severity="MEDIUM",
                            issue_type="FUNCTION_SIGNATURE_CHANGE",
                            description=f"File may call function '{func_name}' which was modified in {os.path.basename(target_file)}",
                            suggested_fix=f"Verify function signature compatibility in {os.path.basename(dependent_file)}"
                        ))
                
                if "variable" in change.lower() or "export" in change.lower():
                    var_name = self._extract_variable_name(change)
                    if var_name and var_name in content:
                        warnings.append(CascadeWarning(
                            file_path=dependent_file,
                            severity="LOW",
                            issue_type="VARIABLE_REFERENCE",
                            description=f"File references variable '{var_name}' which was modified",
                            suggested_fix=f"Verify variable type/value compatibility"
                        ))
            
            # Check memory patterns for recurring issues
            if self.memory_core:
                recurring = self.memory_core.get_recurring_issues(dependent_file)
                for issue in recurring:
                    warnings.append(CascadeWarning(
                        file_path=dependent_file,
                        severity="MEDIUM",
                        issue_type="RECURRING_ISSUE",
                        description=f"File has history of: {issue}",
                        suggested_fix="Review this known problem area"
                    ))
        
        except Exception as e:
            warnings.append(CascadeWarning(
                file_path=dependent_file,
                severity="LOW",
                issue_type="SCAN_ERROR",
                description=f"Could not analyze file: {str(e)}"
            ))
        
        return warnings
    
    def _find_optimization_opportunities(self, file_path: str) -> List[str]:
        """Find proactive optimization suggestions for a file."""
        suggestions = []
        
        try:
            if not os.path.exists(file_path):
                return suggestions
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Run static analysis
            issues = self.static_analyzer.analyze_code(content, file_path)
            
            if issues:
                suggestions.append(f"{os.path.basename(file_path)}: {len(issues)} issue(s) detected - consider optimizing")
                
                # Specific suggestions based on issue types
                if any("loop" in i.lower() for i in issues):
                    suggestions.append(f"  → Optimize loops in {os.path.basename(file_path)}")
                if any("long" in i.lower() or "large" in i.lower() for i in issues):
                    suggestions.append(f"  → Consider splitting {os.path.basename(file_path)} into smaller modules")
        
        except Exception:
            pass
        
        return suggestions
    
    def _extract_signal_name(self, change: str) -> Optional[str]:
        """Extract signal name from change description."""
        # Simple extraction - look for quoted strings or common patterns
        import re
        matches = re.findall(r"'([^']+)'|\"([^\"]+)\"", change)
        for match in matches:
            signal = match[0] or match[1]
            if signal and not signal.isdigit():
                return signal
        return None
    
    def _extract_function_name(self, change: str) -> Optional[str]:
        """Extract function name from change description."""
        import re
        # Look for function_name( pattern
        match = re.search(r'(\w+)\(', change)
        if match:
            return match.group(1)
        return None
    
    def _extract_variable_name(self, change: str) -> Optional[str]:
        """Extract variable name from change description."""
        import re
        # Look for var_name pattern (simple heuristic)
        matches = re.findall(r"'([^']+)'|\"([^\"]+)\"", change)
        for match in matches:
            var = match[0] or match[1]
            if var and not var.isdigit() and not var.startswith("signal"):
                return var
        return None
    
    def get_cascade_summary(self, report: CascadeReport) -> str:
        """Generate a human-readable summary of cascade analysis."""
        lines = []
        lines.append(f"🔗 Cascade Scan: Analyzing {len(report.dependent_files)} dependent files...")
        
        if not report.warnings:
            lines.append("  ✅ No potential breakages detected")
        else:
            by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
            for w in report.warnings:
                by_severity[w.severity].append(w)
            
            for severity in ["HIGH", "MEDIUM", "LOW"]:
                if by_severity[severity]:
                    icon = "⚠️" if severity == "HIGH" else "⚡" if severity == "MEDIUM" else "ℹ️"
                    lines.append(f"  {icon} {severity}: {len(by_severity[severity])} issue(s)")
                    for w in by_severity[severity][:3]:  # Show top 3
                        lines.append(f"     • {os.path.basename(w.file_path)}: {w.description}")
        
        if report.proactive_suggestions:
            lines.append("  💡 Proactive optimizations:")
            for sug in report.proactive_suggestions[:3]:
                lines.append(f"     • {sug}")
        
        if report.files_requiring_review:
            lines.append(f"  🔍 Files requiring manual review: {len(report.files_requiring_review)}")
        
        return "\n".join(lines)


def create_cascade_scanner(dependency_graph, static_analyzer, memory_core=None) -> CascadeScanner:
    """Factory function to create a CascadeScanner instance."""
    return CascadeScanner(dependency_graph, static_analyzer, memory_core)

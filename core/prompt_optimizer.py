"""
Ether Prompt Optimizer - Small Model Optimization System
=========================================================
Optimized prompts specifically designed for small models (1.5B-3B parameters)
with structured templates, clear constraints, and reduced cognitive load.

Features:
- Role-based prompt templates
- Structured output enforcement
- Token-efficient phrasing
- GDScript-specific patterns
- Fallback simplification strategies
"""

from typing import Dict, List, Optional


class PromptOptimizer:
    """Generate optimized prompts for small language models."""
    
    # Model capability profiles
    MODEL_PROFILES = {
        'tiny': {'params': '<1B', 'context': 256, 'complexity': 'low'},
        'small': {'params': '1.5B-3B', 'context': 512, 'complexity': 'medium'},
        'medium': {'params': '7B-13B', 'context': 1024, 'complexity': 'high'}
    }
    
    def __init__(self, model_size: str = 'small'):
        """
        Initialize prompt optimizer.
        
        Args:
            model_size: Target model size ('tiny', 'small', 'medium')
        """
        self.model_size = model_size
        self.profile = self.MODEL_PROFILES.get(model_size, self.MODEL_PROFILES['small'])
    
    def optimize_for_task(self, task_type: str, context: str, query: str) -> str:
        """
        Generate optimized prompt for specific task.
        
        Args:
            task_type: Type of task ('optimize', 'debug', 'explain', 'generate')
            context: Code context
            query: User's request
            
        Returns:
            Optimized prompt string
        """
        if task_type == 'optimize':
            return self._build_optimize_prompt(context, query)
        elif task_type == 'debug':
            return self._build_debug_prompt(context, query)
        elif task_type == 'explain':
            return self._build_explain_prompt(context, query)
        elif task_type == 'generate':
            return self._build_generate_prompt(context, query)
        else:
            return self._build_general_prompt(context, query)
    
    def _build_optimize_prompt(self, context: str, query: str) -> str:
        """Build optimized prompt for code optimization tasks."""
        
        # Extract specific focus from query
        focus_keywords = self._extract_keywords(query)
        
        prompt = f"""You are a GDScript optimization expert. Improve this code focusing on: {', '.join(focus_keywords[:3])}

RULES:
1. Keep changes minimal and specific
2. Maintain exact same functionality
3. Output ONLY the improved function/code section
4. Use GDScript 4.x best practices

CODE TO OPTIMIZE:
```gdscript
{context[:500]}  # Limit context for small models
```

IMPROVED CODE (only the changed part):
```gdscript
"""
        return prompt
    
    def _build_debug_prompt(self, context: str, query: str) -> str:
        """Build optimized prompt for debugging tasks."""
        
        prompt = f"""You are a GDScript debugger. Find and fix the issue described.

ISSUE: {query[:100]}

CODE:
```gdscript
{context[:500]}
```

FIX (output only the corrected lines):
```gdscript
"""
        return prompt
    
    def _build_explain_prompt(self, context: str, query: str) -> str:
        """Build optimized prompt for explanation tasks."""
        
        prompt = f"""Explain this GDScript code in simple terms.

CODE:
```gdscript
{context[:400]}
```

EXPLANATION (2-3 sentences max):
"""
        return prompt
    
    def _build_generate_prompt(self, context: str, query: str) -> str:
        """Build optimized prompt for code generation tasks."""
        
        prompt = f"""Create GDScript code for: {query[:80]}

REQUIREMENTS:
- GDScript 4.x syntax
- Follow Godot best practices
- Include type hints

CODE:
```gdscript
"""
        return prompt
    
    def _build_general_prompt(self, context: str, query: str) -> str:
        """Build general purpose optimized prompt."""
        
        prompt = f"""Task: {query[:100]}

Context:
```gdscript
{context[:400]}
```

Response:
"""
        return prompt
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Common GDScript optimization keywords
        important_terms = [
            'performance', 'optimize', 'fast', 'efficient', 'memory',
            'clean', 'readable', 'maintain', 'refactor', 'simplify',
            'delta', 'frame', 'signal', 'node', 'scene'
        ]
        
        text_lower = text.lower()
        found = [term for term in important_terms if term in text_lower]
        
        # If no important terms found, use first few words
        if not found:
            found = text.split()[:5]
        
        return found
    
    def simplify_prompt(self, prompt: str, reduction_factor: float = 0.7) -> str:
        """
        Simplify prompt for very small models.
        
        Args:
            prompt: Original prompt
            reduction_factor: How much to reduce (0.0-1.0)
            
        Returns:
            Simplified prompt
        """
        lines = prompt.split('\n')
        
        # Remove verbose instructions
        simplified = []
        for line in lines:
            if len(line) < 50 or not line.strip().startswith('#'):
                simplified.append(line)
        
        # Truncate context sections
        result = '\n'.join(simplified[:int(len(simplified) * reduction_factor)])
        
        return result
    
    def add_structure_hints(self, prompt: str, output_format: str = 'code') -> str:
        """
        Add structural hints to guide model output.
        
        Args:
            prompt: Base prompt
            output_format: Expected output format ('code', 'explanation', 'list')
            
        Returns:
            Enhanced prompt with structure hints
        """
        hints = {
            'code': '\nFORMAT: Use ```gdscript ... ``` blocks\nCONSTRAINT: Only output code, no explanations',
            'explanation': '\nFORMAT: Use bullet points\nCONSTRAINT: Maximum 3 points',
            'list': '\nFORMAT: Numbered list\nCONSTRAINT: Maximum 5 items'
        }
        
        return prompt + hints.get(output_format, '')
    
    def create_few_shot_example(self, task: str, input_code: str, output_code: str) -> str:
        """
        Create few-shot learning example.
        
        Args:
            task: Task description
            input_code: Example input
            output_code: Expected output
            
        Returns:
            Formatted few-shot example
        """
        return f"""EXAMPLE {task.upper()}:

INPUT:
```gdscript
{input_code[:200]}
```

OUTPUT:
```gdscript
{output_code[:200]}
```

NOW DO THIS:
"""


class PromptTemplates:
    """Pre-optimized prompt templates for common tasks."""
    
    TEMPLATES = {
        'optimize_function': """Optimize this GDScript function for performance:

FUNCTION:
{code}

IMPROVEMENTS TO APPLY:
- Remove redundant operations
- Use efficient data structures
- Minimize memory allocations

OPTIMIZED VERSION:
```gdscript
""",
        
        'fix_common_errors': """Fix these common GDScript errors:

CODE WITH ERRORS:
{code}

ERRORS TO FIX:
{errors}

CORRECTED CODE:
```gdscript
""",
        
        'explain_concept': """Explain this GDScript concept simply:

CONCEPT: {concept}

CODE EXAMPLE:
{code}

EXPLANATION (max 3 sentences):
""",
        
        'generate_boilerplate': """Generate GDScript boilerplate for: {purpose}

REQUIREMENTS:
- GDScript 4.x
- Type-safe
- Well-commented

CODE:
```gdscript
"""
    }
    
    @classmethod
    def get_template(cls, name: str, **kwargs) -> str:
        """
        Get template and fill in variables.
        
        Args:
            name: Template name
            **kwargs: Variables to substitute
            
        Returns:
            Filled template string
        """
        template = cls.TEMPLATES.get(name, "")
        if not template:
            return ""
        
        # Simple string substitution
        result = template
        for key, value in kwargs.items():
            result = result.replace('{' + key + '}', str(value)[:500])  # Limit substitutions
        
        return result


def get_optimized_prompt(task: str, context: str, query: str, model_size: str = 'small') -> str:
    """
    Convenience function to get optimized prompt.
    
    Args:
        task: Task type
        context: Code context
        query: User query
        model_size: Target model size
        
    Returns:
        Optimized prompt
    """
    optimizer = PromptOptimizer(model_size)
    return optimizer.optimize_for_task(task, context, query)

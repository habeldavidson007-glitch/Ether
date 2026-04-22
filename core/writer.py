"""
Ether Writer - Transform Raw LLM Output into Polished Responses
================================================================
Purpose: Format and enhance LLM responses with professional templates.

Features:
- 6 response templates (explanation, tutorial, debug_report, comparison, casual_chat, code_review)
- Auto-generation of bullet points and examples
- Conversational enhancement
- Format flexibility (narrative, descriptive, bullets, tables)

Usage:
    writer = get_writer()
    response = writer.format_response(raw_llm_output, format_type="explanation", title="Memory Management")
"""

import re
from typing import Dict, List, Optional


class ResponseTemplates:
    """Pre-built response templates for different scenarios."""
    
    TEMPLATES = {
        "explanation": """# {title}

## Overview
{content}

## Key Points
{bullet_points}

## Example
{example}

## Summary
{summary}""",

        "tutorial": """# {title}

## What You'll Learn
{overview}

## Step-by-Step Guide

### Step 1: {step1_title}
{step1_content}

### Step 2: {step2_title}
{step2_content}

### Step 3: {step3_title}
{step3_content}

## ⚠️ Common Pitfalls
{warnings}

## ✅ Best Practices
{best_practices}""",

        "debug_report": """# Debug Report: {title}

## Problem Summary
{problem}

## Root Cause Analysis
{analysis}

## Issues Found
{issues}

## Recommended Fixes
{fixes}

## Prevention Tips
{prevention}""",

        "comparison": """# Comparison: {title}

## Overview
{overview}

## Side-by-Side Comparison

| Feature | Option A | Option B |
|---------|----------|----------|
{comparison_table}

## When to Use Each
{recommendations}

## Conclusion
{conclusion}""",

        "casual_chat": """{greeting}

{content}

{follow_up}""",

        "code_review": """# Code Review: {title}

## Overall Assessment
{assessment}

## Strengths ✅
{strengths}

## Areas for Improvement ⚠️
{improvements}

## Specific Suggestions
{suggestions}

## Refactored Example
{example}"""
    }
    
    @classmethod
    def get_template(cls, template_name: str) -> str:
        """Get a template by name."""
        return cls.TEMPLATES.get(template_name, "{content}")


class Writer:
    """
    Response formatting and enhancement engine.
    
    Transforms raw LLM output into polished, structured responses.
    """
    
    def __init__(self):
        self.templates = ResponseTemplates()
    
    def _extract_bullet_points(self, content: str, max_points: int = 5) -> List[str]:
        """Extract or generate bullet points from content."""
        # Try to find existing bullet points
        bullet_pattern = r'^(?:[-*•]|\d+\.)\s+(.+)$'
        bullets = re.findall(bullet_pattern, content, re.MULTILINE)
        
        if bullets:
            return bullets[:max_points]
        
        # Generate bullets from sentences
        sentences = re.split(r'[.!?]\s+', content)
        meaningful = [s.strip() for s in sentences if len(s.strip()) > 20 and not s.startswith('#')]
        
        return meaningful[:max_points]
    
    def _generate_summary(self, content: str, max_length: int = 100) -> str:
        """Generate a brief summary from content."""
        # Take first sentence or two
        sentences = re.split(r'[.!?]\s+', content)
        summary = sentences[0] if sentences else content[:max_length]
        
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def _format_as_table(self, items_a: List[str], items_b: List[str], 
                         headers: List[str] = None) -> str:
        """Format two lists as a comparison table."""
        if not headers:
            headers = ["Feature", "Option A", "Option B"]
        
        lines = []
        max_len = max(len(items_a), len(items_b))
        
        for i in range(max_len):
            a = items_a[i] if i < len(items_a) else "N/A"
            b = items_b[i] if i < len(items_b) else "N/A"
            lines.append(f"| {i+1}. {headers[0]} | {a} | {b} |")
        
        return "\n".join(lines)
    
    def format_response(self, content: str, format_type: str = "explanation",
                       title: str = "", context: str = "") -> str:
        """
        Format raw content using a specific template.
        
        Args:
            content: Raw LLM output
            format_type: Template type (explanation, tutorial, debug_report, etc.)
            title: Title for the response
            context: Additional context from Librarian
        
        Returns:
            Formatted response string
        """
        template = self.templates.get_template(format_type)
        
        # Extract components from content
        bullet_points = self._extract_bullet_points(content)
        summary = self._generate_summary(content)
        
        # Build formatted response based on template type
        if format_type == "explanation":
            bullets_formatted = "\n".join([f"• {bp}" for bp in bullet_points])
            example = content[-300:] if len(content) > 300 else content
            
            response = template.format(
                title=title or "Explanation",
                content=content[:800],
                bullet_points=bullets_formatted,
                example=example,
                summary=summary
            )
        
        elif format_type == "tutorial":
            # Split content into steps (naive approach)
            paragraphs = content.split('\n\n')
            
            response = template.format(
                title=title or "Tutorial",
                overview=paragraphs[0] if paragraphs else content[:200],
                step1_title="Getting Started",
                step1_content=paragraphs[1] if len(paragraphs) > 1 else "Begin by setting up your environment.",
                step2_title="Implementation",
                step2_content=paragraphs[2] if len(paragraphs) > 2 else "Implement the core functionality.",
                step3_title="Testing",
                step3_content=paragraphs[3] if len(paragraphs) > 3 else "Test your implementation thoroughly.",
                warnings="• Check for common errors\n• Validate inputs",
                best_practices="• Keep code modular\n• Document your work"
            )
        
        elif format_type == "debug_report":
            issues = self._extract_bullet_points(content, max_points=3)
            issues_formatted = "\n".join([f"❌ {issue}" for issue in issues])
            
            response = template.format(
                title=title or "Debug Analysis",
                problem=content[:300],
                analysis="Based on the code analysis...",
                issues=issues_formatted,
                fixes="• Apply the suggested corrections\n• Test after each fix",
                prevention="• Use static analysis tools\n• Follow coding standards"
            )
        
        elif format_type == "comparison":
            # Naive comparison extraction
            response = template.format(
                title=title or "Comparison",
                overview=content[:400],
                comparison_table="| Performance | Good | Better |\n| Ease of Use | Easy | Easier |",
                recommendations="Use Option A for simplicity, Option B for advanced features.",
                conclusion=summary
            )
        
        elif format_type == "code_review":
            strengths = ["Clear structure", "Good naming conventions"]
            improvements = self._extract_bullet_points(content, max_points=3)
            
            response = template.format(
                title=title or "Code Review",
                assessment="The code shows good fundamentals with room for optimization.",
                strengths="\n".join([f"✅ {s}" for s in strengths]),
                improvements="\n".join([f"⚠️ {imp}" for imp in improvements]),
                suggestions="• Consider refactoring for better performance\n• Add error handling",
                example=content[-400:] if len(content) > 400 else content
            )
        
        else:
            # Default: just return content with optional title
            response = f"# {title}\n\n{content}" if title else content
        
        # Add context footnote if provided
        if context:
            response += f"\n\n---\n*Context sourced from knowledge base*"
        
        return response
    
    def enhance_chat_response(self, content: str, context: str = "") -> str:
        """
        Enhance a chat response with conversational elements.
        
        Args:
            content: Raw LLM response
            context: Optional context from Librarian
        
        Returns:
            Enhanced conversational response
        """
        # Add greeting if missing
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon"]
        has_greeting = any(g in content.lower()[:50] for g in greetings)
        
        if not has_greeting:
            greeting_options = [
                "Great question!",
                "Thanks for asking!",
                "Here's what I found:",
                "Let me help you with that:"
            ]
            import random
            greeting = random.choice(greeting_options)
            content = f"{greeting}\n\n{content}"
        
        # Add follow-up suggestion
        follow_ups = [
            "\n\nWould you like me to elaborate on any part?",
            "\n\nLet me know if you need more details!",
            "\n\nFeel free to ask if anything is unclear!",
            "\n\nHappy to help further if needed!"
        ]
        import random
        content += random.choice(follow_ups)
        
        # Add context reference
        if context:
            content += f"\n\n*(Information sourced from relevant documentation)*"
        
        return content
    
    def create_comparison_table(self, topic: str, option_a: str, option_b: str,
                               criteria: List[str]) -> str:
        """
        Create a formatted comparison table.
        
        Args:
            topic: Topic being compared
            option_a: First option name
            option_b: Second option name
            criteria: List of comparison criteria
        
        Returns:
            Markdown-formatted comparison table
        """
        header = f"# {topic}: {option_a} vs {option_b}\n\n"
        
        table_header = f"| Criterion | {option_a} | {option_b} |\n|-----------|{'-' * len(option_a)}|{'-' * len(option_b)}|"
        
        rows = []
        for criterion in criteria:
            rows.append(f"| {criterion} | TBD | TBD |")
        
        return header + table_header + "\n" + "\n".join(rows)


# Singleton instance
_writer_instance: Optional[Writer] = None


def get_writer() -> Writer:
    """
    Get or create Writer singleton instance.
    
    Returns:
        Writer instance
    """
    global _writer_instance
    
    if _writer_instance is None:
        _writer_instance = Writer()
    
    return _writer_instance


# CLI interface for testing
if __name__ == "__main__":
    print("=" * 60)
    print("Ether Writer - Test Interface")
    print("=" * 60)
    
    writer = get_writer()
    
    # Test different templates
    test_cases = [
        {
            "type": "explanation",
            "content": "Memory management in C++ involves manual allocation and deallocation. Use new/delete or smart pointers. Key concepts include RAII, ownership semantics, and avoiding dangling pointers.",
            "title": "C++ Memory Management"
        },
        {
            "type": "tutorial",
            "content": "First, install Godot. Then create a new project. Add a Node2D. Write a script. Run the scene.",
            "title": "Getting Started with Godot"
        },
        {
            "type": "casual_chat",
            "content": "Singletons provide a single point of access but can make testing difficult. Consider dependency injection instead.",
            "title": ""
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['type']}")
        print('='*60)
        
        result = writer.format_response(
            test['content'],
            format_type=test['type'],
            title=test['title']
        )
        
        print(result[:500] + "..." if len(result) > 500 else result)
    
    # Test chat enhancement
    print("\n" + "="*60)
    print("Chat Enhancement Test")
    print("="*60)
    
    chat = writer.enhance_chat_response(
        "Fix the null reference by checking before access",
        context="From cpp_basics.md"
    )
    print(chat)
    
    print("\n✅ Writer ready for integration!")

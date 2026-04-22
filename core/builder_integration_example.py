"""
Ether Brain Expansion - Integration Example
============================================
This file demonstrates how to integrate Librarian and Writer into builder.py

Copy the integration patterns from this file into your core/builder.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.librarian import get_librarian
from core.writer import get_writer


# ============================================================================
# INTEGRATION EXAMPLE 1: Enhanced Chat Mode with Context Retrieval
# ============================================================================

def example_enhanced_chat(user_query: str, current_mode: str = "mixed"):
    """
    Example: How to enhance chat responses with knowledge base context.
    
    This would be integrated into builder.py's process_query method.
    """
    # Initialize components (use singletons)
    librarian = get_librarian()
    writer = get_writer()
    
    # STEP 1: Retrieve relevant context BEFORE sending to LLM
    context = librarian.retrieve(user_query, mode=current_mode, top_k=3)
    
    # STEP 2: Build enhanced prompt with context
    if context:
        prompt = f"""You are Ether AI Assistant. Use this context to answer:

{context}

User Question: {user_query}

Provide a clear, helpful response."""
    else:
        prompt = user_query
    
    # STEP 3: Send to LLM (replace with your actual LLM call)
    # llm_response = query_llm(prompt)  # Your existing LLM function
    llm_response = "This is a simulated LLM response about: " + user_query
    
    # STEP 4: Enhance response with Writer
    final_response = writer.enhance_chat_response(llm_response, context)
    
    return final_response


# ============================================================================
# INTEGRATION EXAMPLE 2: Code Optimization with Formatted Output
# ============================================================================

def example_code_optimization(file_path: str, user_query: str):
    """
    Example: How to use Librarian/Writer for code optimization tasks.
    
    This would be integrated into builder.py's handle_optimize method.
    """
    librarian = get_librarian()
    writer = get_writer()
    
    # Extract programming language from query or file extension
    if ".gd" in file_path or "godot" in user_query.lower():
        mode = "coding"
        # Get Godot-specific context
        context = librarian.retrieve("godot best practices performance", mode=mode)
    elif ".cpp" in file_path or "c++" in user_query.lower():
        context = librarian.retrieve("c++ memory management best practices", mode=mode)
    else:
        context = librarian.retrieve(user_query, mode="coding")
    
    # Your existing optimization logic here...
    # optimized_code = optimize_code(file_path, user_query)
    optimized_code = "# Optimized code would go here"
    
    # Format the response professionally
    response = writer.format_response(
        f"Optimized code:\n{optimized_code}",
        format_type="code_review",
        title=f"Code Optimization: {file_path}",
        context=context
    )
    
    return response


# ============================================================================
# INTEGRATION EXAMPLE 3: Tutorial Generation
# ============================================================================

def example_tutorial_generation(topic: str):
    """
    Example: Generate structured tutorials using knowledge base.
    """
    librarian = get_librarian()
    writer = get_writer()
    
    # Gather comprehensive context
    context = librarian.retrieve(topic, mode="coding", top_k=5, max_chars=4000)
    
    # Build tutorial prompt
    prompt = f"""Using this context, create a step-by-step tutorial:

{context}

Topic: {topic}

Include:
1. Clear prerequisites
2. Step-by-step instructions
3. Code examples
4. Common pitfalls
5. Best practices"""
    
    # Get raw content from LLM
    # raw_content = query_llm(prompt)
    raw_content = "Tutorial content would be generated here..."
    
    # Format as professional tutorial
    tutorial = writer.format_response(
        raw_content,
        format_type="tutorial",
        title=f"Complete Guide: {topic}",
        context=context
    )
    
    return tutorial


# ============================================================================
# INTEGRATION EXAMPLE 4: Comparison Queries
# ============================================================================

def example_comparison(topic_a: str, topic_b: str):
    """
    Example: Handle comparison queries like "Godot vs Unity".
    """
    librarian = get_librarian()
    writer = get_writer()
    
    # Get context for both topics
    context_a = librarian.retrieve(topic_a, mode="coding")
    context_b = librarian.retrieve(topic_b, mode="coding")
    
    combined_context = f"{context_a}\n\n---\n\n{context_b}"
    
    # Build comparison prompt
    prompt = f"""Compare these two technologies:

{combined_context}

Compare: {topic_a} vs {topic_b}

Consider:
- Performance
- Ease of use
- Learning curve
- Community support
- Best use cases"""
    
    # Get comparison from LLM
    # comparison_content = query_llm(prompt)
    comparison_content = "Comparison analysis would go here..."
    
    # Format as comparison report
    report = writer.format_response(
        comparison_content,
        format_type="comparison",
        title=f"{topic_a} vs {topic_b}",
        context=combined_context
    )
    
    return report


# ============================================================================
# INTEGRATION EXAMPLE 5: Debug Analysis with Context
# ============================================================================

def example_debug_analysis(error_message: str, code_snippet: str):
    """
    Example: Enhanced debugging with knowledge base context.
    """
    librarian = get_librarian()
    writer = get_writer()
    
    # Extract keywords from error
    keywords = error_message.split()[:5]
    context = librarian.retrieve(" ".join(keywords), mode="coding")
    
    # Build debug prompt
    prompt = f"""Analyze this error with the help of this context:

Context:
{context}

Error: {error_message}

Code:
{code_snippet}

Provide:
1. Root cause analysis
2. Specific fixes
3. Prevention tips"""
    
    # Get analysis from LLM
    # analysis = query_llm(prompt)
    analysis = "Debug analysis would be generated here..."
    
    # Format as debug report
    report = writer.format_response(
        analysis,
        format_type="debug_report",
        title="Bug Analysis Report",
        context=context
    )
    
    return report


# ============================================================================
# ACTUAL INTEGRATION: Where to modify builder.py
# ============================================================================

"""
TO INTEGRATE INTO builder.py:

1. Add imports at the top of builder.py:
   ```python
   from .librarian import get_librarian
   from .writer import get_writer
   ```

2. In EtherBrain.__init__(), initialize the components:
   ```python
   def __init__(self):
       # ... existing init code ...
       self.librarian = get_librarian()
       self.writer = get_writer()
   ```

3. In process_query(), add context retrieval before LLM calls:
   ```python
   # Around line 1760-1780, after getting project context:
   
   # Add knowledge base context
   if self.librarian:
       kb_context = self.librarian.retrieve(query, mode=self.chat_mode, top_k=2)
       if kb_context:
           context = kb_context + "\\n\\n" + context
   ```

4. After LLM response, enhance with Writer:
   ```python
   # Around line 1900+, after getting LLM response:
   
   if self.writer and fast_intent not in ['greeting', 'status']:
       text = self.writer.enhance_chat_response(text, context)
   ```

5. For handle_optimize(), add formatting:
   ```python
   # In handle_optimize(), after generating fixed code:
   
   if self.writer:
       summary = self.writer.format_response(
           explanation,
           format_type="debug_report",
           title="Optimization Report"
       )
   ```
"""


# ============================================================================
# TEST THE INTEGRATION
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Ether Brain Expansion - Integration Test")
    print("=" * 70)
    
    # Test 1: Enhanced Chat
    print("\n[Test 1] Enhanced Chat Mode")
    print("-" * 70)
    result = example_enhanced_chat("How do I fix memory leaks in C++?")
    print(result[:500] + "...")
    
    # Test 2: Code Optimization
    print("\n[Test 2] Code Optimization")
    print("-" * 70)
    result = example_code_optimization("player.gd", "optimize movement code")
    print(result[:500] + "...")
    
    # Test 3: Tutorial Generation
    print("\n[Test 3] Tutorial Generation")
    print("-" * 70)
    result = example_tutorial_generation("singleton pattern in Godot")
    print(result[:500] + "...")
    
    # Test 4: Comparison
    print("\n[Test 4] Comparison Query")
    print("-" * 70)
    result = example_comparison("Godot", "Unity")
    print(result[:500] + "...")
    
    # Test 5: Debug Analysis
    print("\n[Test 5] Debug Analysis")
    print("-" * 70)
    result = example_debug_analysis(
        "NullReferenceException",
        "var player = get_node('Player')\nplayer.move()"
    )
    print(result[:500] + "...")
    
    print("\n" + "=" * 70)
    print("✅ All integration examples executed successfully!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Copy integration patterns to core/builder.py")
    print("2. Run: python courier/fetcher.py --force (to populate KB)")
    print("3. Test with real queries in Ether CLI")

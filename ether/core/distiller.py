"""
ether/core/distiller.py
The Distiller: Cleans raw web data into "Pure Knowledge" before compression.
Strips HTML, ads, navigation, and fluff to extract only facts, code, and logic.
"""

import re
from html.parser import HTMLParser
from typing import List, Dict, Any

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, d):
        self.text.append(d)
    
    def get_data(self):
        return ''.join(self.text)

def strip_html(html: str) -> str:
    """Remove all HTML tags safely."""
    s = MLStripper()
    try:
        s.feed(html)
        return s.get_data()
    except Exception:
        # Fallback regex if parser fails
        return re.sub(r'<[^>]+>', '', html)

def remove_boilerplate(text: str) -> str:
    """Remove common boilerplate patterns (ads, footers, navs)."""
    # Remove URLs that look like tracking or ads
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Remove social media share buttons text patterns
    patterns = [
        r'(Share on|Tweet this|Subscribe|Sign up for our newsletter)',
        r'(Copyright © \d{4}|All rights reserved)',
        r'(Privacy Policy|Terms of Service|Cookie Policy)',
        r'(Related Articles|You might also like|Read more)',
        r'(Leave a comment|Reply|Post Comment)',
        r'(Advertisement|Advert)',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text

def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace/newlines into single spaces."""
    text = re.sub(r'\n\s*\n', '\n', text)  # Double newlines to single
    text = re.sub(r'[ \t]+', ' ', text)    # Multiple spaces to single
    return text.strip()

def extract_code_blocks(text: str) -> List[str]:
    """Extract code blocks (markdown style or indented) for special handling."""
    # Markdown code blocks
    blocks = re.findall(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
    # Indented code blocks (4 spaces)
    blocks += re.findall(r'^(    .*)$', text, re.MULTILINE)
    return blocks

def distill(raw_content: str, source_type: str = "html") -> Dict[str, Any]:
    """
    Main entry point: Raw Content -> Pure Knowledge.
    
    Returns:
        dict: {
            "title": str,
            "content": str (cleaned),
            "code_snippets": List[str],
            "summary_hint": str (first 200 chars),
            "density_score": float (0.0-1.0)
        }
    """
    if not raw_content:
        return {"title": "", "content": "", "code_snippets": [], "summary_hint": "", "density_score": 0.0}

    # 1. Strip HTML if needed
    if source_type == "html":
        text = strip_html(raw_content)
    else:
        text = raw_content

    # 2. Extract code BEFORE removing boilerplate (sometimes code looks like boilerplate)
    code_snippets = extract_code_blocks(text)
    
    # Remove code from main text temporarily to avoid cleaning it as noise
    for code in code_snippets:
        text = text.replace(code, "[CODE_BLOCK_PLACEHOLDER]")

    # 3. Remove Boilerplate
    text = remove_boilerplate(text)

    # 4. Restore Code
    for i, code in enumerate(code_snippets):
        text = text.replace("[CODE_BLOCK_PLACEHOLDER]", code, 1)

    # 5. Normalize Whitespace
    text = normalize_whitespace(text)

    # 6. Calculate Density Score (Ratio of alphanumeric/content chars to total)
    # Higher score = more information, less whitespace/punctuation
    if len(text) > 0:
        content_chars = sum(1 for c in text if c.isalnum() or c in '.!?')
        density_score = content_chars / len(text)
    else:
        density_score = 0.0

    # Filter out very low density sections (likely remaining noise)
    lines = text.split('\n')
    high_quality_lines = [
        line for line in lines 
        if len(line) > 10 and (sum(1 for c in line if c.isalnum()) / max(len(line), 1)) > 0.3
    ]
    final_content = '\n'.join(high_quality_lines)

    return {
        "title": "Distilled Content", # Could be enhanced with title extraction
        "content": final_content,
        "code_snippets": code_snippets,
        "summary_hint": final_content[:200] + "..." if len(final_content) > 200 else final_content,
        "density_score": round(density_score, 2)
    }

if __name__ == "__main__":
    # Test case
    sample_html = """
    <html>
    <body>
        <h1>How to Make a Brownie</h1>
        <p>Mix flour and sugar.</p>
        <div class="ad">Buy our cookies!</div>
        <pre><code>def bake(): print("oven")</code></pre>
        <footer>Copyright 2024. Share on Twitter.</footer>
    </body>
    </html>
    """
    result = distill(sample_html)
    print(f"Density: {result['density_score']}")
    print(f"Content:\n{result['content']}")
    print(f"Code: {result['code_snippets']}")

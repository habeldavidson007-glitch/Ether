"""
ether/core/distiller.py
The Distiller: Cleans raw web data into "Pure Knowledge" before compression.
Strips HTML, ads, navigation, and fluff to extract only facts, code, and logic.
Reduces raw text size by ~40% before Zstd processing.
"""

import re
import html
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup, NavigableString
import logging

logger = logging.getLogger(__name__)


class Distiller:
    """
    Extracts pure knowledge from raw web content.
    Removes noise, preserves signal.
    """
    
    # Patterns to remove (noise)
    NOISE_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # JavaScript
        r'<style[^>]*>.*?</style>',    # CSS
        r'<nav[^>]*>.*?</nav>',        # Navigation
        r'<header[^>]*>.*?</header>',  # Headers
        r'<footer[^>]*>.*?</footer>',  # Footers
        r'<aside[^>]*>.*?</aside>',    # Sidebars
        r'<!--.*?-->',                  # Comments
        r'<ad[^>]*>.*?</ad>',          # Ads
        r'class=["\'].*?(ad|banner|promo).*?["\']',  # Ad classes
        r'id=["\'].*?(ad|banner|promo).*?["\']',     # Ad IDs
    ]
    
    # Common noise words/phrases to remove from text
    NOISE_WORDS = [
        'click here', 'subscribe', 'newsletter', 'advertisement',
        'related articles', 'read more', 'share this', 'follow us',
        'copyright', 'all rights reserved', 'privacy policy',
        'terms of service', 'cookie policy', 'accept cookies',
        'sign up', 'log in', 'register', 'download app',
        'sponsored', 'promoted', 'advertising', 'buy now',
    ]

    def __init__(self, min_paragraph_length: int = 20, max_paragraphs: int = 50):
        """
        Initialize the Distiller.
        
        Args:
            min_paragraph_length: Minimum characters for a paragraph to be kept
            max_paragraphs: Maximum paragraphs to extract (prevents bloating)
        """
        self.min_paragraph_length = min_paragraph_length
        self.max_paragraphs = max_paragraphs
        
    def distill(self, raw_content: str, source_type: str = "web") -> str:
        """
        Main entry point: Convert raw HTML/text to pure knowledge.
        
        Args:
            raw_content: Raw HTML or text from web fetcher
            source_type: Type of source (web, rss, wiki, etc.)
            
        Returns:
            Cleaned, distilled knowledge text
        """
        if not raw_content or len(raw_content.strip()) < 10:
            return ""
            
        try:
            # Step 1: Parse HTML
            soup = self._parse_html(raw_content)
            
            # Step 2: Remove noise elements
            soup = self._remove_noise(soup)
            
            # Step 3: Extract signal elements
            text_blocks = self._extract_signal(soup, source_type)
            
            # Step 4: Clean and filter text
            cleaned = self._clean_text(text_blocks)
            
            # Step 5: Deduplicate and limit
            final = self._finalize(cleaned)
            
            logger.info(f"Distilled {len(raw_content)} chars → {len(final)} chars ({len(final)/max(len(raw_content),1)*100:.1f}% retained)")
            return final
            
        except Exception as e:
            logger.error(f"Distillation failed: {e}")
            # Fallback: basic text extraction
            return self._fallback_extract(raw_content)
    
    def _parse_html(self, content: str) -> BeautifulSoup:
        """Parse HTML content."""
        try:
            return BeautifulSoup(content, 'html.parser')
        except Exception:
            return BeautifulSoup("<p>" + content + "</p>", 'html.parser')
    
    def _remove_noise(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Remove noise elements from soup."""
        # Remove by tag
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove by class/id patterns
        for pattern in self.NOISE_PATTERNS:
            try:
                for element in soup.find_all(re.compile(pattern, re.IGNORECASE)):
                    element.decompose()
            except Exception:
                pass
        
        # Remove elements with noise-related classes/ids
        noise_keywords = ['ad', 'banner', 'promo', 'sponsor', 'cookie', 'newsletter']
        for element in soup.find_all(class_=True):
            classes = ' '.join(element.get('class', []))
            if any(keyword in classes.lower() for keyword in noise_keywords):
                element.decompose()
                
        for element in soup.find_all(id=True):
            elem_id = element.get('id', '')
            if any(keyword in elem_id.lower() for keyword in noise_keywords):
                element.decompose()
        
        return soup
    
    def _extract_signal(self, soup: BeautifulSoup, source_type: str) -> List[str]:
        """Extract meaningful text blocks."""
        text_blocks = []
        
        # Priority elements based on source type
        if source_type in ['wiki', 'documentation']:
            priority_tags = ['h1', 'h2', 'h3', 'p', 'code', 'pre', 'li']
        elif source_type in ['news', 'rss']:
            priority_tags = ['article', 'p', 'h2', 'h3', 'blockquote']
        else:
            priority_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'li', 'code', 'pre', 'blockquote']
        
        for tag_name in priority_tags:
            for element in soup.find_all(tag_name):
                text = element.get_text(separator=' ', strip=True)
                if len(text) >= self.min_paragraph_length:
                    text_blocks.append(text)
        
        # If no structured content found, get all text
        if not text_blocks:
            body = soup.find('body') or soup
            text = body.get_text(separator=' ', strip=True)
            if text:
                text_blocks.append(text)
        
        return text_blocks
    
    def _clean_text(self, text_blocks: List[str]) -> List[str]:
        """Clean individual text blocks."""
        cleaned = []
        
        for block in text_blocks:
            # Unescape HTML entities
            text = html.unescape(block)
            
            # Remove noise words/phrases
            for noise in self.NOISE_WORDS:
                text = re.sub(r'\b' + re.escape(noise) + r'\b', '', text, flags=re.IGNORECASE)
            
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Remove excessive punctuation
            text = re.sub(r'[^\w\s.,!?;:\-\'\"()]+', ' ', text)
            
            # Remove URLs (keep for reference but clean)
            text = re.sub(r'http[s]?://\S+', '[LINK]', text)
            
            if len(text) >= self.min_paragraph_length:
                cleaned.append(text)
        
        return cleaned
    
    def _finalize(self, text_blocks: List[str]) -> str:
        """Deduplicate, limit, and join text blocks."""
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for block in text_blocks:
            block_hash = hash(block)
            if block_hash not in seen:
                seen.add(block_hash)
                unique.append(block)
        
        # Limit to max paragraphs
        limited = unique[:self.max_paragraphs]
        
        # Join with newlines
        return '\n\n'.join(limited)
    
    def _fallback_extract(self, content: str) -> str:
        """Fallback: basic text extraction when parsing fails."""
        # Remove HTML tags with regex
        text = re.sub(r'<[^>]+>', ' ', content)
        # Unescape
        text = html.unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove noise words
        for noise in self.NOISE_WORDS:
            text = re.sub(r'\b' + re.escape(noise) + r'\b', '', text, flags=re.IGNORECASE)
        return text[:10000]  # Limit fallback output
    
    def distill_batch(self, contents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Distill multiple contents.
        
        Args:
            contents: List of dicts with 'content' and 'source_type' keys
            
        Returns:
            List of dicts with distilled content stats
        """
        results = []
        for item in contents:
            distilled = self.distill(
                item.get('content', ''),
                item.get('source_type', 'web')
            )
            if distilled:
                results.append({
                    'original_length': len(item.get('content', '')),
                    'distilled_length': len(distilled),
                    'compression_ratio': len(distilled) / max(len(item.get('content', '')), 1),
                    'content': distilled,
                    'source_type': item.get('source_type', 'web'),
                    'title': item.get('title', 'Unknown')
                })
        return results


# Legacy function compatibility
def strip_html(html: str) -> str:
    """Remove all HTML tags safely (legacy compatibility)."""
    distiller = Distiller()
    return distiller._fallback_extract(html)

def remove_boilerplate(text: str) -> str:
    """Remove common boilerplate patterns (legacy compatibility)."""
    distiller = Distiller()
    return distiller._clean_text([text])[0] if text else ""

def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace/newlines into single spaces (legacy)."""
    return re.sub(r'\s+', ' ', text).strip()

def extract_code_blocks(text: str) -> List[str]:
    """Extract code blocks (legacy compatibility)."""
    blocks = re.findall(r'```(?:\w+)?\n(.*?)```', text, re.DOTALL)
    blocks += re.findall(r'^(    .*)$', text, re.MULTILINE)
    return blocks

def distill(raw_content: str, source_type: str = "html") -> Dict[str, Any]:
    """
    Legacy distill function for backward compatibility.
    Returns dict format for old code.
    """
    distiller = Distiller()
    content = distiller.distill(raw_content, source_type)
    
    # Extract code snippets
    code_snippets = extract_code_blocks(content)
    
    # Calculate density score
    if len(content) > 0:
        content_chars = sum(1 for c in content if c.isalnum() or c in '.!?')
        density_score = content_chars / len(content)
    else:
        density_score = 0.0
    
    return {
        "title": "Distilled Content",
        "content": content,
        "code_snippets": code_snippets,
        "summary_hint": content[:200] + "..." if len(content) > 200 else content,
        "density_score": round(density_score, 2)
    }

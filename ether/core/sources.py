"""
Ether Omniscient Source Registry
Expanded from 7 Godot sources to 50+ General Knowledge sources.
Categorized for intelligent rotation during idle fetching.
"""

SOURCES = {
    # --- TECHNOLOGY & CODING (Core Strength) ---
    "tech_hackernews": {
        "url": "https://hnrss.org/frontpage",
        "category": "tech",
        "format": "rss",
        "priority": "high"
    },
    "tech_github_trending": {
        "url": "https://github-trends-atom.vercel.app/trending",
        "category": "tech",
        "format": "atom",
        "priority": "high"
    },
    "tech_stackoverflow_blog": {
        "url": "https://stackoverflow.blog/feed/",
        "category": "tech",
        "format": "rss",
        "priority": "medium"
    },
    "tech_arxiv_cs": {
        "url": "http://export.arxiv.org/rss/cs",
        "category": "science_ai",
        "format": "rss",
        "priority": "high"
    },
    "tech_pypl": {
        "url": "https://planetpython.org/rss20.xml",
        "category": "tech",
        "format": "rss",
        "priority": "medium"
    },

    # --- SCIENCE & DISCOVERY ---
    "sci_nature": {
        "url": "https://www.nature.com/nature.rss",
        "category": "science",
        "format": "rss",
        "priority": "medium"
    },
    "sci_science_daily": {
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "category": "science",
        "format": "rss",
        "priority": "low"
    },
    "sci_nasa_apod": {
        "url": "https://apod.nasa.gov/apod.rss",
        "category": "space",
        "format": "rss",
        "priority": "low"
    },
    "sci_pubmed": {
        "url": "https://pubmed.ncbi.nlm.nih.gov/rss/search/1icmCCqUos8eP6s4b9g7X/?limit=10",
        "category": "health",
        "format": "rss",
        "priority": "low"
    },

    # --- GENERAL NEWS & WORLD EVENTS ---
    "news_bbc": {
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "news",
        "format": "rss",
        "priority": "high"
    },
    "news_reuters": {
        "url": "https://www.reutersagency.com/feed/",
        "category": "news",
        "format": "rss",
        "priority": "high"
    },
    "news_aljazeera": {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "category": "news",
        "format": "rss",
        "priority": "medium"
    },

    # --- PHILOSOPHY & HISTORY ---
    "philosophy_stanford": {
        "url": "https://plato.stanford.edu/feeds/latest.xsl",
        "category": "philosophy",
        "format": "rss",
        "priority": "medium"
    },
    "history_smithsonian": {
        "url": "https://www.smithsonianmag.com/rss/history/",
        "category": "history",
        "format": "rss",
        "priority": "low"
    },

    # --- CREATIVE & ARTS ---
    "art_artsy": {
        "url": "https://www.artsy.net/articles/feed",
        "category": "art",
        "format": "rss",
        "priority": "low"
    },
    "lit_paris_review": {
        "url": "https://www.theparisreview.org/blog/feed/",
        "category": "literature",
        "format": "rss",
        "priority": "low"
    },

    # --- GODOT & GAME DEV (Legacy Strength) ---
    "godot_blog": {
        "url": "https://godotengine.org/rss.xml",
        "category": "godot",
        "format": "rss",
        "priority": "high"
    },
    "godot_kit_news": {
        "url": "https://godotengine.org/rss.xml", # Placeholder for kit news
        "category": "godot",
        "format": "rss",
        "priority": "medium"
    }
}

def get_sources_by_category(category: str):
    """Retrieve all sources for a specific category."""
    return {k: v for k, v in SOURCES.items() if v["category"] == category}

def get_high_priority_sources():
    """Retrieve sources marked as high priority for quick fetch cycles."""
    return {k: v for k, v in SOURCES.items() if v.get("priority") == "high"}

def get_all_sources():
    """Return full source dictionary."""
    return SOURCES

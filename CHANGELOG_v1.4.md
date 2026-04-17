# Ether v1.4 — Changelog

## Version 1.4 (Latest) — RAG-Enhanced Context & Semantic Search

### Major Enhancements

#### 1. RAG (Retrieval-Augmented Generation) Engine ✨
- **New Module**: `core/rag_engine.py`
- Implements lightweight TF-IDF based semantic search (no external dependencies)
- Chunked document indexing for precise context retrieval
- Relevance scoring with query-term matching and keyword boosting
- Smart context window building with deduplication

**Benefits:**
- Loads ONLY the most relevant code snippets for each query
- Dramatically improves analysis quality without increasing token count
- Maintains fast response times by avoiding full-file loading
- Better understanding of project structure and relationships

#### 2. Enhanced Context Building
- `LazyProjectLoader.build_lightweight_context()` now uses RAG-based retrieval
- Falls back to keyword matching if RAG fails (graceful degradation)
- Preserves file paths and line numbers in context for better AI responses

#### 3. Model Upgrade
- Upgraded from `qwen2.5:3b-instruct-q4_K_M` to `qwen2.5-coder:7b-instruct-q4_K_M`
- Better code analysis and reasoning capabilities
- Improved handling of complex Godot project structures
- Still quantized (Q4_K_M) for reasonable RAM usage (~6-8GB)

### Bug Fixes

#### Streamlit Deprecation Warning Fixed
- Replaced deprecated `st.components.v1.html` with `st.iframe`
- Eliminates warning messages in console
- Future-proof for Streamlit versions after 2026-06-01

### Updated Files

| File | Changes |
|------|---------|
| `app.py` | Updated to v1.4, fixed Streamlit deprecation, new model requirement |
| `core/builder.py` | Updated to v1.4, new model config, RAG documentation |
| `core/rag_engine.py` | **NEW** - Complete RAG implementation |
| `utils/project_loader.py` | Enhanced `build_lightweight_context()` with RAG support |

### Installation Requirements

```bash
# Update Ollama model
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# Install/update Python dependencies
pip install streamlit>=1.35 requests>=2.31
```

### Migration Notes

- Existing projects work without modification
- RAG engine automatically activates when analyzing project files
- Fallback to keyword matching ensures backward compatibility
- Model upgrade requires ~2GB additional RAM but provides significantly better analysis

### Performance Characteristics

- **Greetings/Status**: <2 seconds (unchanged, fast path via regex)
- **Simple Queries**: <2 seconds (unchanged, cached responses)
- **Complex Analysis**: 5-15 seconds (improved quality with RAG context)
- **Code Generation**: 10-30 seconds (better results with 7B model)

---

## Version 1.3 — Intent-Aware Routing & Lazy Loading

### Optimizations Implemented
1. Intent-aware routing with regex-based fast path
2. Lazy loading of project files on-demand
3. LRU cache with TTL for repeated queries

### Performance
- Greetings respond in <2 seconds
- Cached queries return instantly
- Reduced RAM usage through lazy loading

---

## Previous Versions

See `changelog.md` for earlier version history.

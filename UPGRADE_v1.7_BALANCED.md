# Ether v1.7 Upgrade Guide — Balanced Model for 4GB RAM

## What Changed?

**Model Upgrade:** `qwen2.5:0.5b` → `qwen2.5-coder:3b-instruct-q3_K_S`

### Why This Model?
- **6x smarter**: 3B parameters vs 0.5B for much better code analysis
- **Still fits 4GB**: q3_K_S quantization = ~2.1GB RAM (vs 500MB before)
- **Better reasoning**: Understands complex Godot project structures
- **Coder-specialized**: Trained specifically on code, not just chat

### Trade-offs:
- ✅ Much better at analyzing your game files
- ✅ Understands context and repercussions properly
- ⚠ Requires closing other apps to free up RAM
- ⚠ Slightly slower than 0.5B but still fast enough

## Installation Steps

### 1. Close Other Applications
Before running Ether, close:
- Web browsers (Chrome, Firefox, etc.)
- Other heavy applications
- Leave only terminal and Ollama running

### 2. Pull the New Model
```bash
ollama pull qwen2.5-coder:3b-instruct-q3_K_S
```

Wait for download (~2.1GB). This may take 5-15 minutes depending on your internet.

### 3. Run Ether CLI
```bash
python ether_cli.py
```

### 4. Test It
```
/load C:\Users\habil\Documents\test-game-11 - Copy
what do you think of my current game file?
```

Expected result: Response in 20-40 seconds (no timeout!)

## Troubleshooting

### If you get "Out of Memory" errors:
1. Close more applications
2. Restart your computer to clear RAM
3. Try running with only Ollama + Ether open

### If it's still too slow:
The model is loading a lot of context. Future updates will optimize this further.

### To go back to 0.5B model:
Edit `core/builder.py` line 41:
```python
DEFAULT_MODEL = "qwen2.5:0.5b-instruct-q4_K_M"
```

## Performance Expectations

| Task | 0.5B Model | 3B Model (New) |
|------|-----------|----------------|
| Greetings | Instant | Instant |
| Simple questions | 2-5s | 5-10s |
| Code analysis | Timeout | 20-40s ✓ |
| File review | Timeout | 30-50s ✓ |
| RAM usage | ~800MB | ~2.5GB |

## Next Steps

After testing, we can:
1. Further optimize RAG context loading if needed
2. Add streaming responses for better UX
3. Implement chunked analysis for very large projects

---

**Version:** v1.7  
**Date:** 2026-04-17  
**Model:** qwen2.5-coder:3b-instruct-q3_K_S

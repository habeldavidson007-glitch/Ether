# Ether v1.6 - Ultra-Lightweight Upgrade Guide

## What Changed?

We've **downgraded** from `qwen2.5-coder:1.5b` to `qwen2.5:0.5b` to fit your 4GB RAM system perfectly.

### Why This Fix Works:

| Model | RAM Usage | Speed | Context Limit | Your System |
|-------|-----------|-------|---------------|-------------|
| qwen2.5-coder:1.5b | ~1.1GB | Slow | 384 tokens | ❌ Timeout issues |
| **qwen2.5:0.5b** | **~500MB** | **Fast** | **256 tokens** | ✅ Perfect fit |

### Optimizations Applied:

1. **Smaller Model**: 0.5B parameters instead of 1.5B (67% smaller)
2. **Reduced Context**: Max 1200 chars for analysis (was 2000)
3. **Increased Timeout**: 45s for analysis (was 30s) - gives model more time
4. **Lower Token Limits**: 256 tokens max for analysis (was 384)

## Installation Steps:

### Option 1: Use the Setup Script (Windows)
```bash
setup.bat
```

### Option 2: Manual Installation
```bash
# Step 1: Make sure Ollama is running
ollama serve

# Step 2: Pull the new lightweight model (in a new terminal)
ollama pull qwen2.5:0.5b-instruct-q4_K_M

# Step 3: Run Ether CLI
python ether_cli.py
```

## Expected Performance:

- **Greetings**: Instant (<1s) - still uses fast path
- **Simple Questions**: 2-5 seconds
- **Project Analysis**: 15-30 seconds (no more timeouts!)
- **RAM Usage**: ~500MB for model + ~300MB for Python = ~800MB total

## Trade-offs:

✅ **Pros:**
- No more timeout errors
- Fits comfortably in 4GB RAM
- Faster inference speed
- Leaves RAM for other apps

⚠️ **Cons:**
- Slightly less sophisticated reasoning than 1.5B
- Shorter context window (but RAG compensates for this)
- May give simpler explanations for complex topics

## Usage:

```bash
# Start Ollama (keep this terminal open)
ollama serve

# In another terminal, run Ether
cd C:\Users\habil\Downloads\ether_local\ether_local
python ether_cli.py

# Load your project
/load C:\Users\habil\Documents\test-game-11 - Copy

# Ask questions
what do you think of my current game file setup?
```

## Troubleshooting:

### "Model not found" error
```bash
ollama pull qwen2.5:0.5b-instruct-q4_K_M
```

### Still getting timeouts
1. Close other applications to free up RAM
2. Restart Ollama: close the terminal and run `ollama serve` again
3. Try shorter, more specific questions

### "Connection refused" error
Make sure Ollama is running:
```bash
ollama serve
```

## Next Steps:

1. Run `setup.bat` or manually pull the model
2. Test with simple questions first
3. Then try your project analysis question
4. Report back if it works! 🎮

---

**Note**: The 0.5B model is specifically chosen for your hardware constraints. It's the sweet spot between capability and performance for 4GB RAM systems.

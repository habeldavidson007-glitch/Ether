#!/bin/bash
# Ether local setup — run once

echo "=== Ether Local Setup ==="

# 1. Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "✓ Ollama found"
fi

# 2. Pull model (qwen2.5:3b = ~2GB, runs on 4GB RAM)
echo "Pulling qwen2.5:3b model (~2GB download)..."
ollama pull qwen2.5:3b

# 3. Install Python deps
pip install -r requirements.txt

echo ""
echo "=== Setup complete ==="
echo ""
echo "To run Ether:"
echo "  1. ollama serve          (keep running in background)"
echo "  2. streamlit run app.py  (in another terminal)"

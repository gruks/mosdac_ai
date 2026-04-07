#!/bin/bash
set -e

echo "=== Pulling Qwen2.5-Coder-1.5B model ==="

# Pull the base model
ollama pull qwen2.5-coder:1.5b

# Create custom model with optimizations
echo "Creating custom model with Modelfile..."
ollama create mosdac-coder -f inference/Modelfile

# Verify model exists
echo "Available models:"
ollama list

echo "=== Model ready ==="
echo "Test with: curl http://localhost:11434/v1/chat/completions -d '{\"model\":\"mosdac-coder\",\"messages\":[{\"role\":\"user\",\"content\":\"hello\"}]}'"
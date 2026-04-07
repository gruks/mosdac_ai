#!/bin/bash
set -e

echo "=== Phase 1: Core Inference (RTX 1650) Verification ==="
echo ""

# Check if Ollama is running
echo "[Check 1] Ollama Service"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags | grep -q "200"; then
    echo "  ✓ Ollama is running on port 11434"
else
    echo "  ✗ Ollama is not running"
    echo "  → Start with: ollama serve"
    exit 1
fi

# Check if model is available
echo ""
echo "[Check 2] Model Availability"
if curl -s http://localhost:11434/api/tags | grep -q "mosdac-coder"; then
    echo "  ✓ mosdac-coder model is available"
else
    echo "  ✗ mosdac-coder model not found"
    echo "  → Run: inference/scripts/pull-model.sh"
    exit 1
fi

# Check if FastAPI server is running
echo ""
echo "[Check 3] FastAPI Server"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q "200"; then
    echo "  ✓ FastAPI server is running on port 8000"
else
    echo "  ✗ FastAPI server is not running"
    echo "  → Start with: python api/main.py"
    exit 1
fi

# Run Python smoke tests
echo ""
echo "[Check 4] Running Smoke Tests"
python inference/scripts/test-inference.py --base-url http://localhost:8000 --api-key dev-key-123

echo ""
echo "=== Verification Complete ==="
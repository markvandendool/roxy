#!/bin/bash
ROXY_ROOT="${ROXY_ROOT:-$HOME/.roxy}"
# Warm up Ollama models for faster first response

echo '=== OLLAMA MODEL WARMUP ==='

# Warm up small model
echo 'Warming up llama3.2:1b...'
curl -s http://localhost:11434/api/generate -d '{"model":"llama3.2:1b","prompt":"hi","stream":false}' > /dev/null && echo '  ✅ llama3.2:1b ready'

# Warm up code model
echo 'Warming up qwen2.5-coder:14b...'
curl -s http://localhost:11434/api/generate -d '{"model":"qwen2.5-coder:14b","prompt":"hi","stream":false}' > /dev/null && echo '  ✅ qwen2.5-coder:14b ready'

echo ''
echo 'Models warmed up and ready for fast inference'
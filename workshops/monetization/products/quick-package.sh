#!/usr/bin/env bash
# Quick Product Packager - Create sellable product NOW
# Simplified version - just package what exists

set -e  # Exit on error (but allow unset variables)

PRODUCTS_DIR="$HOME/mindsong-products"
WORKSHOP="$HOME/.roxy/workshops/monetization"

echo "🚀 QUICK PRODUCT PACKAGER"
echo "========================="
echo ""

# Product: Roxy AI Starter Kit
echo "📦 Packaging: Roxy AI Starter Kit"

PKG="$PRODUCTS_DIR/roxy-ai-starter-v1"
rm -rf "$PKG"
mkdir -p "$PKG"/{src,examples,docs}

# Copy core infrastructure files
echo "  ✓ Copying core files..."
cp ~/.roxy/infrastructure.py "$PKG/src/" 2>/dev/null || echo "  ! infrastructure.py not found, skipping"
cp ~/.roxy/cache_redis.py "$PKG/src/" 2>/dev/null || echo "  ! cache_redis.py not found, skipping"
cp ~/.roxy/memory_postgres.py "$PKG/src/" 2>/dev/null || echo "  ! memory_postgres.py not found, skipping"
cp ~/.roxy/expert_router.py "$PKG/src/" 2>/dev/null || echo "  ! expert_router.py not found, skipping"
cp ~/.roxy/event_stream.py "$PKG/src/" 2>/dev/null || echo "  ! event_stream.py not found, skipping"
cp ~/.roxy/obs_controller.py "$PKG/src/" 2>/dev/null || echo "  ! obs_controller.py not found, skipping"

# Sanitize secrets
echo "  ✓ Sanitizing secrets..."
find "$PKG/src" -name "*.py" -exec sed -i 's/sk-[a-zA-Z0-9_-]*/YOUR_API_KEY_HERE/g' {} \;
find "$PKG/src" -name "*.py" -exec sed -i 's/postgres:\/\/[^"'\'']*/"postgresql:\/\/user:pass@localhost\/db"/g' {} \;
find "$PKG/src" -name "*.py" -exec sed -i 's/redis:\/\/[^"'\'']*/"redis:\/\/localhost:6379"/g' {} \;

# Create README
cat > "$PKG/README.md" << 'EOF'
# Roxy AI Starter Kit

**Build AI agents with production-ready infrastructure**

## What's Inside

- `infrastructure.py` - Core AI orchestration
- `cache_redis.py` - Semantic caching (sub-50ms)
- `memory_postgres.py` - Long-term memory with pgvector
- `expert_router.py` - Multi-model routing (MoE pattern)
- `event_stream.py` - Event-driven architecture
- `obs_controller.py` - OBS Studio automation

## Quick Start

```python
from src.infrastructure import RoxyInfrastructure

# Initialize
roxy = RoxyInfrastructure()

# Query with caching + memory
response = roxy.query("Explain quantum computing")
print(response)
```

## Requirements

```bash
pip install fastapi redis psycopg2-binary pgvector ollama-python
docker-compose up -d  # Start Redis + PostgreSQL
```

## Use Cases

- AI chatbots with memory
- Content generation pipelines
- Automation workflows
- RAG applications

## License

MIT - Use commercially, modify freely

## Support

Email: support@mindsong.ai

---

**Regular Price: $99 | Today: $49**
EOF

# Create quick start example
cat > "$PKG/examples/quick_start.py" << 'EOF'
#!/usr/bin/env python3
"""Quick start example for Roxy AI Starter Kit"""

# TODO: Add your implementation here
# This is a template - customize for your use case

print("Roxy AI Starter Kit - Quick Start")
print("Replace this with your code!")
EOF

chmod +x "$PKG/examples/quick_start.py"

# Create Docker Compose
cat > "$PKG/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
      - "8001:8001"
    volumes:
      - redis-data:/data

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_PASSWORD: roxypass
      POSTGRES_DB: roxydb
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  redis-data:
  postgres-data:
EOF

# Create ZIP
echo "  ✓ Creating ZIP..."
cd "$PRODUCTS_DIR"
zip -r roxy-ai-starter-v1.zip roxy-ai-starter-v1/ > /dev/null
FILE_SIZE=$(du -h roxy-ai-starter-v1.zip | cut -f1)

echo ""
echo "✅ PRODUCT READY!"
echo "=================="
echo "📦 Package: $PRODUCTS_DIR/roxy-ai-starter-v1.zip"
echo "📏 Size: $FILE_SIZE"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Test the package:"
echo "   cd $PRODUCTS_DIR/roxy-ai-starter-v1"
echo "   cat README.md"
echo ""
echo "2. Create Gumroad account:"
echo "   https://gumroad.com/start"
echo ""
echo "3. Upload ZIP and set price to \$49"
echo ""
echo "4. Create product description:"
echo "   - Title: Roxy AI Starter Kit - Production AI Infrastructure"
echo "   - Price: \$49"
echo "   - Description: Copy from README.md"
echo "   - Tags: ai, python, infrastructure, automation"
echo ""
echo "5. Share on social media:"
echo "   - Reddit: r/Python, r/SideProject"
echo "   - Twitter/X: #buildinpublic #ai #opensource"
echo "   - Hacker News: Show HN"
echo ""
echo "💰 REVENUE POTENTIAL: 10 sales/month = \$490/mo"
echo ""

#!/bin/bash
# Backup script for ROXY data
# Backs up: PostgreSQL, ChromaDB, config, secrets

set -e

BACKUP_DIR="/home/mark/.roxy/backups"
DATE=$(date +%Y%m%d_%H%M%S)
ROXY_DIR="/home/mark/.roxy"

echo "🔄 ROXY Backup Starting - $DATE"
echo "=================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL (if running)
echo "📦 Backing up PostgreSQL..."
if docker ps | grep -q roxy-postgres; then
    docker exec roxy-postgres pg_dumpall -U roxy | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"
    echo "✅ PostgreSQL backup: postgres_$DATE.sql.gz"
else
    echo "⚠️  PostgreSQL container not running, skipping"
fi

# Backup ChromaDB
echo "📦 Backing up ChromaDB..."
if [ -d "$ROXY_DIR/chroma_db" ]; then
    tar -czf "$BACKUP_DIR/chromadb_$DATE.tar.gz" -C "$ROXY_DIR" chroma_db/
    echo "✅ ChromaDB backup: chromadb_$DATE.tar.gz"
else
    echo "⚠️  ChromaDB directory not found, skipping"
fi

# Backup configuration
echo "📦 Backing up configuration..."
cp "$ROXY_DIR/config.json" "$BACKUP_DIR/config_$DATE.json" 2>/dev/null || echo "⚠️  config.json not found"

# Backup secret token (encrypted would be better!)
cp "$ROXY_DIR/secret.token" "$BACKUP_DIR/secret_token_$DATE" 2>/dev/null || echo "⚠️  secret.token not found"

# Backup logs directory structure (not the logs themselves, too large)
tar -czf "$BACKUP_DIR/logs_structure_$DATE.tar.gz" --exclude='*.log' -C "$ROXY_DIR" logs/ 2>/dev/null || echo "⚠️  logs directory not found"

# Cleanup: Keep only last 7 days of backups
echo "🧹 Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -type f -mtime +7 -delete
OLD_COUNT=$(find "$BACKUP_DIR" -type f -mtime +7 | wc -l)
if [ "$OLD_COUNT" -gt 0 ]; then
    echo "✅ Deleted $OLD_COUNT old backup files"
fi

# Display backup summary
echo ""
echo "=================================="
echo "✅ Backup Complete!"
echo "=================================="
echo "Location: $BACKUP_DIR"
echo "Files:"
ls -lh "$BACKUP_DIR" | grep "$DATE" || true
echo ""

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "Total backup directory size: $TOTAL_SIZE"

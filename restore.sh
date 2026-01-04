#!/bin/bash
# Restore script for ROXY data
# Usage: ./restore.sh YYYYMMDD_HHMMSS

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Backup timestamp required"
    echo "Usage: $0 <backup_timestamp>"
    echo ""
    echo "Available backups:"
    ls -1 /home/mark/.roxy/backups/*.tar.gz 2>/dev/null | xargs -n1 basename | sed 's/chromadb_//' | sed 's/.tar.gz//' | sort -u || echo "No backups found"
    exit 1
fi

BACKUP_DIR="/home/mark/.roxy/backups"
DATE=$1
ROXY_DIR="/home/mark/.roxy"

echo "🔄 ROXY Restore Starting - $DATE"
echo "=================================="

# Check if backups exist
if [ ! -f "$BACKUP_DIR/chromadb_$DATE.tar.gz" ]; then
    echo "❌ Error: Backup not found for $DATE"
    echo "Available backups:"
    ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | xargs -n1 basename | sed 's/chromadb_//' | sed 's/.tar.gz//' | sort -u
    exit 1
fi

# Confirm restoration
read -p "⚠️  This will overwrite current data. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Stop ROXY core
echo "🛑 Stopping ROXY core..."
systemctl --user stop roxy-core || true

# Restore PostgreSQL
if [ -f "$BACKUP_DIR/postgres_$DATE.sql.gz" ]; then
    echo "📦 Restoring PostgreSQL..."
    gunzip < "$BACKUP_DIR/postgres_$DATE.sql.gz" | docker exec -i roxy-postgres psql -U roxy
    echo "✅ PostgreSQL restored"
else
    echo "⚠️  PostgreSQL backup not found, skipping"
fi

# Restore ChromaDB
if [ -f "$BACKUP_DIR/chromadb_$DATE.tar.gz" ]; then
    echo "📦 Restoring ChromaDB..."
    # Backup current ChromaDB first
    if [ -d "$ROXY_DIR/chroma_db" ]; then
        mv "$ROXY_DIR/chroma_db" "$ROXY_DIR/chroma_db.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    tar -xzf "$BACKUP_DIR/chromadb_$DATE.tar.gz" -C "$ROXY_DIR"
    echo "✅ ChromaDB restored"
else
    echo "⚠️  ChromaDB backup not found, skipping"
fi

# Restore config
if [ -f "$BACKUP_DIR/config_$DATE.json" ]; then
    echo "📦 Restoring config..."
    cp "$BACKUP_DIR/config_$DATE.json" "$ROXY_DIR/config.json"
    echo "✅ Config restored"
fi

# Restore secret token
if [ -f "$BACKUP_DIR/secret_token_$DATE" ]; then
    echo "📦 Restoring secret token..."
    cp "$BACKUP_DIR/secret_token_$DATE" "$ROXY_DIR/secret.token"
    chmod 600 "$ROXY_DIR/secret.token"
    echo "✅ Secret token restored"
fi

# Start ROXY core
echo "🚀 Starting ROXY core..."
systemctl --user start roxy-core

echo ""
echo "=================================="
echo "✅ Restore Complete!"
echo "=================================="
echo "Restored from: $DATE"
echo "ROXY core status:"
systemctl --user status roxy-core --no-pager | head -5

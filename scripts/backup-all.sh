#!/bin/bash
# Backup all critical Roxy data to MinIO

BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/tmp/roxy-backup-$BACKUP_DATE"
MINIO_BUCKET="roxy-backups"

echo "=== ROXY BACKUP - $BACKUP_DATE ==="
mkdir -p "$BACKUP_DIR"

# Backup configurations
echo '[1/4] Backing up configurations...'
cp -r /opt/roxy/integrations/config "$BACKUP_DIR/" 2>/dev/null && echo '    ✅ Integration configs'
cp /opt/roxy/.env "$BACKUP_DIR/" 2>/dev/null && echo '    ✅ Environment file'

# Backup voice data
echo '[2/4] Backing up voice data...'
cp -r /opt/roxy/voice/wakeword/samples "$BACKUP_DIR/wakeword-samples" 2>/dev/null && echo '    ✅ Wake word samples'
cp -r /opt/roxy/voice/wakeword/models "$BACKUP_DIR/wakeword-models" 2>/dev/null && echo '    ✅ Wake word models'

# Backup scripts
echo '[3/4] Backing up scripts...'
cp -r /opt/roxy/scripts "$BACKUP_DIR/scripts" 2>/dev/null && echo '    ✅ Automation scripts'

# Create tarball
echo '[4/4] Creating archive...'
cd /tmp && tar -czf "roxy-backup-$BACKUP_DATE.tar.gz" "roxy-backup-$BACKUP_DATE"
ARCHIVE="/tmp/roxy-backup-$BACKUP_DATE.tar.gz"
SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "    ✅ Archive created: $SIZE"

# Upload to MinIO (if mc is configured)
if command -v mc &> /dev/null; then
    mc cp "$ARCHIVE" "local/$MINIO_BUCKET/" 2>/dev/null && echo "    ✅ Uploaded to MinIO" || echo "    ⚠️ MinIO upload skipped"
fi

# Cleanup
rm -rf "$BACKUP_DIR"
echo ''
echo "Backup complete: $ARCHIVE"

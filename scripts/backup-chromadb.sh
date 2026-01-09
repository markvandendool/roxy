#!/bin/bash
# ROXY/ROXY-1 ChromaDB Backup Script
# Part of: ROXY-100-METRIC-INFRASTRUCTURE-V1
# Purpose: Automated backup of ChromaDB vector database to MinIO S3
#
# Usage: ./backup-chromadb.sh
# Cron: 0 2 * * * ~/.roxy/scripts/backup-chromadb.sh >> ~/.roxy/logs/roxy-backup.log 2>&1

set -e

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CHROMADB_DATA="/var/lib/docker/volumes/compose_chromadb_data/_data"
BACKUP_DIR="/tmp/chromadb-backups"
BACKUP_FILE="chromadb_backup_${TIMESTAMP}.tar.gz"
MINIO_BUCKET="roxy/chromadb-backups"
RETENTION_DAYS=7

echo "========================================"
echo "ChromaDB Backup - ${TIMESTAMP}"
echo "========================================"

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Check if ChromaDB data exists
if [ ! -d "${CHROMADB_DATA}" ]; then
    echo "ERROR: ChromaDB data directory not found: ${CHROMADB_DATA}"
    exit 1
fi

# Create compressed backup
echo "Creating backup archive..."
tar -czf ${BACKUP_DIR}/${BACKUP_FILE} -C ${CHROMADB_DATA} .

# Get backup size
BACKUP_SIZE=$(du -h ${BACKUP_DIR}/${BACKUP_FILE} | cut -f1)
echo "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload to MinIO
echo "Uploading to MinIO..."
mc cp ${BACKUP_DIR}/${BACKUP_FILE} ${MINIO_BUCKET}/

# Verify upload
if mc ls ${MINIO_BUCKET}/${BACKUP_FILE} > /dev/null 2>&1; then
    echo "Upload successful!"
else
    echo "ERROR: Upload failed!"
    exit 1
fi

# Clean up local backup
rm -f ${BACKUP_DIR}/${BACKUP_FILE}

# Apply retention policy (keep last 7 days)
echo "Applying retention policy (${RETENTION_DAYS} days)..."
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y%m%d)

# List and remove old backups
mc ls ${MINIO_BUCKET}/ | while read -r line; do
    FILENAME=$(echo "$line" | awk '{print $NF}')
    if [[ $FILENAME =~ chromadb_backup_([0-9]{8}) ]]; then
        FILE_DATE=${BASH_REMATCH[1]}
        if [[ $FILE_DATE < $CUTOFF_DATE ]]; then
            echo "Removing old backup: ${FILENAME}"
            mc rm ${MINIO_BUCKET}/${FILENAME}
        fi
    fi
done

# Show current backups
echo ""
echo "Current backups in MinIO:"
mc ls ${MINIO_BUCKET}/

echo ""
echo "Backup complete!"
echo "========================================"

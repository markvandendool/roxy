# ROXY Disaster Recovery Guide

## Overview

This document outlines backup and restore procedures for ROXY infrastructure.

## Recovery Time Objectives (RTO)

- **ROXY Core**: < 5 minutes
- **PostgreSQL**: < 15 minutes
- **ChromaDB**: < 30 minutes
- **Full System**: < 1 hour

## Recovery Point Objectives (RPO)

- **Daily Backups**: 24 hours maximum data loss
- **Manual Backups**: On-demand before major changes

## Backup Components

### 1. PostgreSQL Database

**Backup**: Full database dump using `pg_dumpall`
**Location**: `/home/mark/.roxy/backups/postgres_YYYYMMDD_HHMMSS.sql.gz`
**Frequency**: Daily at 2:00 AM

### 2. ChromaDB Vector Store

**Backup**: Compressed tar archive of `chroma_db` directory
**Location**: `/home/mark/.roxy/backups/chromadb_YYYYMMDD_HHMMSS.tar.gz`
**Frequency**: Daily at 2:00 AM

### 3. Configuration Files

**Backup**: `config.json` and `secret.token`
**Location**: `/home/mark/.roxy/backups/config_YYYYMMDD_HHMMSS.json` and `secret_token_YYYYMMDD_HHMMSS`
**Frequency**: Daily at 2:00 AM

## Automated Backups

### Setup Cron Job

Add to crontab:
```bash
crontab -e
```

Add this line:
```
0 2 * * * /home/mark/.roxy/backup.sh >> /home/mark/.roxy/logs/backup.log 2>&1
```

This runs daily at 2:00 AM.

### Manual Backup

Run backup script manually:
```bash
/home/mark/.roxy/backup.sh
```

## Restore Procedures

### Full System Restore

1. **Stop ROXY Core**:
   ```bash
   systemctl --user stop roxy-core
   ```

2. **List Available Backups**:
   ```bash
   ls -lh /home/mark/.roxy/backups/
   ```

3. **Run Restore Script**:
   ```bash
   /home/mark/.roxy/restore.sh YYYYMMDD_HHMMSS
   ```

4. **Verify Restore**:
   ```bash
   systemctl --user status roxy-core
   /opt/roxy/scripts/health_check.sh
   ```

### Partial Restore

#### Restore PostgreSQL Only

```bash
gunzip < /home/mark/.roxy/backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i roxy-postgres psql -U roxy
```

#### Restore ChromaDB Only

```bash
# Backup current first
mv /home/mark/.roxy/chroma_db /home/mark/.roxy/chroma_db.backup.$(date +%Y%m%d_%H%M%S)

# Restore
tar -xzf /home/mark/.roxy/backups/chromadb_YYYYMMDD_HHMMSS.tar.gz -C /home/mark/.roxy
```

#### Restore Config Only

```bash
cp /home/mark/.roxy/backups/config_YYYYMMDD_HHMMSS.json /home/mark/.roxy/config.json
cp /home/mark/.roxy/backups/secret_token_YYYYMMDD_HHMMSS /home/mark/.roxy/secret.token
chmod 600 /home/mark/.roxy/secret.token
```

## Backup Retention

- **Retention Period**: 7 days
- **Automatic Cleanup**: Old backups (>7 days) are automatically deleted
- **Manual Cleanup**: `find /home/mark/.roxy/backups -type f -mtime +7 -delete`

## Backup Verification

### Verify Backup Integrity

```bash
# Check PostgreSQL backup
gunzip -t /home/mark/.roxy/backups/postgres_YYYYMMDD_HHMMSS.sql.gz

# Check ChromaDB backup
tar -tzf /home/mark/.roxy/backups/chromadb_YYYYMMDD_HHMMSS.tar.gz > /dev/null && echo "OK"
```

### Test Restore (Dry Run)

1. Create test environment
2. Run restore script
3. Verify all services start correctly
4. Test ROXY core functionality

## Disaster Recovery Scenarios

### Scenario 1: Complete System Failure

1. Restore from most recent backup
2. Verify all services are healthy
3. Test ROXY core functionality
4. Monitor for 24 hours

### Scenario 2: Database Corruption

1. Stop affected services
2. Restore PostgreSQL from backup
3. Restart services
4. Verify data integrity

### Scenario 3: ChromaDB Data Loss

1. Stop ROXY core
2. Restore ChromaDB from backup
3. Restart ROXY core
4. Verify RAG functionality

### Scenario 4: Configuration Loss

1. Restore config files from backup
2. Restart ROXY core
3. Verify configuration is correct

## Backup Monitoring

### Check Backup Status

```bash
# View backup log
tail -f /home/mark/.roxy/logs/backup.log

# List recent backups
ls -lht /home/mark/.roxy/backups/ | head -10
```

### Backup Failure Alerts

Monitor backup log for errors:
```bash
grep -i error /home/mark/.roxy/logs/backup.log
```

## Best Practices

1. **Test Restores Regularly**: Test restore procedures quarterly
2. **Multiple Backup Locations**: Consider off-site backups for critical data
3. **Encrypt Backups**: Use encryption for sensitive data (secrets, tokens)
4. **Document Changes**: Keep changelog of configuration changes
5. **Monitor Backup Size**: Ensure sufficient disk space for backups

## Emergency Contacts

- **System Administrator**: [Your contact]
- **Database Administrator**: [Your contact]
- **On-Call Engineer**: [Your contact]

## Related Documentation

- `docs/INFRASTRUCTURE.md`: Infrastructure overview
- `scripts/health_check.sh`: Health check script
- `backup.sh`: Backup script
- `restore.sh`: Restore script


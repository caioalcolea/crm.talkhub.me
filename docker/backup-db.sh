#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# TalkHub CRM — PostgreSQL Backup
# Creates a compressed pg_dump and optionally uploads to S3
#
# Usage:
#   ./docker/backup-db.sh              # Local backup only
#   ./docker/backup-db.sh --upload     # Backup + upload to S3
# ============================================================

CONTAINER_NAME="djangocrm_crm_db"
BACKUP_DIR="backups"
DB_NAME="crm_db"
DB_USER="postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/crm_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[backup]${NC} $*"; }
fail() { echo -e "${RED}[backup]${NC} $*"; exit 1; }

# Parse args
UPLOAD=false
for arg in "$@"; do
    case "$arg" in
        --upload) UPLOAD=true ;;
    esac
done

# Ensure backup dir exists
mkdir -p "$BACKUP_DIR"

# Find the running container
CONTAINER_ID=$(docker ps -q -f "name=${CONTAINER_NAME}" 2>/dev/null | head -1)
if [[ -z "$CONTAINER_ID" ]]; then
    # Try with swarm service naming
    CONTAINER_ID=$(docker ps -q -f "label=com.docker.swarm.service.name=${CONTAINER_NAME}" 2>/dev/null | head -1)
fi
[[ -n "$CONTAINER_ID" ]] || fail "PostgreSQL container not found"

# Run pg_dump
log "Starting backup of ${DB_NAME}..."
docker exec "$CONTAINER_ID" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE" \
    || fail "pg_dump failed"

FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${FILESIZE})"

# Cleanup old backups
DELETED=$(find "$BACKUP_DIR" -name "crm_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
    log "Cleaned up ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
fi

# Optional S3 upload
if $UPLOAD; then
    if command -v aws &>/dev/null; then
        S3_BUCKET="${CRM_S3_BUCKET:-talkhub-crm}"
        S3_ENDPOINT="${CRM_S3_ENDPOINT:-https://s3.talkhub.me}"
        log "Uploading to s3://${S3_BUCKET}/backups/..."
        aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/backups/" \
            --endpoint-url "$S3_ENDPOINT" \
            || fail "S3 upload failed"
        log "Upload complete"
    else
        log "Warning: AWS CLI not found, skipping S3 upload"
    fi
fi

log "Backup complete!"

#!/bin/bash
#
# PostgreSQL 备份脚本 - Phase Q8.1.1
#
# 用途：每日 02:00 通过 cron 执行 pg_dump 并上传到 MinIO
# 使用：
#   bash scripts/backup_pg.sh
#   或加入 crontab:
#   0 2 * * * /path/to/backup_pg.sh >> /var/log/claywords_backup.log 2>&1
#

set -euo pipefail

# ============== 配置 ==============
# 数据库配置
DB_HOST="${PG_HOST:-localhost}"
DB_PORT="${PG_PORT:-5432}"
DB_USER="${PG_USER:-claywords}"
DB_NAME="${PG_DB:-claywords}"
PGPASSWORD="${PG_PASSWORD:-claywords_secret}"
export PGPASSWORD

# MinIO 配置
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_BUCKET="${MINIO_BUCKET:-claywords}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-claywords}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-claywords_secret}"

# 备份配置
BACKUP_DIR="${BACKUP_DIR:-/tmp/claywords_backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"  # 本地保留天数
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pg_dump_${DB_NAME}_${TIMESTAMP}.dump"

# 告警配置
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"  # 飞书/钉钉 webhook URL

# ============== 函数 ==============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

send_alert() {
    local level="$1"
    local message="$2"

    log "[$level] $message"

    # 发送告警到 webhook（如果配置）
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"msg_type\": \"text\", \"content\": {\"text\": \"[ClayWords Backup] [$level] $message\"}}" \
            > /dev/null 2>&1 || true
    fi
}

cleanup_local_backups() {
    log "Cleaning up local backups older than ${RETENTION_DAYS} days..."
    find "$BACKUP_DIR" -name "pg_dump_*.dump" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
}

upload_to_minio() {
    local file="$1"
    local key="backups/pg/$(basename $file)"

    log "Uploading to MinIO: ${MINIO_BUCKET}/${key}"

    # 优先使用 mc (MinIO Client)，回退到 aws cli
    if command -v mc &> /dev/null; then
        mc alias set claywords_minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null
        mc cp "$file" "claywords_minio/${MINIO_BUCKET}/${key}"
    elif command -v aws &> /dev/null; then
        AWS_ACCESS_KEY_ID="$MINIO_ACCESS_KEY" \
        AWS_SECRET_ACCESS_KEY="$MINIO_SECRET_KEY" \
        aws s3 cp "$file" "s3://${MINIO_BUCKET}/${key}" \
            --endpoint-url "$MINIO_ENDPOINT" \
            --no-verify-ssl
    else
        log "WARNING: Neither 'mc' nor 'aws' CLI found, skipping upload"
        return 1
    fi

    log "Upload completed: ${key}"
}

# ============== 主流程 ==============
main() {
    log "=== ClayWords PostgreSQL Backup Started ==="
    log "Database: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    log "Backup file: ${BACKUP_FILE}"

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    # 执行 pg_dump
    log "Running pg_dump..."
    if ! pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -F c \
        -f "$BACKUP_FILE" \
        "$DB_NAME"; then
        send_alert "ERROR" "pg_dump failed for database ${DB_NAME}"
        exit 1
    fi

    # 检查文件大小
    local file_size=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
    local file_size_mb=$((file_size / 1024 / 1024))
    log "Backup file size: ${file_size_mb} MB"

    if [ "$file_size" -lt 1024 ]; then
        send_alert "ERROR" "Backup file is suspiciously small (${file_size} bytes)"
        exit 1
    fi

    # 上传到 MinIO
    if ! upload_to_minio "$BACKUP_FILE"; then
        send_alert "WARNING" "Failed to upload backup to MinIO, but local backup is preserved"
    fi

    # 清理旧备份
    cleanup_local_backups

    log "=== Backup Completed Successfully ==="
    send_alert "INFO" "Backup completed: ${BACKUP_FILE} (${file_size_mb} MB)"
}

# ============== 错误处理 ==============
trap 'send_alert "ERROR" "Backup script failed at line $LINENO"' ERR

main "$@"

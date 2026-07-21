#!/bin/bash
#
# Redis 备份脚本 - Phase Q8.1.4
#
# 用途：触发 Redis BGSAVE 并备份 RDB 文件
# 使用：
#   bash scripts/backup_redis.sh
#

set -euo pipefail

# ============== 配置 ==============
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# MinIO 配置
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_BUCKET="${MINIO_BUCKET:-claywords}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-claywords}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-claywords_secret}"

# 备份配置
BACKUP_DIR="${BACKUP_DIR:-/tmp/claywords_backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"  # Redis 保留 7 天
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RDB_BACKUP_FILE="${BACKUP_DIR}/redis_dump_${TIMESTAMP}.rdb"

# Docker 容器名（如果是 docker 部署）
REDIS_CONTAINER="${REDIS_CONTAINER:-claywords_redis}"

# ============== 函数 ==============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

trigger_bgsave() {
    log "Triggering Redis BGSAVE..."

    if command -v redis-cli &> /dev/null; then
        if [ -n "$REDIS_PASSWORD" ]; then
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" BGSAVE
        else
            redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE
        fi
    elif docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
        docker exec "$REDIS_CONTAINER" redis-cli BGSAVE
    else
        log "ERROR: Neither redis-cli nor docker container available"
        return 1
    fi

    # 等待 BGSAVE 完成
    sleep 5

    log "BGSAVE triggered"
}

copy_rdb_file() {
    log "Copying RDB file to ${RDB_BACKUP_FILE}..."

    if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
        docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "$RDB_BACKUP_FILE"
    elif [ -f /var/lib/redis/dump.rdb ]; then
        cp /var/lib/redis/dump.rdb "$RDB_BACKUP_FILE"
    else
        log "ERROR: Cannot find Redis RDB file"
        return 1
    fi

    log "RDB file copied"
}

upload_to_minio() {
    local file="$1"
    local key="backups/redis/$(basename $file)"

    log "Uploading to MinIO: ${MINIO_BUCKET}/${key}"

    if command -v mc &> /dev/null; then
        mc alias set claywords_minio "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null
        mc cp "$file" "claywords_minio/${MINIO_BUCKET}/${key}"
        log "Upload completed"
    else
        log "WARNING: 'mc' not found, skipping upload"
        return 1
    fi
}

# ============== 主流程 ==============
main() {
    log "=== Redis Backup Started ==="
    log "Redis: ${REDIS_HOST}:${REDIS_PORT}"

    mkdir -p "$BACKUP_DIR"

    trigger_bgsave || exit 1
    copy_rdb_file || exit 1

    local file_size=$(stat -c%s "$RDB_BACKUP_FILE" 2>/dev/null || stat -f%z "$RDB_BACKUP_FILE")
    log "RDB file size: $((file_size / 1024)) KB"

    upload_to_minio "$RDB_BACKUP_FILE" || log "Upload failed, but local backup preserved"

    # 清理旧备份
    find "$BACKUP_DIR" -name "redis_dump_*.rdb" -type f -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true

    log "=== Redis Backup Completed ==="
}

main "$@"

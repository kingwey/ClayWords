#!/bin/bash
#
# MinIO 异地镜像脚本 - Phase Q8.1.3
#
# 用途：将本地 MinIO 数据镜像到云端 OSS（异地备份）
# 使用：
#   bash scripts/mirror_minio.sh
#   或加入 crontab:
#   30 2 * * * /path/to/mirror_minio.sh >> /var/log/claywords_mirror.log 2>&1
#

set -euo pipefail

# ============== 配置 ==============
# 本地 MinIO
LOCAL_ENDPOINT="${LOCAL_MINIO_ENDPOINT:-http://localhost:9000}"
LOCAL_ACCESS_KEY="${LOCAL_MINIO_ACCESS_KEY:-claywords}"
LOCAL_SECRET_KEY="${LOCAL_MINIO_SECRET_KEY:-claywords_secret}"
LOCAL_BUCKET="${LOCAL_MINIO_BUCKET:-claywords}"

# 远程 OSS (阿里云/腾讯云/AWS S3)
REMOTE_ENDPOINT="${REMOTE_OSS_ENDPOINT:-}"
REMOTE_ACCESS_KEY="${REMOTE_OSS_ACCESS_KEY:-}"
REMOTE_SECRET_KEY="${REMOTE_OSS_SECRET_KEY:-}"
REMOTE_BUCKET="${REMOTE_OSS_BUCKET:-}"

# Mirror 配置
MIRROR_INTERVAL="${MIRROR_INTERVAL:-once}"  # once / continuous
DRY_RUN="${DRY_RUN:-false}"

# ============== 函数 ==============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_dependencies() {
    if ! command -v mc &> /dev/null; then
        log "ERROR: 'mc' (MinIO Client) is required but not installed"
        log "Install: https://docs.min.io/docs/minio-client-quickstart-guide"
        exit 1
    fi
}

setup_aliases() {
    log "Setting up MinIO aliases..."

    mc alias set local_claywords "$LOCAL_ENDPOINT" "$LOCAL_ACCESS_KEY" "$LOCAL_SECRET_KEY" 2>/dev/null

    if [ -n "$REMOTE_ENDPOINT" ] && [ -n "$REMOTE_ACCESS_KEY" ]; then
        mc alias set remote_oss "$REMOTE_ENDPOINT" "$REMOTE_ACCESS_KEY" "$REMOTE_SECRET_KEY" 2>/dev/null
        log "Remote OSS configured"
    else
        log "WARNING: Remote OSS not configured, skipping mirror"
        return 1
    fi
}

enable_versioning() {
    log "Enabling versioning on local bucket..."
    mc version enable "local_claywords/${LOCAL_BUCKET}" 2>/dev/null || \
        log "Versioning may already be enabled or not supported"
}

mirror_data() {
    local source="local_claywords/${LOCAL_BUCKET}"
    local target="remote_oss/${REMOTE_BUCKET}"

    log "Mirroring: ${source} -> ${target}"

    local opts="--overwrite --remove"
    if [ "$DRY_RUN" = "true" ]; then
        opts="${opts} --dry-run"
    fi

    if [ "$MIRROR_INTERVAL" = "continuous" ]; then
        # 持续监控并同步
        log "Starting continuous mirror..."
        mc mirror --watch $opts "$source" "$target"
    else
        # 单次同步
        mc mirror $opts "$source" "$target"
        log "Mirror completed"
    fi
}

verify_mirror() {
    log "Verifying mirror..."

    local local_count=$(mc ls --recursive "local_claywords/${LOCAL_BUCKET}" | wc -l)
    local remote_count=$(mc ls --recursive "remote_oss/${REMOTE_BUCKET}" | wc -l)

    log "Local files: ${local_count}"
    log "Remote files: ${remote_count}"

    if [ "$local_count" = "$remote_count" ]; then
        log "✓ Mirror verified: file counts match"
    else
        log "WARNING: File count mismatch (may be normal if mirror is in progress)"
    fi
}

# ============== 主流程 ==============
main() {
    log "=== MinIO Mirror Started ==="

    check_dependencies

    if ! setup_aliases; then
        log "Cannot setup aliases, exiting"
        exit 1
    fi

    enable_versioning
    mirror_data
    verify_mirror

    log "=== MinIO Mirror Completed ==="
}

main "$@"

#!/bin/bash
#
# PostgreSQL 恢复脚本 - Phase Q8.2.1
#
# 用途：从备份文件恢复 PostgreSQL 数据库
# 使用：
#   bash scripts/restore_pg.sh <backup_file>
#   bash scripts/restore_pg.sh /tmp/claywords_backups/pg_dump_claywords_20260621_020000.dump
#

set -euo pipefail

# ============== 配置 ==============
DB_HOST="${PG_HOST:-localhost}"
DB_PORT="${PG_PORT:-5432}"
DB_USER="${PG_USER:-claywords}"
DB_NAME="${PG_DB:-claywords_restore}"  # 默认恢复到不同的数据库名
PGPASSWORD="${PG_PASSWORD:-claywords_secret}"
export PGPASSWORD

BACKUP_FILE="${1:-}"

# ============== 函数 ==============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

usage() {
    cat <<EOF
Usage: $0 <backup_file>

Restores a PostgreSQL backup created by backup_pg.sh

Environment variables:
  PG_HOST       PostgreSQL host (default: localhost)
  PG_PORT       PostgreSQL port (default: 5432)
  PG_USER       PostgreSQL user (default: claywords)
  PG_DB         Target database name (default: claywords_restore)
  PG_PASSWORD   PostgreSQL password

Example:
  $0 /tmp/claywords_backups/pg_dump_claywords_20260621.dump
  PG_DB=claywords_test $0 /path/to/backup.dump

EOF
    exit 1
}

verify_backup_file() {
    if [ -z "$BACKUP_FILE" ]; then
        usage
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        log "ERROR: Backup file not found: $BACKUP_FILE"
        exit 1
    fi

    local file_size=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE")
    log "Backup file: $BACKUP_FILE"
    log "File size: $((file_size / 1024 / 1024)) MB"

    if [ "$file_size" -lt 1024 ]; then
        log "ERROR: Backup file is suspiciously small"
        exit 1
    fi
}

create_target_db() {
    log "Creating target database: $DB_NAME"

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres <<EOF || true
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME};
EOF
}

restore_database() {
    log "Restoring database from $BACKUP_FILE..."
    log "Target: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"

    pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-privileges \
        "$BACKUP_FILE"

    log "Restore completed"
}

verify_restoration() {
    log "Verifying restoration..."

    local table_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')

    log "Tables restored: $table_count"

    if [ "$table_count" -gt 0 ]; then
        log "✓ Restoration verified"

        # 显示主要表的行数
        log "Row counts:"
        for table in users studios orders sessions design_templates; do
            local count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
                "SELECT count(*) FROM ${table};" 2>/dev/null | tr -d ' ' || echo "N/A")
            log "  ${table}: ${count}"
        done
    else
        log "WARNING: No tables found after restoration"
    fi
}

# ============== 主流程 ==============
main() {
    log "=== PostgreSQL Restore Started ==="

    verify_backup_file

    # 警告
    if [ "$DB_NAME" != "claywords_restore" ] && [ "$DB_NAME" != "claywords_test" ]; then
        log "WARNING: You are about to restore to database '$DB_NAME'"
        log "This will DROP and RECREATE the target database!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log "Aborted"
            exit 0
        fi
    fi

    create_target_db
    restore_database
    verify_restoration

    log "=== Restore Completed Successfully ==="
    log "Database '$DB_NAME' is ready for use"
}

main "$@"

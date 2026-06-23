# 备份与恢复演练 Runbook

> Phase Q8.2.1: 月度恢复演练 runbook  
> 目标 RTO ≤ 30min, RPO ≤ 15min

---

## 1. 备份策略

### 备份频率

| 数据 | 频率 | 保留期 | 工具 |
|------|------|--------|------|
| PostgreSQL Full | 每日 02:00 | 30 天本地 + 90 天云端 | `backup_pg.sh` |
| PostgreSQL WAL | 每 15 分钟 | 7 天 | `archive_command` |
| Redis RDB | 每日 03:00 | 7 天 | `backup_redis.sh` |
| MinIO 数据 | 持续镜像 | 永久（OSS 异地） | `mirror_minio.sh` |

### 备份位置

```
本地: /tmp/claywords_backups/
本地 MinIO: claywords/backups/{pg,redis,wal}/
云端 OSS: oss-claywords/backups/  (异地备份)
```

---

## 2. 恢复演练流程

### 2.1 月度演练标准流程

每月第一个周日执行，目标：
- ✅ RTO（恢复时间目标）≤ 30 分钟
- ✅ RPO（恢复点目标）≤ 15 分钟
- ✅ 数据完整性 100%

### 2.2 演练步骤

#### Step 1: 准备 Staging 环境

```bash
# 启动 staging Docker 环境
cd infra
docker compose -f docker-compose.staging.yml up -d

# 等待服务启动
docker ps | grep claywords_staging
```

#### Step 2: 下载最新备份

```bash
# 从 MinIO 下载最新的备份
mc cp claywords_minio/claywords/backups/pg/pg_dump_claywords_$(date +%Y%m%d)*.dump \
   /tmp/restore_backup.dump

# 验证文件
ls -la /tmp/restore_backup.dump
file /tmp/restore_backup.dump  # 应该是 PostgreSQL custom dump 格式
```

#### Step 3: 恢复 PostgreSQL

```bash
# 设置 staging 数据库
export PG_HOST=staging-pg.claywords.local
export PG_USER=claywords
export PG_DB=claywords_restored
export PG_PASSWORD=staging_secret

# 执行恢复（计时开始）
START_TIME=$(date +%s)

bash scripts/restore_pg.sh /tmp/restore_backup.dump

END_TIME=$(date +%s)
RESTORE_TIME=$((END_TIME - START_TIME))
echo "Restore time: ${RESTORE_TIME} seconds"
```

#### Step 4: 恢复 Redis

```bash
# 复制 RDB 文件到 Redis 容器
docker cp /tmp/redis_dump.rdb claywords_staging_redis:/data/dump.rdb

# 重启 Redis 加载备份
docker restart claywords_staging_redis

# 验证数据
docker exec claywords_staging_redis redis-cli DBSIZE
```

#### Step 5: 验证数据完整性

```bash
# 检查关键表
psql -h staging-pg -U claywords -d claywords_restored <<EOF
-- 用户数
SELECT 'users', count(*) FROM users
UNION ALL
SELECT 'studios', count(*) FROM studios
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'tasks', count(*) FROM tasks
UNION ALL
SELECT 'uploads', count(*) FROM uploads;

-- 最新订单
SELECT order_id, user_id, status, total_price, created_at
FROM orders
ORDER BY created_at DESC LIMIT 5;

-- 最新任务
SELECT task_id, state, created_at
FROM tasks
ORDER BY created_at DESC LIMIT 5;
EOF
```

#### Step 6: 应用层冒烟测试

```bash
# 启动 staging 后端
docker compose -f docker-compose.staging.yml up -d backend

# 健康检查
curl http://staging.claywords.local/health
# 预期: {"status": "healthy"}

# 关键 API 测试
curl http://staging.claywords.local/api/v1/orders/statuses
curl http://staging.claywords.local/metrics
```

#### Step 7: 记录演练结果

```bash
# 创建演练记录
cat > /var/log/claywords/drill_$(date +%Y%m%d).log <<EOF
演练日期: $(date)
PG 恢复时间: ${RESTORE_TIME}s
Redis 恢复时间: XXs
数据完整性: ✓
应用启动: ✓
RTO 达标: $([ $RESTORE_TIME -le 1800 ] && echo "是" || echo "否")
EOF
```

---

## 3. 紧急恢复流程

### 3.1 数据库故障

**场景**: 主数据库数据损坏/丢失

```bash
# 1. 立即下线服务（防止脏写）
docker stop claywords_backend claywords_worker

# 2. 评估损坏程度
psql -U claywords -d claywords -c "SELECT pg_database_size('claywords');"

# 3. 创建恢复数据库
psql -U claywords -d postgres -c "CREATE DATABASE claywords_emergency;"

# 4. 恢复最新备份
LATEST_BACKUP=$(ls -t /tmp/claywords_backups/pg_dump_*.dump | head -1)
PG_DB=claywords_emergency bash scripts/restore_pg.sh "$LATEST_BACKUP"

# 5. 应用 WAL 增量（如果配置了 WAL 归档）
# pg_wal_replay 操作（需要 PITR 配置）

# 6. 切换数据库连接
# 修改 .env 或 ConfigMap
sed -i 's/claywords/claywords_emergency/g' /etc/claywords/.env

# 7. 重启服务
docker start claywords_backend claywords_worker

# 8. 验证服务
curl http://localhost:8000/health
```

### 3.2 Redis 数据丢失

**场景**: Redis AOF 文件损坏

```bash
# 1. 停止服务
docker stop claywords_backend claywords_worker claywords_redis

# 2. 备份当前 Redis 数据
docker cp claywords_redis:/data /tmp/redis_corrupt_backup

# 3. 删除损坏文件
docker exec claywords_redis rm -f /data/dump.rdb /data/appendonly.aof

# 4. 恢复最新 RDB
LATEST_RDB=$(ls -t /tmp/claywords_backups/redis_dump_*.rdb | head -1)
docker cp "$LATEST_RDB" claywords_redis:/data/dump.rdb

# 5. 重启 Redis
docker start claywords_redis

# 6. 验证
docker exec claywords_redis redis-cli DBSIZE
```

### 3.3 MinIO 数据丢失

**场景**: 本地 MinIO 数据丢失

```bash
# 从云端 OSS 恢复
mc mirror remote_oss/claywords-backup local_claywords/claywords \
    --overwrite

# 验证
mc ls --recursive local_claywords/claywords | wc -l
```

---

## 4. 验证清单

### 备份验证（每日）

- [ ] 备份文件存在且大小合理（> 1MB）
- [ ] 备份成功上传到 MinIO
- [ ] 异地镜像同步正常
- [ ] 没有备份失败告警

### 恢复演练（每月）

- [ ] PostgreSQL 恢复 RTO ≤ 30 分钟
- [ ] Redis 恢复 RTO ≤ 5 分钟
- [ ] 数据完整性 100%（关键表行数一致）
- [ ] 应用启动并通过健康检查
- [ ] 关键 API 测试通过
- [ ] RPO ≤ 15 分钟（数据丢失少于 15 分钟）

### 灾难恢复（季度）

- [ ] 完整数据中心切换演练
- [ ] DNS 切换流程
- [ ] 域名证书更新
- [ ] 监控告警系统恢复

---

## 5. 自动化检查

### 备份监控（每小时）

```bash
# 添加到 crontab:
# 0 * * * * /path/to/check_backup.sh

#!/bin/bash
# check_backup.sh
LAST_BACKUP=$(find /tmp/claywords_backups -name "pg_dump_*.dump" -mtime -1 | head -1)

if [ -z "$LAST_BACKUP" ]; then
    # 24 小时内没有备份 → 告警
    curl -X POST $ALERT_WEBHOOK -d '{"text": "ClayWords 备份失败：24h 内无新备份"}'
fi
```

### CI 自动化恢复测试（每月）

参见 `.github/workflows/restore-test.yml`（待创建）

---

## 6. 应急联系人

| 角色 | 联系方式 | 职责 |
|------|---------|------|
| OPS 主负责人 | xxx@claywords.com | 数据库恢复 |
| OPS 备用 | yyy@claywords.com | 二线支持 |
| 安全团队 | sec@claywords.com | 数据泄漏调查 |
| CTO | cto@claywords.com | 重大故障决策 |

---

## 7. 改进记录

| 日期 | 演练结果 | 改进项 | 负责人 |
|------|---------|--------|--------|
| 2026-06-21 | 初次配置 | 完成基础脚本 | OPS |
| - | - | - | - |

---

## 附录: 故障排查

### Q1: pg_dump 失败 - "could not connect to server"

```bash
# 检查 PG 服务
systemctl status postgresql
# 或 docker ps | grep postgres

# 检查网络
nc -zv $PG_HOST $PG_PORT

# 检查认证
psql -h $PG_HOST -U $PG_USER -d $PG_DB -c "SELECT 1;"
```

### Q2: 恢复后数据不一致

```bash
# 对比备份前后的关键表
psql -d original -c "SELECT count(*) FROM users;"
psql -d restored -c "SELECT count(*) FROM users;"

# 如果不一致，检查 WAL 是否完整
ls -la /var/lib/postgresql/data/pg_wal/
```

### Q3: MinIO 镜像速度慢

```bash
# 调整并发
mc mirror --parallel 8 source target

# 使用增量同步
mc mirror --skip-errors source target
```

# PostgreSQL 高可用与 WAL 归档配置

> Phase Q8.1.2: PG WAL 归档（每 15min）  
> Phase Q8.3.1: 流式复制 + Patroni（生产环境）

---

## 1. WAL 归档配置（PITR 支持）

### 1.1 修改 postgresql.conf

```conf
# WAL 归档相关配置
wal_level = replica                    # 启用 WAL 归档
archive_mode = on                       # 启用归档模式
archive_command = '/usr/local/bin/archive_wal.sh %p %f'  # 归档命令
archive_timeout = 900                   # 强制每 15 分钟归档（即使 WAL 未满）

# 复制相关
max_wal_senders = 10                    # 最大 WAL 发送进程数
wal_keep_size = 1024                    # 保留最近 1GB WAL
hot_standby = on                        # 允许只读副本

# 性能调优
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 1.2 创建归档脚本

```bash
#!/bin/bash
# /usr/local/bin/archive_wal.sh
#
# WAL 归档脚本 - 上传到 MinIO

WAL_FILE="$1"
WAL_FILENAME="$2"

MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_BUCKET="${MINIO_BUCKET:-claywords}"
WAL_PREFIX="backups/wal/$(date +%Y/%m/%d)"

# 上传到 MinIO
mc alias set minio_archive "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>/dev/null

mc cp "$WAL_FILE" "minio_archive/${MINIO_BUCKET}/${WAL_PREFIX}/${WAL_FILENAME}"

# 返回 0 表示成功（PostgreSQL 必须）
exit 0
```

### 1.3 启用配置

```bash
# 修改配置后重启 PG
systemctl restart postgresql

# 验证归档
psql -c "SELECT pg_switch_wal();"  # 强制切换 WAL
ls -la /var/lib/postgresql/data/pg_wal/

# 验证归档到 MinIO
mc ls minio_archive/claywords/backups/wal/
```

---

## 2. 流式复制配置

### 2.1 主库配置

```conf
# postgresql.conf (主库)
listen_addresses = '*'
max_wal_senders = 10
wal_level = replica
hot_standby = on

# pg_hba.conf
host    replication    replicator    0.0.0.0/0    md5
```

### 2.2 创建复制用户

```sql
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator_secret';
```

### 2.3 备库配置

```bash
# 备库初始化
pg_basebackup -h primary-pg.local -D /var/lib/postgresql/data \
    -U replicator -P -v -R -X stream

# 启动备库
systemctl start postgresql

# 验证复制状态
psql -c "SELECT pg_is_in_recovery();"  # 备库返回 true

# 在主库验证
psql -c "SELECT * FROM pg_stat_replication;"
```

---

## 3. Patroni 自动故障切换

### 3.1 Patroni 配置示例

```yaml
# /etc/patroni/patroni.yml
scope: claywords-pg-cluster
namespace: /claywords/
name: pg-node-1

restapi:
  listen: 0.0.0.0:8008
  connect_address: pg-node-1.local:8008

etcd:
  hosts: etcd-1:2379,etcd-2:2379,etcd-3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      use_slots: true
      parameters:
        wal_level: replica
        max_wal_senders: 10
        max_replication_slots: 10
        hot_standby: "on"

  initdb:
    - encoding: UTF8
    - data-checksums

  pg_hba:
    - host replication replicator 0.0.0.0/0 md5
    - host all all 0.0.0.0/0 md5

postgresql:
  listen: 0.0.0.0:5432
  connect_address: pg-node-1.local:5432
  data_dir: /var/lib/postgresql/data
  bin_dir: /usr/lib/postgresql/16/bin
  authentication:
    replication:
      username: replicator
      password: replicator_secret
    superuser:
      username: postgres
      password: postgres_secret
```

### 3.2 启动 Patroni 集群

```bash
# 在每个节点启动 Patroni
systemctl start patroni

# 查看集群状态
patronictl -c /etc/patroni/patroni.yml list

# 输出示例：
# +-------------+------------------+--------+---------+----+-----------+
# | Member      | Host             | Role   | State   | TL | Lag in MB |
# +-------------+------------------+--------+---------+----+-----------+
# | pg-node-1   | 10.0.0.1:5432    | Leader | running | 1  |           |
# | pg-node-2   | 10.0.0.2:5432    | Replica| running | 1  |         0 |
# | pg-node-3   | 10.0.0.3:5432    | Replica| running | 1  |         0 |
# | pg-node-4   | 10.0.0.4:5432    | Replica| running | 1  |         0 |
# +-------------+------------------+--------+---------+----+-----------+
```

### 3.3 测试自动故障切换

```bash
# 杀掉主库
patronictl -c /etc/patroni/patroni.yml restart claywords-pg-cluster pg-node-1

# 30 秒内应该完成切换
patronictl -c /etc/patroni/patroni.yml list

# 验证新主库
psql -h new-leader.local -c "SELECT pg_is_in_recovery();"  # 应该返回 false
```

---

## 4. Redis Sentinel 高可用

### 4.1 Sentinel 配置（3 节点）

```conf
# sentinel.conf
port 26379
dir /var/lib/redis-sentinel
sentinel monitor claywords-redis-master 10.0.0.10 6379 2
sentinel down-after-milliseconds claywords-redis-master 5000
sentinel parallel-syncs claywords-redis-master 1
sentinel failover-timeout claywords-redis-master 30000
sentinel auth-pass claywords-redis-master redis_secret
```

### 4.2 启动 Sentinel

```bash
# 在 3 个节点上启动
redis-sentinel /etc/redis/sentinel.conf

# 检查 Sentinel 状态
redis-cli -p 26379 SENTINEL masters
redis-cli -p 26379 SENTINEL slaves claywords-redis-master
```

### 4.3 应用层连接

```python
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [
        ('sentinel-1.local', 26379),
        ('sentinel-2.local', 26379),
        ('sentinel-3.local', 26379),
    ],
    socket_timeout=0.5
)

# 自动获取主库
master = sentinel.master_for('claywords-redis-master', socket_timeout=0.5)
slave = sentinel.slave_for('claywords-redis-master', socket_timeout=0.5)
```

---

## 5. MinIO 分布式部署（4 节点纠删码）

### 5.1 启动 4 节点 MinIO

```bash
# 在 4 个节点上同时启动
# 节点 1
minio server http://minio{1...4}.local/data --console-address ":9001"

# 数据保护：4 节点可承受 2 节点故障
# 默认配置：EC:2（2 数据 + 2 校验）
```

### 5.2 验证集群状态

```bash
mc admin info minio_cluster
# 输出: 4 nodes, 16 drives online

# 模拟节点故障
ssh minio2.local 'systemctl stop minio'

# 数据仍然可读
mc ls minio_cluster/claywords
```

---

## 6. 监控指标

### 6.1 PostgreSQL 复制延迟

```sql
-- 查询复制延迟
SELECT
    pid,
    application_name,
    state,
    sent_lsn,
    write_lsn,
    flush_lsn,
    replay_lsn,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;
```

### 6.2 Prometheus 告警规则

```yaml
groups:
  - name: postgres_replication
    rules:
      - alert: PostgresReplicationLag
        expr: pg_replication_lag_seconds > 60
        for: 5m
        annotations:
          summary: "PG 复制延迟超过 60 秒"

      - alert: PostgresReplicaDown
        expr: pg_replication_connected_replicas < 2
        for: 1m
        annotations:
          summary: "PG 备库少于 2 个"

  - name: redis_sentinel
    rules:
      - alert: RedisSentinelDown
        expr: up{job="redis-sentinel"} == 0
        for: 1m
        annotations:
          summary: "Redis Sentinel 节点不可用"
```

---

## 7. 灾难恢复目标

### 7.1 RTO/RPO 目标

| 场景 | RTO | RPO | 实现方式 |
|------|-----|-----|---------|
| 主库故障 | < 1 分钟 | 0 | Patroni 自动切换 |
| 备库故障 | 不影响 | 0 | 流式复制 |
| 整个数据中心故障 | < 30 分钟 | < 15 分钟 | 异地备份恢复 |
| Redis 主节点故障 | < 1 分钟 | < 1 秒 | Sentinel 自动切换 |
| MinIO 单节点故障 | 0 | 0 | 纠删码自动恢复 |

### 7.2 演练频率

- **自动化测试**: 每月 CI 自动运行
- **人工演练**: 每季度一次
- **完整 DR 演练**: 每半年一次

---

## 8. 故障切换 Runbook

### 8.1 PostgreSQL 主库故障

```bash
# 1. Patroni 自动检测（30 秒内）
# 2. 选举新主库（自动）
# 3. 切换 DNS / VIP
# 4. 应用自动重连

# 验证步骤
patronictl list
psql -h pg-vip.local -c "SELECT pg_is_in_recovery();"
```

### 8.2 Redis 主节点故障

```bash
# 1. Sentinel 自动检测（5 秒内）
# 2. 选举新主节点
# 3. 应用自动重连（通过 Sentinel）

# 验证
redis-cli -p 26379 SENTINEL get-master-addr-by-name claywords-redis-master
```

---

## 9. 性能基线

### 9.1 备份性能

| 数据库大小 | 全量备份时间 | 恢复时间 |
|-----------|------------|---------|
| 100 MB | 5 秒 | 10 秒 |
| 1 GB | 30 秒 | 60 秒 |
| 10 GB | 5 分钟 | 10 分钟 |
| 100 GB | 30 分钟 | 60 分钟 |

### 9.2 复制延迟基线

- **正常**: < 100 ms
- **告警**: > 1 秒
- **严重**: > 60 秒

---

## 附录: 工具清单

| 工具 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 16+ | 主数据库 |
| Patroni | 3.0+ | PG 高可用 |
| etcd | 3.5+ | Patroni DCS |
| Redis | 7+ | 缓存/队列 |
| Redis Sentinel | 7+ | Redis 高可用 |
| MinIO | latest | 对象存储 |
| pg_dump / pg_restore | 16+ | 备份/恢复 |
| mc (MinIO Client) | latest | MinIO 镜像 |

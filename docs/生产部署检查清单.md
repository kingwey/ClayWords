# 生产部署检查清单

> Phase Q10 P0: 生产环境部署前检查  
> 日期: 2026-06-22  
> 状态: 待完成

---

## 部署前必须完成项 (P0)

### 1. 配置文件 ✅

- [x] `backend/.env.production` - 生产环境配置
- [x] `backend/.env.staging` - Staging 环境配置
- [x] `backend/requirements.lock.txt` - 依赖版本锁定
- [x] `backend/app/core/config.py` - 配置类更新

### 2. 安全配置 ⏸️

- [ ] **关闭 DEBUG 模式**
  - 检查: `ENVIRONMENT=production` + `DEBUG=False`
  - 位置: `.env.production`
  - 状态: ✅ 已配置

- [ ] **JWT 过期时间**
  - 检查: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080` (7天)
  - 位置: `.env.production`
  - 状态: ✅ 已配置

- [ ] **CORS 域名限制**
  - 检查: `CORS_ORIGINS=https://claywords.com,https://www.claywords.com`
  - 位置: `.env.production`
  - 状态: ✅ 已配置

- [ ] **更换生产密钥**
  - `CRYPTO_PEPPER`: ⚠️ 需要生成强随机值
  - `JWT_SECRET_KEY`: ⚠️ 需要生成强随机值
  - `DATABASE_PASSWORD`: ⚠️ 需要生成强随机值
  - `MINIO_SECRET_KEY`: ⚠️ 需要生成强随机值

### 3. HTTPS 配置 ⏸️

- [ ] **域名购买**
  - claywords.com
  - api.claywords.com

- [ ] **DNS 配置**
  - A 记录指向 K8s Ingress IP
  - CNAME 记录配置

- [ ] **TLS 证书**
  - Let's Encrypt 自动签发
  - cert-manager 配置
  - 强制 HTTPS 跳转

### 4. 数据库配置 ⏸️

- [ ] **PostgreSQL**
  - 创建生产数据库
  - 配置连接池
  - 执行 Alembic 迁移

- [ ] **Redis**
  - 配置持久化 (AOF + RDB)
  - 设置最大内存限制
  - 配置密码认证

- [ ] **MinIO**
  - 创建 bucket
  - 配置访问策略
  - 启用版本控制

### 5. K8s 集群 ⏸️

- [ ] **集群准备**
  - 3 个 Master 节点
  - 5 个 Worker 节点
  - 1 个 GPU 节点（可选）

- [ ] **Namespace 创建**
  ```bash
  kubectl create namespace production
  kubectl create namespace staging
  ```

- [ ] **Secrets 创建**
  ```bash
  kubectl create secret generic claywords-secrets \
    --from-literal=DATABASE_PASSWORD=xxx \
    --from-literal=JWT_SECRET_KEY=xxx \
    --from-literal=CRYPTO_PEPPER=xxx \
    --from-literal=MINIO_SECRET_KEY=xxx \
    --from-literal=TONGYI_API_KEY=xxx \
    -n production
  ```

### 6. 监控告警 ✅

- [x] Prometheus 配置
- [x] Grafana Dashboard
- [x] 告警规则
- [ ] 告警接收人配置（飞书/邮件）

### 7. 备份配置 ✅

- [x] PostgreSQL 每日备份脚本
- [x] Redis 每日备份脚本
- [x] MinIO 异地镜像脚本
- [ ] Cron 任务部署

### 8. CI/CD 配置 ✅

- [x] GitHub Actions workflows
- [x] Docker 镜像构建
- [x] 自动化测试
- [ ] 生产部署 workflow

---

## 生产密钥生成

### 生成强随机密钥

```bash
# CRYPTO_PEPPER (32 字节)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT_SECRET_KEY (64 字节)
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# DATABASE_PASSWORD (32 字符)
python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"

# MINIO_SECRET_KEY (32 字符)
python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"
```

### 保存到 K8s Secret

```bash
# 生成所有密钥并保存
export CRYPTO_PEPPER=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
export DB_PASSWORD=$(python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))")
export MINIO_SECRET=$(python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))")

# 创建 Secret
kubectl create secret generic claywords-secrets \
  --from-literal=CRYPTO_PEPPER="$CRYPTO_PEPPER" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET" \
  --from-literal=DATABASE_PASSWORD="$DB_PASSWORD" \
  --from-literal=MINIO_SECRET_KEY="$MINIO_SECRET" \
  -n production

# 验证
kubectl get secret claywords-secrets -n production -o yaml
```

---

## 部署流程

### 1. Staging 环境部署

```bash
# 1. 部署到 Staging
helm install claywords-staging ./helm/claywords \
  --namespace staging \
  --create-namespace \
  -f helm/claywords/values.yaml \
  --set global.environment=staging \
  --set backend.image.tag=staging-latest

# 2. 验证部署
kubectl get pods -n staging
kubectl logs -f deployment/backend -n staging

# 3. 健康检查
curl https://staging-api.claywords.com/health

# 4. 烟雾测试
curl https://staging-api.claywords.com/metrics
```

### 2. Production 环境部署

```bash
# 1. 创建生产 Secrets
kubectl apply -f k8s/secrets-production.yaml

# 2. 部署到 Production
helm install claywords ./helm/claywords \
  --namespace production \
  --create-namespace \
  -f helm/claywords/values-production.yaml

# 3. 验证部署
kubectl get pods -n production
kubectl get svc -n production
kubectl get ingress -n production

# 4. 健康检查
curl https://api.claywords.com/health

# 5. 数据库迁移
kubectl exec -it deployment/backend -n production -- alembic upgrade head
```

### 3. 灰度发布（金丝雀）

```bash
# 1. 部署金丝雀版本（10% 流量）
helm upgrade claywords ./helm/claywords \
  --namespace production \
  -f helm/claywords/values-production.yaml \
  --set backend.canary.enabled=true \
  --set backend.canary.weight=10 \
  --set backend.image.tag=v1.0.1

# 2. 监控指标
kubectl port-forward -n production svc/grafana 3000:3000

# 3. 逐步增加流量
helm upgrade claywords ./helm/claywords \
  --namespace production \
  --set backend.canary.weight=25

helm upgrade claywords ./helm/claywords \
  --namespace production \
  --set backend.canary.weight=50

# 4. 完全切换
helm upgrade claywords ./helm/claywords \
  --namespace production \
  --set backend.canary.enabled=false \
  --set backend.image.tag=v1.0.1
```

---

## 回滚流程

### 快速回滚

```bash
# 查看历史
helm history claywords -n production

# 回滚到上一版本
helm rollback claywords -n production

# 回滚到指定版本
helm rollback claywords 3 -n production
```

---

## 监控指标

### 关键指标

- **Backend Pods**: Ready 3/3
- **CPU 使用率**: < 70%
- **内存使用率**: < 80%
- **请求响应时间**: P95 < 500ms
- **错误率**: < 1%

### 告警阈值

- 5xx 错误率 > 5% → 立即告警
- P95 响应时间 > 1s → 警告
- Pod 重启 > 3 次/小时 → 告警
- 数据库连接池 > 80% → 警告

---

## 故障排查

### 常见问题

#### 1. Pod 无法启动

```bash
# 查看事件
kubectl describe pod <pod-name> -n production

# 查看日志
kubectl logs <pod-name> -n production

# 常见原因
# - Secret 未创建
# - 镜像拉取失败
# - 资源不足
```

#### 2. 数据库连接失败

```bash
# 测试连接
kubectl exec -it deployment/backend -n production -- \
  python -c "import asyncpg; print('OK')"

# 检查 Service
kubectl get svc postgres-service -n production

# 检查 Secret
kubectl get secret claywords-secrets -n production -o yaml
```

#### 3. Ingress 无法访问

```bash
# 检查 Ingress
kubectl describe ingress claywords-ingress -n production

# 检查证书
kubectl get certificate -n production

# 检查 DNS
nslookup api.claywords.com
```

---

## 性能优化

### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_tasks_state ON tasks(state);

-- 分析查询
EXPLAIN ANALYZE SELECT ...;

-- 连接池配置
pool_size = 20
max_overflow = 10
```

### 2. Redis 优化

```bash
# 内存淘汰策略
maxmemory-policy allkeys-lru

# 持久化优化
appendfsync everysec
save 900 1
save 300 10
```

### 3. 应用优化

- 启用 HTTP/2
- 开启 gzip 压缩
- CDN 加速静态资源
- 数据库查询优化
- Redis 缓存热点数据

---

## 安全加固

### 1. 网络安全

- [ ] NetworkPolicy 限制 Pod 间通信
- [ ] Ingress 配置 WAF 规则
- [ ] 启用 DDoS 防护（Cloudflare）

### 2. 访问控制

- [ ] RBAC 最小权限原则
- [ ] Service Account 隔离
- [ ] Secret 加密存储（KMS）

### 3. 审计日志

- [ ] 启用 K8s 审计日志
- [ ] API 访问日志归档
- [ ] 敏感操作记录

---

## 文档清单

- [x] OWASP Top 10 安全检查
- [x] 许可证合规报告
- [x] 备份恢复 Runbook
- [x] 高可用配置文档
- [ ] 运维手册
- [ ] 故障处理手册

---

## 联系方式

**技术负责人**: tech@claywords.com  
**运维负责人**: ops@claywords.com  
**安全负责人**: security@claywords.com  
**值班电话**: 待配置

---

## 上线 Checklist

### 部署前（T-1天）

- [ ] 所有 P0 项完成
- [ ] Staging 环境测试通过
- [ ] 数据库备份完成
- [ ] 回滚方案准备
- [ ] 值班人员到位

### 部署中（T Day）

- [ ] 部署到生产环境
- [ ] 健康检查通过
- [ ] 烟雾测试通过
- [ ] 监控指标正常
- [ ] 日志无异常

### 部署后（T+1天）

- [ ] 24 小时监控正常
- [ ] 用户反馈收集
- [ ] 性能基线建立
- [ ] 上线复盘会议

---

## 修订历史

| 日期 | 版本 | 修改内容 | 作者 |
|------|------|---------|------|
| 2026-06-22 | 1.0 | 初始版本 | OPS Team |

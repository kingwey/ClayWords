# ClayWords Helm Chart

ClayWords 陶瓷定制平台 Kubernetes 部署

## 快速开始

```bash
# 添加 chart 仓库（本地）
helm repo add claywords ./helm

# 安装到 production 命名空间
helm install claywords claywords/claywords \
  --namespace production \
  --create-namespace \
  -f values-production.yaml

# 查看状态
kubectl get pods -n production
```

## Chart 结构

```
helm/claywords/
├── Chart.yaml           # Chart 元数据
├── values.yaml          # 默认配置
├── values-staging.yaml  # Staging 环境配置
├── values-production.yaml  # 生产环境配置
└── templates/
    ├── backend/
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── hpa.yaml
    │   └── configmap.yaml
    ├── worker/
    │   ├── deployment.yaml
    │   └── configmap.yaml
    ├── postgres/
    │   ├── statefulset.yaml
    │   ├── service.yaml
    │   └── pvc.yaml
    ├── redis/
    │   ├── statefulset.yaml
    │   └── service.yaml
    ├── minio/
    │   ├── statefulset.yaml
    │   ├── service.yaml
    │   └── pvc.yaml
    └── ingress.yaml
```

## 配置说明

### Backend

- **Replicas**: 3 (生产), 1 (staging)
- **Resources**: 
  - Request: 500m CPU, 512Mi Memory
  - Limit: 1000m CPU, 1Gi Memory
- **HPA**: 最小 3，最大 10，CPU 70%

### Worker

- **Replicas**: 2 (生产), 1 (staging)
- **Resources**:
  - Request: 1000m CPU, 1Gi Memory
  - Limit: 2000m CPU, 2Gi Memory

### PostgreSQL

- **Storage**: 50Gi (生产), 10Gi (staging)
- **Replicas**: 1 (单节点), 3 (HA with Patroni)
- **Backup**: 每日自动备份到 MinIO

### Redis

- **Storage**: 10Gi
- **Mode**: Standalone (staging), Sentinel (production)

### MinIO

- **Storage**: 100Gi (生产), 20Gi (staging)
- **Mode**: Standalone (staging), Distributed (production)

## 环境变量

通过 ConfigMap 和 Secret 管理：

```yaml
# ConfigMap (非敏感配置)
apiVersion: v1
kind: ConfigMap
metadata:
  name: claywords-config
data:
  DATABASE_HOST: postgres-service
  REDIS_HOST: redis-service
  MINIO_ENDPOINT: http://minio-service:9000

# Secret (敏感配置)
apiVersion: v1
kind: Secret
metadata:
  name: claywords-secrets
type: Opaque
stringData:
  DATABASE_PASSWORD: <base64>
  CRYPTO_PEPPER: <base64>
  JWT_SECRET: <base64>
```

## 健康检查

所有服务配置了 livenessProbe 和 readinessProbe：

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## 持久化存储

使用 PVC (PersistentVolumeClaim)：

- **postgres-data**: 50Gi
- **redis-data**: 10Gi
- **minio-data**: 100Gi

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: claywords-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
    - hosts:
        - api.claywords.com
      secretName: claywords-tls
  rules:
    - host: api.claywords.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend-service
                port:
                  number: 8000
```

## 监控

- **Prometheus**: 自动抓取 `/metrics` 端点
- **Grafana**: 预置 Dashboard
- **Loki**: 日志聚合

## 备份

- **PostgreSQL**: 每日 02:00 自动备份
- **Redis**: 每日 03:00 RDB 备份
- **MinIO**: 异地镜像到阿里云 OSS

## 升级

```bash
# 灰度发布（金丝雀）
helm upgrade claywords claywords/claywords \
  --namespace production \
  -f values-production.yaml \
  --set backend.canary.enabled=true \
  --set backend.canary.weight=10

# 完整升级
helm upgrade claywords claywords/claywords \
  --namespace production \
  -f values-production.yaml
```

## 回滚

```bash
# 查看历史
helm history claywords -n production

# 回滚到上一版本
helm rollback claywords -n production

# 回滚到指定版本
helm rollback claywords 3 -n production
```

## 故障排查

```bash
# 查看 Pod 状态
kubectl get pods -n production

# 查看日志
kubectl logs -f deployment/backend -n production

# 进入容器
kubectl exec -it pod/backend-xxx -n production -- /bin/bash

# 查看事件
kubectl get events -n production --sort-by='.lastTimestamp'
```

## 成本估算

### Staging 环境

- **节点**: 2 个 (4 Core, 8Gi)
- **存储**: 40Gi
- **月成本**: 约 ¥500

### Production 环境

- **节点**: 8 个 (3 master + 5 worker)
  - Master: 4 Core, 8Gi × 3
  - Worker: 8 Core, 16Gi × 4
  - GPU Worker: 1 × GPU 节点
- **存储**: 200Gi SSD
- **月成本**: 约 ¥5000-8000

## 安全

- **网络策略**: 限制 Pod 间通信
- **RBAC**: 最小权限原则
- **Secret 加密**: etcd 加密
- **镜像扫描**: Trivy 自动扫描

## 许可证

MIT License

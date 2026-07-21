#!/bin/bash
#
# 生产部署脚本 - Phase Q10 P0
#
# 用途：一键部署到 K8s 生产环境
# 使用：bash scripts/deploy_production.sh
#

set -euo pipefail

# ============== 配置 ==============
NAMESPACE="production"
RELEASE_NAME="claywords"
CHART_PATH="./helm/claywords"
VALUES_FILE="./helm/claywords/values-production.yaml"

# ============== 函数 ==============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_prerequisites() {
    log "Checking prerequisites..."

    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        log "ERROR: kubectl not found"
        exit 1
    fi

    # 检查 helm
    if ! command -v helm &> /dev/null; then
        log "ERROR: helm not found"
        exit 1
    fi

    # 检查集群连接
    if ! kubectl cluster-info &> /dev/null; then
        log "ERROR: Cannot connect to K8s cluster"
        exit 1
    fi

    log "✓ Prerequisites OK"
}

create_namespace() {
    log "Creating namespace..."
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    log "✓ Namespace ready"
}

create_secrets() {
    log "Creating secrets..."

    # 检查 Secret 是否已存在
    if kubectl get secret claywords-secrets -n "$NAMESPACE" &> /dev/null; then
        log "⚠ Secrets already exist, skipping..."
        return
    fi

    # 生成密钥
    log "Generating secrets..."
    CRYPTO_PEPPER=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    DB_PASSWORD=$(python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))")
    MINIO_SECRET=$(python3 -c "import secrets; import string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))")

    # 创建 Secret
    kubectl create secret generic claywords-secrets \
        --from-literal=CRYPTO_PEPPER="$CRYPTO_PEPPER" \
        --from-literal=JWT_SECRET_KEY="$JWT_SECRET" \
        --from-literal=DATABASE_PASSWORD="$DB_PASSWORD" \
        --from-literal=MINIO_SECRET_KEY="$MINIO_SECRET" \
        --from-literal=TONGYI_API_KEY="${TONGYI_API_KEY:-}" \
        -n "$NAMESPACE"

    log "✓ Secrets created"

    # 保存到临时文件（仅用于记录，生产环境应使用 Vault）
    cat > /tmp/claywords-secrets-backup.txt <<EOF
CRYPTO_PEPPER=$CRYPTO_PEPPER
JWT_SECRET_KEY=$JWT_SECRET
DATABASE_PASSWORD=$DB_PASSWORD
MINIO_SECRET_KEY=$MINIO_SECRET
EOF

    log "⚠ Secrets saved to /tmp/claywords-secrets-backup.txt (backup this file!)"
}

deploy_helm() {
    log "Deploying with Helm..."

    # 检查是否已安装
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log "Release exists, upgrading..."
        helm upgrade "$RELEASE_NAME" "$CHART_PATH" \
            --namespace "$NAMESPACE" \
            -f "$VALUES_FILE" \
            --wait \
            --timeout 10m
    else
        log "Installing new release..."
        helm install "$RELEASE_NAME" "$CHART_PATH" \
            --namespace "$NAMESPACE" \
            --create-namespace \
            -f "$VALUES_FILE" \
            --wait \
            --timeout 10m
    fi

    log "✓ Helm deployment complete"
}

run_migrations() {
    log "Running database migrations..."

    # 等待 backend pod 就绪
    kubectl wait --for=condition=ready pod \
        -l app=backend \
        -n "$NAMESPACE" \
        --timeout=300s

    # 获取 backend pod 名称
    POD=$(kubectl get pods -n "$NAMESPACE" -l app=backend -o jsonpath='{.items[0].metadata.name}')

    # 运行迁移
    kubectl exec -it "$POD" -n "$NAMESPACE" -- alembic upgrade head

    log "✓ Migrations complete"
}

verify_deployment() {
    log "Verifying deployment..."

    # 检查 Pods
    log "Checking pods..."
    kubectl get pods -n "$NAMESPACE"

    # 检查 Services
    log "Checking services..."
    kubectl get svc -n "$NAMESPACE"

    # 检查 Ingress
    log "Checking ingress..."
    kubectl get ingress -n "$NAMESPACE"

    # 健康检查
    log "Checking health endpoint..."
    INGRESS_HOST=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[0].spec.rules[0].host}')
    if [ -n "$INGRESS_HOST" ]; then
        curl -f "https://$INGRESS_HOST/health" || log "⚠ Health check failed"
    fi

    log "✓ Deployment verified"
}

show_status() {
    log "=== Deployment Status ==="

    echo ""
    echo "Namespace: $NAMESPACE"
    echo "Release: $RELEASE_NAME"
    echo ""

    kubectl get all -n "$NAMESPACE"

    echo ""
    log "Access URLs:"
    kubectl get ingress -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,HOSTS:.spec.rules[*].host
}

# ============== 主流程 ==============
main() {
    log "=== ClayWords Production Deployment ==="

    check_prerequisites
    create_namespace
    create_secrets
    deploy_helm
    run_migrations
    verify_deployment
    show_status

    log "=== Deployment Complete ==="
    log "Next steps:"
    log "1. Monitor pods: kubectl get pods -n $NAMESPACE -w"
    log "2. Check logs: kubectl logs -f deployment/backend -n $NAMESPACE"
    log "3. Access Grafana: kubectl port-forward svc/grafana 3000:3000 -n $NAMESPACE"
}

main "$@"

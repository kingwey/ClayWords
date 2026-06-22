#!/usr/bin/env python3
"""
P0 生产部署配置验证脚本

验证所有 P0 必须项已完成
"""

import sys
from pathlib import Path


def test_production_env_exists():
    """测试生产环境配置存在"""
    print("Testing production .env...", end=" ")
    env_prod = Path("backend/.env.production")
    if env_prod.exists():
        content = env_prod.read_text(encoding='utf-8')
        if "ENVIRONMENT=production" in content and "DEBUG=False" in content:
            print(f"[OK] Production config exists")
            return True
        else:
            print(f"[FAIL] Missing required config")
            return False
    else:
        print("[FAIL] .env.production not found")
        return False


def test_staging_env_exists():
    """测试 Staging 环境配置存在"""
    print("\nTesting staging .env...", end=" ")
    env_staging = Path("backend/.env.staging")
    if env_staging.exists():
        print(f"[OK] Staging config exists")
        return True
    else:
        print("[FAIL] .env.staging not found")
        return False


def test_requirements_lock_exists():
    """测试依赖版本锁定文件存在"""
    print("\nTesting requirements.lock.txt...", end=" ")
    lock_file = Path("backend/requirements.lock.txt")
    if lock_file.exists():
        content = lock_file.read_text(encoding='utf-8')
        # 检查关键依赖
        required_deps = ["fastapi==", "sqlalchemy==", "redis=="]
        missing = [dep for dep in required_deps if dep not in content]
        if not missing:
            print(f"[OK] Dependencies locked")
            return True
        else:
            print(f"[FAIL] Missing: {missing}")
            return False
    else:
        print("[FAIL] requirements.lock.txt not found")
        return False


def test_config_updated():
    """测试配置文件已更新"""
    print("\nTesting config.py updates...", end=" ")
    config = Path("backend/app/core/config.py")
    if config.exists():
        content = config.read_text(encoding='utf-8')
        required_items = [
            "ENVIRONMENT",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
            "CORS_ORIGINS",
            "is_production",
        ]
        missing = [item for item in required_items if item not in content]
        if not missing:
            print(f"[OK] Config updated")
            return True
        else:
            print(f"[FAIL] Missing: {missing}")
            return False
    else:
        print("[FAIL] config.py not found")
        return False


def test_main_uses_config_cors():
    """测试 main.py 使用配置的 CORS"""
    print("\nTesting main.py CORS config...", end=" ")
    main_file = Path("backend/app/main.py")
    if main_file.exists():
        content = main_file.read_text(encoding='utf-8')
        if "cors_origins_list" in content:
            print(f"[OK] CORS uses config")
            return True
        else:
            print(f"[FAIL] CORS hardcoded")
            return False
    else:
        print("[FAIL] main.py not found")
        return False


def test_helm_production_values():
    """测试 Helm production values 存在"""
    print("\nTesting Helm production values...", end=" ")
    values_prod = Path("helm/claywords/values-production.yaml")
    if values_prod.exists():
        content = values_prod.read_text(encoding='utf-8')
        if "environment: production" in content:
            print(f"[OK] Helm production values exists")
            return True
        else:
            print(f"[FAIL] Missing production config")
            return False
    else:
        print("[FAIL] values-production.yaml not found")
        return False


def test_deploy_script_exists():
    """测试部署脚本存在"""
    print("\nTesting deploy script...", end=" ")
    deploy_script = Path("scripts/deploy_production.sh")
    if deploy_script.exists():
        print(f"[OK] Deploy script exists")
        return True
    else:
        print("[FAIL] deploy_production.sh not found")
        return False


def test_deployment_checklist():
    """测试部署检查清单存在"""
    print("\nTesting deployment checklist...", end=" ")
    checklist = Path("docs/生产部署检查清单.md")
    if checklist.exists():
        size = checklist.stat().st_size
        if size > 3000:
            print(f"[OK] Deployment checklist exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Checklist too small")
            return False
    else:
        print("[FAIL] Checklist not found")
        return False


def test_jwt_expiration_configured():
    """测试 JWT 过期时间已配置"""
    print("\nTesting JWT expiration...", end=" ")
    env_prod = Path("backend/.env.production")
    if env_prod.exists():
        content = env_prod.read_text(encoding='utf-8')
        if "JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080" in content:  # 7 天
            print(f"[OK] JWT expires in 7 days")
            return True
        else:
            print(f"[FAIL] JWT expiration not set")
            return False
    else:
        print("[SKIP] .env.production not found")
        return False


def test_debug_disabled():
    """测试生产环境 DEBUG 关闭"""
    print("\nTesting DEBUG disabled...", end=" ")
    env_prod = Path("backend/.env.production")
    if env_prod.exists():
        content = env_prod.read_text(encoding='utf-8')
        if "DEBUG=False" in content:
            print(f"[OK] DEBUG disabled")
            return True
        else:
            print(f"[FAIL] DEBUG not disabled")
            return False
    else:
        print("[SKIP] .env.production not found")
        return False


def main():
    print("=== P0 Production Deployment Config Verification ===\n")

    results = []

    # Run all tests
    results.append(test_production_env_exists())
    results.append(test_staging_env_exists())
    results.append(test_requirements_lock_exists())
    results.append(test_config_updated())
    results.append(test_main_uses_config_cors())
    results.append(test_helm_production_values())
    results.append(test_deploy_script_exists())
    results.append(test_deployment_checklist())
    results.append(test_jwt_expiration_configured())
    results.append(test_debug_disabled())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All P0 deployment configs ready!")
        print("\nNext steps:")
        print("1. Generate production secrets:")
        print("   python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        print("2. Configure K8s cluster")
        print("3. Deploy: bash scripts/deploy_production.sh")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

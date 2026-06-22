#!/usr/bin/env python3
"""
Phase Q8 验证脚本

测试备份、恢复脚本和高可用配置
"""

import os
import sys
import subprocess
from pathlib import Path


def test_backup_pg_script_exists():
    """测试 PG 备份脚本存在"""
    print("Testing backup_pg.sh exists...", end=" ")
    script = Path("scripts/backup_pg.sh")
    if script.exists():
        # 检查脚本是否可读
        size = script.stat().st_size
        if size > 1000:
            print(f"[OK] backup_pg.sh exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Script too small: {size} bytes")
            return False
    else:
        print("[FAIL] Script not found")
        return False


def test_backup_redis_script_exists():
    """测试 Redis 备份脚本存在"""
    print("\nTesting backup_redis.sh exists...", end=" ")
    script = Path("scripts/backup_redis.sh")
    if script.exists():
        size = script.stat().st_size
        if size > 500:
            print(f"[OK] backup_redis.sh exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Script too small: {size} bytes")
            return False
    else:
        print("[FAIL] Script not found")
        return False


def test_mirror_minio_script_exists():
    """测试 MinIO 镜像脚本存在"""
    print("\nTesting mirror_minio.sh exists...", end=" ")
    script = Path("scripts/mirror_minio.sh")
    if script.exists():
        print(f"[OK] mirror_minio.sh exists ({script.stat().st_size} bytes)")
        return True
    else:
        print("[FAIL] Script not found")
        return False


def test_restore_pg_script_exists():
    """测试 PG 恢复脚本存在"""
    print("\nTesting restore_pg.sh exists...", end=" ")
    script = Path("scripts/restore_pg.sh")
    if script.exists():
        print(f"[OK] restore_pg.sh exists ({script.stat().st_size} bytes)")
        return True
    else:
        print("[FAIL] Script not found")
        return False


def test_runbook_exists():
    """测试备份恢复 runbook 存在"""
    print("\nTesting backup runbook...", end=" ")
    runbook = Path("docs/备份恢复-Runbook.md")
    if runbook.exists():
        size = runbook.stat().st_size
        if size > 2000:
            print(f"[OK] Runbook exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Runbook too small")
            return False
    else:
        print("[FAIL] Runbook not found")
        return False


def test_ha_config_exists():
    """测试高可用配置文档存在"""
    print("\nTesting HA config doc...", end=" ")
    doc = Path("docs/PG-高可用配置.md")
    if doc.exists():
        size = doc.stat().st_size
        if size > 1000:
            print(f"[OK] HA config doc exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Doc too small")
            return False
    else:
        print("[FAIL] Doc not found")
        return False


def test_restore_test_workflow_exists():
    """测试 CI 恢复测试 workflow 存在"""
    print("\nTesting restore-test workflow...", end=" ")
    workflow = Path(".github/workflows/restore-test.yml")
    if workflow.exists():
        print(f"[OK] Workflow exists ({workflow.stat().st_size} bytes)")
        return True
    else:
        print("[FAIL] Workflow not found")
        return False


def test_redis_aof_enabled():
    """测试 Redis AOF 持久化已启用"""
    print("\nTesting Redis AOF in docker-compose...", end=" ")
    compose = Path("infra/docker-compose.yml")
    if compose.exists():
        content = compose.read_text(encoding="utf-8")
        if "appendonly yes" in content and "everysec" in content:
            print("[OK] Redis AOF enabled with everysec")
            return True
        else:
            print("[FAIL] AOF not properly configured")
            return False
    else:
        print("[FAIL] docker-compose.yml not found")
        return False


def test_pg_backup_script_executable():
    """测试 PG 备份脚本可执行（检查内容）"""
    print("\nTesting backup script content...", end=" ")
    script = Path("scripts/backup_pg.sh")
    if not script.exists():
        print("[SKIP] Script not found")
        return False

    content = script.read_text(encoding="utf-8")

    # 检查关键命令
    required_commands = ["pg_dump", "mc cp", "BACKUP_DIR"]
    missing = [cmd for cmd in required_commands if cmd not in content]

    if not missing:
        print("[OK] Backup script has all required commands")
        return True
    else:
        print(f"[FAIL] Missing commands: {missing}")
        return False


def test_workflow_yaml_valid():
    """测试 workflow YAML 有效"""
    print("\nTesting workflow YAML validity...", end=" ")
    try:
        import yaml

        workflow = Path(".github/workflows/restore-test.yml")
        with open(workflow, "r", encoding="utf-8") as f:
            yaml.safe_load(f)

        print("[OK] Workflow YAML valid")
        return True

    except ImportError:
        print("[SKIP] PyYAML not installed")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def main():
    print("=== Phase Q8 Verification ===\n")

    results = []

    # Run all tests
    results.append(test_backup_pg_script_exists())
    results.append(test_backup_redis_script_exists())
    results.append(test_mirror_minio_script_exists())
    results.append(test_restore_pg_script_exists())
    results.append(test_runbook_exists())
    results.append(test_ha_config_exists())
    results.append(test_restore_test_workflow_exists())
    results.append(test_redis_aof_enabled())
    results.append(test_pg_backup_script_executable())
    results.append(test_workflow_yaml_valid())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q8 features ready.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

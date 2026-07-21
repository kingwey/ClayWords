#!/usr/bin/env python3
"""
Phase Q9 验证脚本

测试 CI/CD 配置和测试基础设施
"""

import os
import sys
import subprocess
from pathlib import Path


def test_pytest_config_exists():
    """测试 pytest 配置存在"""
    print("Testing pytest config...", end=" ")
    pytest_ini = Path("backend/pytest.ini")
    if pytest_ini.exists():
        print(f"[OK] pytest.ini exists ({pytest_ini.stat().st_size} bytes)")
        return True
    else:
        print("[FAIL] pytest.ini not found")
        return False


def test_conftest_exists():
    """测试 conftest.py 存在"""
    print("\nTesting conftest.py...", end=" ")
    conftest = Path("backend/tests/conftest.py")
    if conftest.exists():
        print(f"[OK] conftest.py exists")
        return True
    else:
        print("[FAIL] conftest.py not found")
        return False


def test_unit_tests_exist():
    """测试单元测试文件存在"""
    print("\nTesting unit test files...", end=" ")
    test_files = [
        "backend/tests/test_crypto.py",
        "backend/tests/test_metrics.py",
        "backend/tests/test_logging_middleware.py",
        "backend/tests/test_alerting.py",
        "backend/tests/test_payment.py",
        "backend/tests/test_smoke.py",
    ]

    missing = [f for f in test_files if not Path(f).exists()]
    if not missing:
        print(f"[OK] All {len(test_files)} test files exist")
        return True
    else:
        print(f"[FAIL] Missing: {missing}")
        return False


def test_github_workflows_exist():
    """测试 GitHub Actions 工作流存在"""
    print("\nTesting GitHub workflows...", end=" ")
    workflows = [
        ".github/workflows/backend-ci.yml",
        ".github/workflows/docker-build.yml",
    ]

    missing = [w for w in workflows if not Path(w).exists()]
    if not missing:
        print(f"[OK] All {len(workflows)} workflows exist")
        return True
    else:
        print(f"[FAIL] Missing: {missing}")
        return False


def test_dockerfile_exists():
    """测试 Dockerfile 存在"""
    print("\nTesting Dockerfiles...", end=" ")
    dockerfiles = [
        "backend/Dockerfile",
        "backend/Dockerfile.worker",
        "backend/.dockerignore",
    ]

    missing = [f for f in dockerfiles if not Path(f).exists()]
    if not missing:
        print(f"[OK] All {len(dockerfiles)} Docker files exist")
        return True
    else:
        print(f"[FAIL] Missing: {missing}")
        return False


def test_pytest_runs():
    """测试 pytest 可以运行"""
    print("\nTesting pytest execution...", end=" ")
    try:
        # Set environment
        env = os.environ.copy()
        env.update({
            "DATABASE_URL": "postgresql+asyncpg://claywords:claywords_secret@localhost:5432/claywords",
            "REDIS_URL": "redis://localhost:6379",
            "CRYPTO_PEPPER": "test_pepper",
        })

        # Run pytest on unit tests
        result = subprocess.run(
            [
                "pytest",
                "tests/test_crypto.py",
                "tests/test_metrics.py",
                "tests/test_alerting.py",
                "-v", "--tb=no", "-q",
            ],
            cwd="backend",
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            # Count passed tests
            output_lower = result.stdout.lower()
            passed_count = output_lower.count("passed")
            print(f"[OK] Tests passed (count: {passed_count})")
            return True
        else:
            print(f"[FAIL] Exit code: {result.returncode}")
            print(result.stdout[-500:])
            return False

    except subprocess.TimeoutExpired:
        print("[FAIL] Timeout")
        return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def test_workflow_yaml_valid():
    """测试 YAML 工作流文件有效"""
    print("\nTesting YAML validity...", end=" ")
    try:
        import yaml

        for workflow in [
            ".github/workflows/backend-ci.yml",
            ".github/workflows/docker-build.yml",
        ]:
            with open(workflow, "r", encoding="utf-8") as f:
                yaml.safe_load(f)

        print("[OK] All YAML files valid")
        return True

    except ImportError:
        print("[SKIP] PyYAML not installed")
        return True
    except yaml.YAMLError as e:
        print(f"[FAIL] YAML error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


def main():
    print("=== Phase Q9 Verification ===\n")

    results = []

    # Run all tests
    results.append(test_pytest_config_exists())
    results.append(test_conftest_exists())
    results.append(test_unit_tests_exist())
    results.append(test_github_workflows_exist())
    results.append(test_dockerfile_exists())
    results.append(test_pytest_runs())
    results.append(test_workflow_yaml_valid())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q9 features ready.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

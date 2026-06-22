#!/usr/bin/env python3
"""
Phase Q10 验证脚本

测试安全加固和生产部署配置
"""

import sys
from pathlib import Path


def test_owasp_checklist_exists():
    """测试 OWASP 安全检查清单存在"""
    print("Testing OWASP checklist...", end=" ")
    doc = Path("docs/security-owasp-top10.md")
    if doc.exists():
        size = doc.stat().st_size
        if size > 5000:
            print(f"[OK] OWASP checklist exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Checklist too small")
            return False
    else:
        print("[FAIL] Checklist not found")
        return False


def test_rate_limit_middleware_exists():
    """测试速率限制中间件存在"""
    print("\nTesting rate limit middleware...", end=" ")
    middleware = Path("backend/app/core/rate_limit.py")
    if middleware.exists():
        size = middleware.stat().st_size
        if size > 2000:
            print(f"[OK] Rate limit middleware exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Middleware too small")
            return False
    else:
        print("[FAIL] Middleware not found")
        return False


def test_prompt_defense_exists():
    """测试 Prompt 注入防护存在"""
    print("\nTesting prompt defense...", end=" ")
    defense = Path("backend/app/core/prompt_defense.py")
    if defense.exists():
        size = defense.stat().st_size
        if size > 3000:
            print(f"[OK] Prompt defense exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Defense module too small")
            return False
    else:
        print("[FAIL] Defense module not found")
        return False


def test_license_compliance_exists():
    """测试许可证合规文档存在"""
    print("\nTesting license compliance doc...", end=" ")
    doc = Path("docs/license-compliance.md")
    if doc.exists():
        size = doc.stat().st_size
        if size > 3000:
            print(f"[OK] License compliance doc exists ({size} bytes)")
            return True
        else:
            print(f"[FAIL] Doc too small")
            return False
    else:
        print("[FAIL] Doc not found")
        return False


def test_helm_chart_exists():
    """测试 Helm Chart 存在"""
    print("\nTesting Helm chart...", end=" ")
    chart = Path("helm/claywords/Chart.yaml")
    values = Path("helm/claywords/values.yaml")
    readme = Path("helm/claywords/README.md")

    if chart.exists() and values.exists() and readme.exists():
        print(f"[OK] Helm chart complete")
        return True
    else:
        missing = []
        if not chart.exists():
            missing.append("Chart.yaml")
        if not values.exists():
            missing.append("values.yaml")
        if not readme.exists():
            missing.append("README.md")
        print(f"[FAIL] Missing: {missing}")
        return False


def test_rate_limit_rules():
    """测试速率限制规则内容"""
    print("\nTesting rate limit rules content...", end=" ")
    middleware = Path("backend/app/core/rate_limit.py")
    if not middleware.exists():
        print("[SKIP] Middleware not found")
        return False

    content = middleware.read_text(encoding="utf-8")

    # 检查关键规则
    required_rules = [
        "/api/v1/auth/login",  # 登录限制
        "/api/v1/sse/tickets",  # SSE 票据限制
        "/api/v1/tasks",  # 任务限制
    ]

    missing = [rule for rule in required_rules if rule not in content]

    if not missing:
        print("[OK] All required rate limit rules present")
        return True
    else:
        print(f"[FAIL] Missing rules: {missing}")
        return False


def test_prompt_defense_blacklist():
    """测试 Prompt 防护黑名单"""
    print("\nTesting prompt defense blacklist...", end=" ")
    defense = Path("backend/app/core/prompt_defense.py")
    if not defense.exists():
        print("[SKIP] Defense module not found")
        return False

    content = defense.read_text(encoding="utf-8")

    # 检查关键黑名单词
    required_keywords = [
        "忽略",
        "ignore",
        "system prompt",
        "password",
    ]

    missing = [kw for kw in required_keywords if kw not in content]

    if not missing:
        print("[OK] Prompt defense blacklist complete")
        return True
    else:
        print(f"[FAIL] Missing keywords: {missing}")
        return False


def test_owasp_p0_items():
    """测试 OWASP P0 优先级项"""
    print("\nTesting OWASP P0 items...", end=" ")
    doc = Path("docs/security-owasp-top10.md")
    if not doc.exists():
        print("[SKIP] OWASP doc not found")
        return False

    content = doc.read_text(encoding="utf-8")

    # 检查 P0 关键项
    p0_items = [
        "HTTPS",
        "DEBUG",
        "CORS",
        "JWT",
        "速率限制",
        "Prompt 注入",
    ]

    missing = [item for item in p0_items if item not in content]

    if not missing:
        print("[OK] All P0 items documented")
        return True
    else:
        print(f"[FAIL] Missing P0 items: {missing}")
        return False


def test_helm_values_structure():
    """测试 Helm values 结构"""
    print("\nTesting Helm values structure...", end=" ")
    values = Path("helm/claywords/values.yaml")
    if not values.exists():
        print("[SKIP] values.yaml not found")
        return False

    content = values.read_text(encoding="utf-8")

    # 检查关键配置
    required_sections = [
        "backend:",
        "worker:",
        "postgres:",
        "redis:",
        "minio:",
        "ingress:",
    ]

    missing = [section for section in required_sections if section not in content]

    if not missing:
        print("[OK] Helm values structure complete")
        return True
    else:
        print(f"[FAIL] Missing sections: {missing}")
        return False


def main():
    print("=== Phase Q10 Verification ===\n")

    results = []

    # Run all tests
    results.append(test_owasp_checklist_exists())
    results.append(test_rate_limit_middleware_exists())
    results.append(test_prompt_defense_exists())
    results.append(test_license_compliance_exists())
    results.append(test_helm_chart_exists())
    results.append(test_rate_limit_rules())
    results.append(test_prompt_defense_blacklist())
    results.append(test_owasp_p0_items())
    results.append(test_helm_values_structure())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q10 features ready.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

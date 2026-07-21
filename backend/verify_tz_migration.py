#!/usr/bin/env python
"""验证 timezone-aware 迁移的快速检查脚本"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))


def test_time_helper():
    """测试 time.utcnow() 返回 aware datetime"""
    from app.core.time import utcnow
    dt = utcnow()
    assert dt.tzinfo is not None, "utcnow() should return timezone-aware datetime"
    print(f"✓ time.utcnow() returns aware datetime: {dt.tzinfo}")


def test_entities_import():
    """测试 entities.py 可独立 import"""
    from app.models.entities import Base
    tables = Base.metadata.tables
    print(f"✓ entities.py imports successfully: {len(tables)} tables")

    # 检查一个表的时间列定义
    users_table = tables['users']
    created_at_col = users_table.c.created_at
    print(f"✓ users.created_at timezone={created_at_col.type.timezone}")
    assert created_at_col.type.timezone is True, "DateTime columns should have timezone=True"


def test_no_naive_utcnow():
    """确认代码中没有遗留的 datetime.utcnow()"""
    import subprocess
    result = subprocess.run(
        ['grep', '-rn', 'datetime.utcnow', 'app/', '--include=*.py'],
        capture_output=True,
        text=True
    )
    # 只有 app/core/time.py 中的实现应该存在
    lines = [line for line in result.stdout.split('\n') if line and 'app/core/time.py' not in line]
    if lines:
        print(f"✗ Found {len(lines)} remaining datetime.utcnow() calls:")
        for line in lines:
            print(f"  {line}")
        sys.exit(1)
    print("✓ No naive datetime.utcnow() calls remain (except time.py helper)")


if __name__ == '__main__':
    print("=== Timezone-aware Migration Verification ===\n")

    try:
        test_time_helper()
        test_entities_import()
        test_no_naive_utcnow()
        print("\n✅ All checks passed!")
    except Exception as e:
        print(f"\n❌ Check failed: {e}")
        sys.exit(1)

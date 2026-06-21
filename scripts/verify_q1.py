#!/usr/bin/env python3
"""
Phase Q1 验证脚本

测试 Postgres + pgvector + Alembic 迁移系统
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import text
from app.db.session import engine, async_session_maker
from app.models.entities import User, DesignTemplate
from app.core.crypto import get_crypto


async def test_connection():
    """测试数据库连接"""
    print("Testing database connection...", end=" ")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"[OK] Connected to PostgreSQL")
            print(f"  Version: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_pgvector():
    """测试 pgvector 扩展"""
    print("\nTesting pgvector extension...", end=" ")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
            version = result.scalar()
            if version:
                print(f"[OK] pgvector {version} installed")
                return True
            else:
                print("[FAIL] pgvector not found")
                return False
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_tables():
    """测试所有表是否创建"""
    print("\nTesting tables...", end=" ")
    expected_tables = [
        'users', 'studios', 'sessions', 'session_messages',
        'design_templates', 'designs', 'design_versions',
        'orders', 'order_logs', 'studio_craft_overrides',
        'idempotency_keys', 'tasks', 'alembic_version'
    ]

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ))
            tables = [row[0] for row in result]

            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"[FAIL] Missing tables: {missing}")
                return False
            else:
                print(f"[OK] All {len(expected_tables)} tables created")
                return True
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_vector_column():
    """测试 vector 列类型"""
    print("\nTesting vector column type...", end=" ")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT column_name, udt_name, character_maximum_length
                FROM information_schema.columns
                WHERE table_name='design_templates' AND column_name='embedding'
            """))
            row = result.first()
            if row and 'vector' in str(row):
                print(f"[OK] embedding column is vector type")
                return True
            else:
                print(f"[FAIL] embedding column type incorrect: {row}")
                return False
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_ivfflat_index():
    """测试 ivfflat 索引"""
    print("\nTesting ivfflat index...", end=" ")
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename='design_templates' AND indexname='idx_design_templates_embedding'
            """))
            row = result.first()
            if row and 'ivfflat' in row[1]:
                print(f"[OK] ivfflat index created")
                return True
            else:
                print(f"[FAIL] ivfflat index not found")
                return False
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_encryption():
    """测试加密字段"""
    print("\nTesting encrypted fields...", end=" ")
    try:
        crypto = get_crypto()
        test_phone = "13912345678"

        # 加密
        encrypted = crypto.encrypt(test_phone)

        # 解密
        decrypted = crypto.decrypt(encrypted)

        if decrypted == test_phone:
            print(f"[OK] Encryption/decryption working")
            return True
        else:
            print(f"[FAIL] Decryption mismatch")
            return False
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        return False


async def test_crud_operations():
    """测试 CRUD 操作"""
    print("\nTesting CRUD operations...", end=" ")
    try:
        async with async_session_maker() as session:
            # Create
            crypto = get_crypto()
            test_phone = "13900000001"
            user = User(
                phone_hash=crypto.hash_phone(test_phone),
                phone_encrypted=test_phone  # EncryptedStr will auto-encrypt
            )
            session.add(user)
            await session.commit()

            # Read
            await session.refresh(user)
            user_id = user.user_id

            # Verify phone is decrypted correctly
            if user.phone_encrypted == test_phone:
                print(f"[OK] CRUD operations working")
            else:
                print(f"[FAIL] Phone decryption failed: expected {test_phone}, got {user.phone_encrypted}")
                return False

            # Cleanup
            await session.delete(user)
            await session.commit()

            return True
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=== Phase Q1 Verification ===\n")

    results = []

    # Run all tests
    results.append(await test_connection())
    results.append(await test_pgvector())
    results.append(await test_tables())
    results.append(await test_vector_column())
    results.append(await test_ivfflat_index())
    results.append(await test_encryption())
    results.append(await test_crud_operations())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q1 is complete.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


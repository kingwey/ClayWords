#!/usr/bin/env python3
"""
Phase Q4 验证脚本

测试文件上传、MinIO 集成和安全扫描状态机
"""

import asyncio
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.storage import minio_client
from app.db.session import async_session_maker
from app.models.entities import Upload
from sqlalchemy import select


async def test_minio_connection():
    """测试 MinIO 连接"""
    print("Testing MinIO connection...", end=" ")
    try:
        minio_client.connect()
        # Try to check bucket
        bucket_exists = minio_client._client.bucket_exists(minio_client._client._bucket_name)
        print(f"[OK] MinIO connected, bucket exists: {bucket_exists}")
        return True
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_presigned_url_generation():
    """测试预签名 URL 生成"""
    print("\nTesting presigned URL generation...", end=" ")
    try:
        minio_client.connect()

        # Generate object key
        object_key = minio_client.generate_object_key("test", "txt")

        # Generate presigned PUT URL
        put_url = minio_client.presigned_put_url(object_key)

        if put_url and "localhost:9000" in put_url:
            print(f"[OK] Presigned URL generated")
            print(f"     Object key: {object_key}")
            return True
        else:
            print(f"[FAIL] Invalid URL: {put_url}")
            return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_upload_record_creation():
    """测试上传记录创建"""
    print("\nTesting upload record creation...", end=" ")
    try:
        async with async_session_maker() as session:
            # Create upload record
            upload = Upload(
                object_key="test/verification.txt",
                file_name="verification.txt",
                file_size=1024,
                mime_type="text/plain",
                state="pending",
                uploader_id="test_user_123",
            )
            session.add(upload)
            await session.commit()
            await session.refresh(upload)

            upload_id = upload.upload_id

            # Verify it was created
            stmt = select(Upload).where(Upload.upload_id == upload_id)
            result = await session.execute(stmt)
            retrieved = result.scalar_one_or_none()

            if retrieved and retrieved.state == "pending":
                print(f"[OK] Upload record created: {upload_id[:8]}...")

                # Cleanup
                await session.delete(retrieved)
                await session.commit()
                return True
            else:
                print("[FAIL] Record not found or invalid")
                return False

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[FAIL] {e}")
        return False


async def test_state_transitions():
    """测试状态机转换"""
    print("\nTesting state transitions...", end=" ")
    try:
        async with async_session_maker() as session:
            # Create upload
            upload = Upload(
                object_key="test/state_test.txt",
                file_name="state_test.txt",
                file_size=512,
                mime_type="text/plain",
                state="pending",
                uploader_id="test_user_456",
            )
            session.add(upload)
            await session.commit()
            await session.refresh(upload)

            upload_id = upload.upload_id

            # Transition: pending -> scanning
            upload.state = "scanning"
            await session.commit()

            # Transition: scanning -> clean
            upload.state = "clean"
            upload.scan_result = {"clean": True, "threats": []}
            await session.commit()

            # Verify final state
            await session.refresh(upload)
            if upload.state == "clean" and upload.scan_result.get("clean"):
                print("[OK] State transitions working")

                # Cleanup
                await session.delete(upload)
                await session.commit()
                return True
            else:
                print(f"[FAIL] Final state incorrect: {upload.state}")
                return False

    except Exception as e:
        print(f"[FAIL] {e}")
        return False


async def test_file_type_validation():
    """测试文件类型验证逻辑"""
    print("\nTesting file type validation logic...", end=" ")

    # These would normally be tested via API, but we can verify the constants
    from app.api.uploads import (
        ALLOWED_IMAGE_TYPES,
        ALLOWED_MODEL_TYPES,
        MAX_IMAGE_SIZE,
        MAX_MODEL_SIZE,
    )

    if (
        "image/jpeg" in ALLOWED_IMAGE_TYPES
        and "model/gltf-binary" in ALLOWED_MODEL_TYPES
        and MAX_IMAGE_SIZE == 10 * 1024 * 1024
        and MAX_MODEL_SIZE == 50 * 1024 * 1024
    ):
        print("[OK] File type validation configured")
        return True
    else:
        print("[FAIL] Validation configuration incorrect")
        return False


async def test_uploads_table_schema():
    """测试 uploads 表结构"""
    print("\nTesting uploads table schema...", end=" ")
    try:
        from sqlalchemy import inspect
        from app.db.session import engine

        async with engine.connect() as conn:
            # Check if table exists
            result = await conn.execute(
                sqlalchemy.text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'uploads'
                """)
            )
            columns = {row[0]: row[1] for row in result}

            required_columns = {
                'upload_id', 'object_key', 'file_name',
                'file_size', 'mime_type', 'state',
                'uploader_id', 'created_at'
            }

            if required_columns.issubset(columns.keys()):
                print(f"[OK] Table schema correct ({len(columns)} columns)")
                return True
            else:
                missing = required_columns - columns.keys()
                print(f"[FAIL] Missing columns: {missing}")
                return False

    except Exception as e:
        import sqlalchemy
        print(f"[FAIL] {e}")
        return False


async def main():
    print("=== Phase Q4 Verification ===\n")

    results = []

    # Run all tests
    results.append(await test_minio_connection())
    results.append(await test_presigned_url_generation())
    results.append(await test_upload_record_creation())
    results.append(await test_state_transitions())
    results.append(await test_file_type_validation())
    results.append(await test_uploads_table_schema())

    # Summary
    print("\n=== Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Phase Q4 core features complete.")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

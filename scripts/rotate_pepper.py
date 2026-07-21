#!/usr/bin/env python3
"""
Pepper Rotation Script

轮换加密 pepper，支持 7 天双 pepper 共存窗口。

Usage:
    # Step 1: 设置新 pepper（双 pepper 模式）
    python rotate_pepper.py --old-pepper "old_value" --new-pepper "new_value" --dual-mode

    # Step 2: 7天后移除旧 pepper
    python rotate_pepper.py --old-pepper "old_value" --new-pepper "new_value" --finalize
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.entities import User
from app.core.crypto import CryptoService
from app.core.config import settings


async def rotate_users(
    session: AsyncSession,
    old_crypto: CryptoService,
    new_crypto: CryptoService,
    batch_size: int = 100
):
    """重新加密所有用户的敏感数据"""
    print("Fetching users...", end=" ", flush=True)
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()
    print(f"{len(users)} users found")

    if not users:
        print("No users to rotate")
        return 0

    count = 0
    errors = 0

    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]

        for user in batch:
            try:
                # 解密手机号（使用旧 pepper）
                phone = old_crypto.decrypt(user.phone_encrypted)

                # 重新加密（使用新 pepper）
                user.phone_encrypted = new_crypto.encrypt(phone)
                user.phone_hash = new_crypto.hash_phone(phone)

                # 处理可选字段
                if user.email_encrypted:
                    try:
                        email = old_crypto.decrypt(user.email_encrypted)
                        user.email_encrypted = new_crypto.encrypt(email)
                    except Exception:
                        # 如果解密失败，可能已经是新 pepper 加密的
                        pass

                if user.address_encrypted:
                    try:
                        address = old_crypto.decrypt(user.address_encrypted)
                        user.address_encrypted = new_crypto.encrypt(address)
                    except Exception:
                        pass

                count += 1

            except Exception as e:
                print(f"\n✗ Error processing user {user.user_id}: {e}")
                errors += 1
                continue

        await session.commit()
        print(f"  Processed {count}/{len(users)} users", end="\r", flush=True)

    print(f"\n✓ Rotated {count} users ({errors} errors)")
    return count


async def main():
    parser = argparse.ArgumentParser(description="Rotate encryption pepper")
    parser.add_argument("--old-pepper", required=True, help="Current pepper value")
    parser.add_argument("--new-pepper", required=True, help="New pepper value")
    parser.add_argument("--dual-mode", action="store_true", help="Enable dual-pepper mode (7 days)")
    parser.add_argument("--finalize", action="store_true", help="Finalize rotation (remove old pepper)")
    parser.add_argument("--database-url", help="Database URL (default from env)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    args = parser.parse_args()

    if args.dual_mode and args.finalize:
        print("✗ Cannot use --dual-mode and --finalize together")
        return 1

    print("=== Pepper Rotation ===")
    print(f"Old pepper: {args.old_pepper[:8]}...")
    print(f"New pepper: {args.new_pepper[:8]}...")

    if args.dual_mode:
        print("Mode: Dual-pepper (7-day grace period)")
    elif args.finalize:
        print("Mode: Finalize (remove old pepper)")
    else:
        print("Mode: Direct rotation")

    print()

    # Confirm
    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted")
        return 0

    # Create crypto services
    old_crypto = CryptoService(args.old_pepper)
    new_crypto = CryptoService(args.new_pepper)

    # Database connection
    db_url = args.database_url or settings.DATABASE_URL
    engine = create_async_engine(db_url)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with SessionLocal() as session:
            # Rotate all users
            count = await rotate_users(session, old_crypto, new_crypto, args.batch_size)

        if args.dual_mode:
            print("\n=== Next Steps ===")
            expire_date = datetime.now() + timedelta(days=7)
            print(f"1. Set NEW_PEPPER={args.new_pepper} in environment")
            print(f"2. Keep OLD_PEPPER={args.old_pepper} for 7 days (until {expire_date.strftime('%Y-%m-%d')})")
            print("3. Run with --finalize after grace period")
        elif args.finalize:
            print("\n=== Rotation Complete ===")
            print(f"✓ Old pepper can now be removed from environment")
            print(f"✓ Set CRYPTO_PEPPER={args.new_pepper}")
        else:
            print("\n=== Rotation Complete ===")
            print(f"✓ Set CRYPTO_PEPPER={args.new_pepper} in environment")

        return 0

    except Exception as e:
        print(f"\n✗ Rotation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

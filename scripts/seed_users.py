"""Seed Users Script"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from app.db.session import session_scope
from app.models.entities import User
from app.core.crypto import get_crypto


USERS = [
    {
        "phone": "13800000001",
        "role": "user",
        "name": "演示用户A"
    },
    {
        "phone": "13800000002",
        "role": "studio",
        "name": "工作室主"
    },
    {
        "phone": "13800000003",
        "role": "admin",
        "name": "平台管理员"
    }
]


async def seed_users():
    """Insert seed users"""
    crypto = get_crypto()

    async with session_scope() as session:
        for user_data in USERS:
            phone = user_data.pop("phone")
            user = User(
                phone_hash=crypto.hash_phone(phone),
                phone_encrypted=crypto.encrypt(phone),
                **user_data
            )
            session.add(user)
        print(f"Inserted {len(USERS)} users")


if __name__ == "__main__":
    asyncio.run(seed_users())

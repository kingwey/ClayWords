"""Seed Users Script"""

import asyncio
import sys
import os

# Add backend to path and set working directory
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from app.db.session import session_scope
from app.models.entities import User
from app.core.crypto import get_crypto


USERS = [
    {
        "phone": "13800000001",
        "name": "演示用户A"
    },
    {
        "phone": "13800000002",
        "name": "工作室主"
    },
    {
        "phone": "13800000003",
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
                phone_encrypted=crypto.encrypt(phone)
            )
            session.add(user)
        print(f"Inserted {len(USERS)} users")


if __name__ == "__main__":
    asyncio.run(seed_users())

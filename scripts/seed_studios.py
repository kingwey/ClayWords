"""Seed Studios Script"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from app.db.session import session_scope
from app.models.entities import Studio


STUDIOS = [
    {
        "name": "陶溪川王师傅",
        "location": "景德镇",
        "specialties": ["白瓷", "青花", "釉下彩"],
        "capacity": 15,
        "rating": 4.8,
        "price_range_min": 200,
        "price_range_max": 2000,
        "estimated_days": 10
    },
    {
        "name": "德化李师傅",
        "location": "德化",
        "specialties": ["白瓷", "茶具", "香插"],
        "capacity": 20,
        "rating": 4.6,
        "price_range_min": 150,
        "price_range_max": 1500,
        "estimated_days": 8
    },
    {
        "name": "宜兴赵师傅",
        "location": "宜兴",
        "specialties": ["紫砂", "茶宠", "花瓶"],
        "capacity": 12,
        "rating": 4.9,
        "price_range_min": 300,
        "price_range_max": 3000,
        "estimated_days": 14
    },
    {
        "name": "平台中央工作室",
        "location": "景德镇",
        "specialties": ["白瓷", "青瓷", "粗陶", "紫砂"],
        "capacity": 50,
        "rating": 4.5,
        "price_range_min": 100,
        "price_range_max": 5000,
        "estimated_days": 7
    }
]


async def seed_studios():
    """Insert seed studios"""
    async with session_scope() as session:
        for studio_data in STUDIOS:
            studio = Studio(**studio_data)
            session.add(studio)
        print(f"Inserted {len(STUDIOS)} studios")


if __name__ == "__main__":
    asyncio.run(seed_studios())

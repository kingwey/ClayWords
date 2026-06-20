"""Seed Design Templates Script"""

import asyncio
import sys
import os

# Add backend to path and set working directory
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from app.db.session import session_scope
from app.models.entities import DesignTemplate


TEMPLATES = [
    # Animals (10)
    {"name": "玉兔", "category": "animal", "description": "可爱的小兔子造型"},
    {"name": "金蟾", "category": "animal", "description": "招财金蟾摆件"},
    {"name": "貔貅", "category": "animal", "description": "招财进宝貔貅"},
    {"name": "麒麟", "category": "animal", "description": "祥瑞神兽麒麟"},
    {"name": "仙鹤", "category": "animal", "description": "松鹤延年仙鹤"},
    {"name": "锦鲤", "category": "animal", "description": "锦鲤跃龙门"},
    {"name": "青蛙", "category": "animal", "description": "荷叶青蛙茶宠"},
    {"name": "蜗牛", "category": "animal", "description": "卡通蜗牛摆件"},
    {"name": "蝴蝶", "category": "animal", "description": "翩翩起舞蝴蝶"},
    {"name": "螃蟹", "category": "animal", "description": "横行霸道螃蟹"},

    # Landscape (6)
    {"name": "山水", "category": "landscape", "description": "山水意象摆件"},
    {"name": "假山", "category": "landscape", "description": "微型假山盆景"},
    {"name": "枯山水", "category": "landscape", "description": "日式枯山水"},
    {"name": "松树", "category": "landscape", "description": "松树盆景"},
    {"name": "竹林", "category": "landscape", "description": "竹林七贤意境"},
    {"name": "荷塘", "category": "landscape", "description": "荷塘月色"},

    # Vessels (10)
    {"name": "花瓶", "category": "vessel", "description": "经典陶瓷花瓶"},
    {"name": "茶壶", "category": "vessel", "description": "功夫茶茶壶"},
    {"name": "茶杯", "category": "vessel", "description": "品茗茶杯"},
    {"name": "香插", "category": "vessel", "description": "线香香插"},
    {"name": "香炉", "category": "vessel", "description": "熏香香炉"},
    {"name": "灯罩", "category": "vessel", "description": "陶瓷灯罩"},
    {"name": "果盘", "category": "vessel", "description": "水果盘"},
    {"name": "花盆", "category": "vessel", "description": "多肉花盆"},
    {"name": "笔筒", "category": "vessel", "description": "书房笔筒"},
    {"name": "香薰瓶", "category": "vessel", "description": "空气清新瓶"},
    {"name": "储物罐", "category": "vessel", "description": "茶叶储物罐"},

    # Abstract (4)
    {"name": "漩涡", "category": "abstract", "description": "抽象漩涡造型"},
    {"name": "山形", "category": "abstract", "description": "几何山形"},
    {"name": "环形", "category": "abstract", "description": "莫比乌斯环"},
    {"name": "混沌", "category": "abstract", "description": "混沌初开"}
]


async def seed_templates():
    """Insert seed templates"""
    async with session_scope() as session:
        for tmpl_data in TEMPLATES:
            template = DesignTemplate(
                glb_url=f"templates/{tmpl_data['name']}.glb",
                thumbnail_url=f"thumbnails/{tmpl_data['name']}.png",
                default_params={"material": "porcelain_white"},
                **tmpl_data
            )
            session.add(template)
        print(f"Inserted {len(TEMPLATES)} templates")


if __name__ == "__main__":
    asyncio.run(seed_templates())

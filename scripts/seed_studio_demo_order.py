"""演示用：给 demo 工作室 (demo-studio-0001) 派发一条待接单订单。

完整链路：user(13800000001) → session → design → design_version → order(dispatched)
派单目标为 demo 工作室，登录 13800000002 即可在工作室端看到并走「接单 → 完成 → 发货」全流程。

前置：
  1. 数据库已迁移到 head（含 003_add_user_role）
  2. 至少用 13800000002 登录过一次（自动创建 demo-studio-0001）
  3. 至少用 13800000001 登录过一次（自动创建普通用户）

运行：python scripts/seed_studio_demo_order.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime

backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from sqlalchemy import select
from app.db.session import session_scope
from app.core.crypto import get_crypto
from app.models.entities import (
    User, Studio, Session as ChatSession, Design, DesignVersion, Order,
)

DEMO_STUDIO_ID = "demo-studio-0001"
DEMO_USER_PHONE = "13800000001"


async def seed():
    crypto = get_crypto()
    phone_hash = crypto.hash_phone(DEMO_USER_PHONE)

    async with session_scope() as session:
        # 1. 普通用户
        user = (await session.execute(
            select(User).where(User.phone_hash == phone_hash)
        )).scalar_one_or_none()
        if not user:
            print(f"[!] 未找到用户 {DEMO_USER_PHONE}，请先用该账号登录一次")
            return

        # 2. demo 工作室
        studio = (await session.execute(
            select(Studio).where(Studio.studio_id == DEMO_STUDIO_ID)
        )).scalar_one_or_none()
        if not studio:
            print(f"[!] 未找到工作室 {DEMO_STUDIO_ID}，请先用 13800000002 登录一次")
            return

        # 3. 会话
        chat = ChatSession(
            session_id=str(uuid.uuid4()),
            user_id=user.user_id,
            title="演示设计 · 玉兔捧月",
        )
        session.add(chat)
        await session.flush()

        # 4. 设计
        design = Design(
            design_id=str(uuid.uuid4()),
            session_id=chat.session_id,
            design_params={
                "shape": "兔子坐月",
                "glaze_color": "冷白釉",
                "size": "18cm",
                "style": "新中式",
                "material": "白瓷",
                "usage": "玄关摆件",
            },
        )
        session.add(design)
        await session.flush()

        # 5. 设计版本（订单 option_id 指向它）
        version = DesignVersion(
            version_id=str(uuid.uuid4()),
            design_id=design.design_id,
            version_no=1,
            option_no=1,
            pipeline="template",
            name="玉兔捧月",
            description="可爱的玉兔造型摆件，寓意吉祥如意。",
            glb_url="demos/yutuguan.glb",
            thumbnail_url="demos/yutuguan.png",
            craft_check_result={"passed": True, "issues": [], "auto_fixed": False},
            estimated_volume=320.0,
            estimated_weight=480.0,
            price=386.0,
            estimated_days=10,
        )
        session.add(version)
        await session.flush()

        # 6. 订单（dispatched，派给 demo 工作室）
        order = Order(
            order_id=str(uuid.uuid4()),
            user_id=user.user_id,
            session_id=chat.session_id,
            option_id=version.version_id,
            studio_id=DEMO_STUDIO_ID,
            status="dispatched",
            idempotency_key=f"demo-studio-order-{uuid.uuid4().hex[:8]}",
            shipping_name="陶语演示",
            shipping_phone="138****0001",
            shipping_address="北京市朝阳区某某街道 88 号",
            total_price=386.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(order)
        await session.flush()

        print("[OK] 已派发待接单订单到 demo 工作室")
        print(f"     order_id  = {order.order_id}")
        print(f"     studio_id = {DEMO_STUDIO_ID}")
        print(f"     status    = dispatched")
        print("     用 13800000002 登录工作室端即可看到并接单")


if __name__ == "__main__":
    asyncio.run(seed())

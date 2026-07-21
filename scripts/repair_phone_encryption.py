"""修复手机号密文 pepper 不一致问题

背景:
  历史上 CRYPTO_PEPPER 变更过, 导致旧 users.phone_encrypted 用旧 pepper 加密,
  当前 pepper 无法解密 (decrypt → InvalidTag), 前端个人资料"手机号"显示为空。

原理:
  phone_hash 是 SHA256(明文), 与 pepper 无关, 因此可用已知候选明文反查匹配,
  恢复明文后用当前 pepper 重新加密回写。无法匹配的 (非演示号) 只能跳过。

用法:
  python scripts/repair_phone_encryption.py            # dry-run, 只报告
  python scripts/repair_phone_encryption.py --apply    # 实际回写

安全:
  - 不打印完整手机号 (脱敏输出)
  - 仅在 decrypt 失败时才尝试修复, 不动正常数据
"""

import asyncio
import os
import sys

backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from sqlalchemy import select  # noqa: E402

from app.db.session import session_scope  # noqa: E402
from app.models.entities import User  # noqa: E402
from app.core.crypto import get_crypto  # noqa: E402


# 已知候选明文手机号 (演示账号 + 你的真实测试号可在此补充)
CANDIDATE_PHONES = [
    "13800000001",
    "13800000002",
    "13800000003",
]


def _mask(phone: str) -> str:
    return phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else "***"


async def repair(apply: bool) -> None:
    crypto = get_crypto()
    hash_to_phone = {crypto.hash_phone(p): p for p in CANDIDATE_PHONES}

    fixed = skipped = healthy = 0
    async with session_scope() as session:
        users = (await session.execute(select(User))).scalars().all()
        for user in users:
            # 先看当前 pepper 能否解密; 能就是健康数据, 不动
            try:
                crypto.decrypt(user.phone_encrypted)
                healthy += 1
                continue
            except Exception:
                pass

            # 解密失败 → 尝试用 phone_hash 反查明文
            phone = hash_to_phone.get(user.phone_hash)
            if not phone:
                print(f"  跳过 {user.user_id[:8]} (phone_hash 未匹配已知候选号码)")
                skipped += 1
                continue

            print(f"  修复 {user.user_id[:8]} -> {_mask(phone)}"
                  + ("" if apply else " (dry-run)"))
            if apply:
                user.phone_encrypted = crypto.encrypt(phone)
            fixed += 1

        if not apply:
            # session_scope 提交前回滚: dry-run 不写库
            await session.rollback()

    print(f"\n健康 {healthy} / 待修复 {fixed} / 无法修复 {skipped}")
    if not apply and fixed:
        print("这是 dry-run。加 --apply 实际回写。")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(repair(apply))

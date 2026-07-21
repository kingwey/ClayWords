"""
ClayWords · 演示视频录制脚本 v2

要点：
- viewport 1920x1080（无浏览器 chrome 干扰，效果等同全屏）
- 每个关键节点都 ensure_ready：等关键元素出现 + 等动画稳定，再走下一步
- 字幕浮层墨绿底 + 金箔边，与陶语视觉一致

前提：
    后端 http://127.0.0.1:8000  + 前端 http://127.0.0.1:5173 都在跑

输出：
    docs/videos/claywords-demo.webm   （≈ 75 秒，1920×1080）

用法：
    python scripts/record_demo.py
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT / "docs" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

FRONT = "http://127.0.0.1:5173"
WIDTH, HEIGHT = 1920, 1080


# ============================================================
#   工具函数
# ============================================================
async def caption(page: Page, text: str, ms: int = 0):
    """页面顶部居中浮一条字幕，ms>0 后自动消失"""
    await page.evaluate(
        """
        ([t, dur]) => {
          let cap = document.getElementById('__cw_caption');
          if (!cap) {
            cap = document.createElement('div');
            cap.id = '__cw_caption';
            cap.style.cssText = `
              position:fixed; top:32px; left:50%; transform:translateX(-50%);
              padding:18px 40px; background:rgba(45,74,72,0.95); color:#fff;
              font-family:"Songti SC","STSong","SimSun",serif;
              font-size:24px; letter-spacing:4px; font-weight:600;
              border-radius:999px; box-shadow:0 12px 32px rgba(0,0,0,0.3);
              z-index:99999; backdrop-filter:blur(8px);
              border:2px solid rgba(212,165,116,0.6);
              pointer-events:none;
            `;
            const sty = document.createElement('style');
            sty.textContent = `@keyframes capIn{from{opacity:0;transform:translate(-50%,-16px)}to{opacity:1;transform:translate(-50%,0)}}
              #__cw_caption.show{animation: capIn .4s ease both}`;
            document.head.appendChild(sty);
            document.body.appendChild(cap);
          }
          cap.textContent = t;
          cap.classList.remove('show');
          void cap.offsetWidth;
          cap.classList.add('show');
          cap.style.opacity = '1';
          if (dur > 0) {
            clearTimeout(window.__cw_cap_timer);
            window.__cw_cap_timer = setTimeout(() => {
              cap.style.transition = 'opacity .4s';
              cap.style.opacity = '0';
            }, dur);
          }
        }
        """,
        [text, ms],
    )


async def smooth_scroll(page: Page, y: int, ms: int = 800):
    await page.evaluate(
        """
        ({y, ms}) => new Promise(r => {
          const start = window.scrollY, delta = y - start, t0 = performance.now();
          const tick = (t) => {
            const k = Math.min(1, (t - t0) / ms);
            const e = 1 - Math.pow(1 - k, 3);
            window.scrollTo(0, start + delta * e);
            if (k < 1) requestAnimationFrame(tick); else r();
          };
          requestAnimationFrame(tick);
        })
        """,
        {"y": y, "ms": ms},
    )


async def ensure_ready(page: Page, selectors: list[str], timeout: int = 8000) -> bool:
    """等任意一个 selector 出现且可见，全部超时则返回 False（不抛）"""
    for sel in selectors:
        try:
            await page.wait_for_selector(sel, state="visible", timeout=timeout)
            return True
        except PWTimeout:
            continue
    return False


async def settle(page: Page, ms: int = 600):
    """等动画稳定 + 让 RAF 跑两轮"""
    await page.wait_for_timeout(ms)


# ============================================================
#   主流程
# ============================================================
async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=[
                f"--window-size={WIDTH},{HEIGHT}",
                "--window-position=0,0",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        context = await browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": WIDTH, "height": HEIGHT},
            locale="zh-CN",
            color_scheme="light",
        )
        page = await context.new_page()

        # ============================================================
        #   段 1 · Hero 首页（约 9 秒）
        # ============================================================
        await page.goto(f"{FRONT}/", wait_until="domcontentloaded")
        # 等 Hero 真正渲染：玉兔花瓶 SVG + 标题
        ok = await ensure_ready(page, [".hero-ceramic", ".hero-title", "h1"], timeout=10000)
        if not ok:
            print("WARN  hero not ready, fallback to fixed wait")
            await settle(page, 1500)
        # 让 SVG 浮动动画跑半个周期再开始
        await settle(page, 1200)

        await caption(page, "陶语 · 一句话烧出专属陶瓷", 4000)
        await settle(page, 2500)
        await caption(page, "AI 创造力大赛 · 生活娱乐 + 社会公益", 3500)
        await smooth_scroll(page, 480, 1100)
        await settle(page, 1600)
        await smooth_scroll(page, 0, 900)
        await settle(page, 1100)

        # ============================================================
        #   段 2 · 登录（约 6 秒）
        # ============================================================
        await caption(page, "演示账号一键登录", 3500)
        await settle(page, 700)

        await page.goto(f"{FRONT}/login", wait_until="domcontentloaded")
        # 等登录页关键元素：手机号输入框 OR 演示账号区
        await ensure_ready(
            page,
            [".demo-accounts", ".login-card", "input[placeholder*='手机']"],
            timeout=8000,
        )
        await settle(page, 1200)

        clicked = False
        # 兼容多种实现：按文案或按 class
        for sel in [
            "button:has-text('演示用户')",
            ".demo-account:has-text('演示用户')",
            "button:has-text('普通用户')",
            ".demo-account >> nth=0",
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click(timeout=2500)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # 兜底：手填
            try:
                await page.fill('input[placeholder*="手机"]', "13800000001")
                await settle(page, 300)
                await page.fill('input[placeholder*="验证码"]', "123456")
                await settle(page, 300)
                await page.click("button:has-text('登录')", timeout=2000)
            except Exception:
                pass

        await settle(page, 2000)

        # ============================================================
        #   段 3 · 对话式设计台 · 自动 demo（约 14 秒）
        # ============================================================
        await caption(page, "对话式设计台 · 三栏布局", 4000)
        # 等 DesignView 三栏出现
        await ensure_ready(
            page,
            [".chat-panel", ".options-panel", ".design-layout"],
            timeout=10000,
        )
        await settle(page, 1500)

        await caption(page, "AI 解析意图 → 并行 3 路线生成", 4000)
        # 等三方案卡片真正浮现（onMounted 1.5s 后才注入 prompt）
        await ensure_ready(page, [".option-card"], timeout=15000)
        await settle(page, 2500)

        await caption(page, "壁厚 · 悬臂 · 底面 · 收缩 · 工艺校验", 4000)
        await settle(page, 3000)

        # ============================================================
        #   段 4 · 选中方案 + 釉色切换（约 11 秒）
        # ============================================================
        await caption(page, "选中方案 → 6 釉色本地实时切换", 3500)
        await settle(page, 700)

        # 点第一张方案卡
        try:
            card = page.locator(".option-card").first
            if await card.count() > 0:
                await card.scroll_into_view_if_needed()
                await card.click(timeout=3000)
                await settle(page, 1300)
        except Exception:
            pass

        # 等 3D 预览或釉色面板就绪
        await ensure_ready(page, [".glaze-options", ".glaze-btn", ".preview-stage"], timeout=4000)
        await settle(page, 800)

        # 切 4 种釉色
        for g in ["青瓷釉", "胭脂红", "玉青釉", "天目釉"]:
            try:
                btn = page.locator(f".glaze-btn[title='{g}']").first
                if await btn.count() > 0:
                    await btn.click()
                    await settle(page, 1100)
            except Exception:
                pass

        await settle(page, 700)

        # ============================================================
        #   段 5 · 微调 + 版本树（约 11 秒）
        # ============================================================
        await caption(page, "自然语言微调 · 自动落版本", 3500)
        await settle(page, 600)

        # 点 2 个微调按钮
        for tweak in ["耳朵再长一点", "加入桂花纹理"]:
            try:
                tb = page.locator(f"button.tweak-chip:has-text('{tweak}')").first
                if await tb.count() > 0:
                    await tb.scroll_into_view_if_needed()
                    await tb.click()
                    await settle(page, 2000)
            except Exception:
                pass

        # 展开版本树
        await caption(page, "版本树 · 历史版本可回滚", 3000)
        try:
            vt = page.locator("button.version-toggle").first
            if await vt.count() > 0:
                await vt.scroll_into_view_if_needed()
                await vt.click()
                await settle(page, 2500)
        except Exception:
            pass

        # ============================================================
        #   段 6 · 派单可视化（约 10 秒）
        # ============================================================
        await caption(page, "智能派单 · 4 维加权评分", 4000)

        order_clicked = False
        for sel in [
            "button:has-text('确认方案')",
            "button.summary-cta",
            ".option-actions button:has-text('下单')",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(timeout=3000)
                    order_clicked = True
                    break
            except Exception:
                continue

        if order_clicked:
            # 等派单弹窗
            await ensure_ready(page, [".dispatch-dialog", ".dispatch-body"], timeout=5000)
            await settle(page, 3000)

        await caption(page, "陶溪川 · 林师傅 · 0.87 高分胜出", 3500)
        await settle(page, 2500)

        # 点"确认派单"
        try:
            confirm = page.locator("button:has-text('确认派单')").first
            if await confirm.count() == 0:
                confirm = page.locator(".dispatch-footer .el-button--primary").first
            if await confirm.count() > 0:
                await confirm.click(timeout=3000)
                await settle(page, 1800)
        except Exception:
            pass

        # ============================================================
        #   段 7 · 工单印章 + 接单 toast（约 8 秒）
        # ============================================================
        await caption(page, "工单印章 + 师傅已接单", 4000)
        # 等工单弹窗 + toast
        await ensure_ready(page, [".workorder-dialog", ".seal", ".studio-accept-toast"], timeout=4000)
        await settle(page, 4000)

        # ============================================================
        #   段 8 · 尾屏（约 4 秒）
        # ============================================================
        await caption(page, "陶语 ClayWords · 让手艺触手可及", 4000)
        await settle(page, 4000)

        # ============================================================
        #   收尾
        # ============================================================
        video_path = await page.video.path() if page.video else None
        await context.close()
        await browser.close()

        if video_path:
            src = Path(video_path)
            dst = VIDEO_DIR / "claywords-demo.webm"
            if src.exists():
                if dst.exists():
                    dst.unlink()
                shutil.move(str(src), str(dst))
                size_kb = dst.stat().st_size // 1024
                print(f"OK  video saved: {dst}  ({size_kb} KB · {WIDTH}x{HEIGHT})")
            else:
                print(f"WARN  expected video at {src} not found")


if __name__ == "__main__":
    asyncio.run(run())

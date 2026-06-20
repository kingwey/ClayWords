"""Work-order PDF generation.

优先用 weasyprint 渲染 PDF；环境无 weasyprint 时退化为可打印的 HTML。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from html import escape


# ============================================================
#   HTML 模板（与陶语视觉系统保持一致：墨绿主色 + 陶土橙强调）
# ============================================================
WORKORDER_CSS = """
@page { size: A4; margin: 18mm; }
body {
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", "PingFang SC", "Microsoft YaHei", serif;
  color: #2a2420;
  background: #faf6f0;
  line-height: 1.7;
  margin: 0;
  padding: 0;
}
.page { padding: 0; }
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 2px solid #2d4a48;
  padding-bottom: 16px;
  margin-bottom: 24px;
}
.brand {
  font-size: 28px;
  font-weight: 700;
  color: #2d4a48;
  letter-spacing: 6px;
}
.brand .accent { color: #c97b5a; }
.subtitle {
  font-size: 12px;
  color: #8a7d6f;
  letter-spacing: 4px;
  text-transform: uppercase;
}
h1 {
  font-size: 22px;
  font-weight: 700;
  color: #2d4a48;
  letter-spacing: 4px;
  margin: 0;
}
.meta {
  text-align: right;
  font-size: 12px;
  color: #6b5e4f;
  font-family: "JetBrains Mono", "Consolas", monospace;
}
.meta .num {
  color: #c97b5a;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 2px;
}
.section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 14px;
  color: #c97b5a;
  letter-spacing: 4px;
  text-transform: uppercase;
  border-bottom: 1px dashed #e5dccf;
  padding-bottom: 6px;
  margin-bottom: 12px;
}
.kv {
  display: grid;
  grid-template-columns: 110px 1fr;
  row-gap: 6px;
  column-gap: 12px;
  font-size: 13px;
}
.kv .k { color: #8a7d6f; }
.kv .v { color: #2a2420; font-weight: 600; }
.craft-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 24px;
  font-size: 13px;
}
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-left: 6px;
}
.badge.pass { background: #e6f0ea; color: #5b8a72; }
.badge.fail { background: #f9e1e1; color: #c75b5b; }
.badge.warn { background: #fbe8d7; color: #c97b5a; }
.glb-link {
  display: inline-block;
  background: #fff;
  border: 1px solid #e5dccf;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 12px;
  color: #2d4a48;
  font-family: "JetBrains Mono", monospace;
  word-break: break-all;
}
.thumb {
  width: 180px;
  height: 180px;
  border: 1px solid #e5dccf;
  border-radius: 12px;
  background: #fffdf9 url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"><text x="100" y="105" text-anchor="middle" font-family="Songti SC" font-size="22" fill="%232d4a48" letter-spacing="4">陶语 · 预览</text></svg>') center/cover no-repeat;
  display: inline-block;
}
.address-block {
  background: #fffdf9;
  border-left: 3px solid #c97b5a;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 13px;
}
.params-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.params-table th, .params-table td {
  border: 1px solid #e5dccf;
  padding: 8px 10px;
  text-align: left;
}
.params-table th {
  background: #f3ebe0;
  color: #2d4a48;
  letter-spacing: 1px;
  font-weight: 600;
}
.footer {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 1px solid #e5dccf;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #a89a8a;
  font-family: "JetBrains Mono", monospace;
  letter-spacing: 1px;
}
.seal {
  position: relative;
  width: 90px;
  height: 90px;
  border: 3px solid #c75b5b;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #c75b5b;
  font-family: "Songti SC", serif;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 4px;
  transform: rotate(-12deg);
  opacity: 0.85;
  margin-left: auto;
}
"""


def _badge(passed: bool, auto_fixed: bool) -> str:
    if passed and not auto_fixed:
        return '<span class="badge pass">校验通过</span>'
    if passed and auto_fixed:
        return '<span class="badge warn">已自动修复</span>'
    return '<span class="badge fail">需复核</span>'


def _kv_row(k: str, v: Any) -> str:
    return f'<div class="k">{escape(k)}</div><div class="v">{escape(str(v))}</div>'


def generate_workorder_html(workorder: dict) -> str:
    """
    根据工单数据生成 HTML。

    workorder dict 期望字段：
        order_id, design_name, studio_name, studio_master, deadline,
        glb_url, thumbnail_url, craft_check (dict), design_params (dict),
        price, estimated_days, material, dimensions_mm,
        ship_to (dict: name, phone, address)
    """
    order_id = workorder.get("order_id", "—")
    design_name = workorder.get("design_name", "—")
    studio_name = workorder.get("studio_name", "—")
    studio_master = workorder.get("studio_master", "—")
    deadline = workorder.get("deadline", "—")
    glb_url = workorder.get("glb_url", "—")
    craft_check = workorder.get("craft_check") or {}
    passed = bool(craft_check.get("passed", False))
    auto_fixed = bool(craft_check.get("auto_fixed", False))
    issues = craft_check.get("issues") or []
    design_params = workorder.get("design_params") or {}
    price = workorder.get("price", 0)
    estimated_days = workorder.get("estimated_days", "—")
    material = workorder.get("material", "porcelain_white")
    dimensions = workorder.get("dimensions_mm") or {}
    ship_to = workorder.get("ship_to") or {}

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    issues_html = (
        "<ul style='margin:6px 0 0 18px;'>"
        + "".join(f"<li>{escape(str(i))}</li>" for i in issues)
        + "</ul>"
        if issues
        else "<span style='color:#5b8a72;'>无遗留 issue</span>"
    )

    params_rows = "".join(
        f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>"
        for k, v in design_params.items()
    ) or "<tr><td colspan='2' style='color:#a89a8a;'>无</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>陶语工单 · {escape(str(order_id))}</title>
<style>{WORKORDER_CSS}</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div>
      <div class="brand">陶<span class="accent">语</span></div>
      <div class="subtitle">CLAYWORDS WORK ORDER</div>
    </div>
    <div class="meta">
      <div>工单编号</div>
      <div class="num">{escape(str(order_id))}</div>
      <div style="margin-top:6px;">{now}</div>
    </div>
  </div>

  <h1>制作工单 · {escape(str(design_name))}</h1>

  <div class="section">
    <div class="section-title">承制信息</div>
    <div class="kv">
      {_kv_row("工作室", studio_name)}
      {_kv_row("责任师傅", studio_master)}
      {_kv_row("交付日期", f"{deadline}（约 {estimated_days} 天）")}
      {_kv_row("订单金额", f"¥ {price}")}
    </div>
  </div>

  <div class="section">
    <div class="section-title">作品规格</div>
    <div style="display:flex; gap:24px;">
      <div class="thumb"></div>
      <div style="flex:1;">
        <div class="kv">
          {_kv_row("作品名称", design_name)}
          {_kv_row("材质", material)}
          {_kv_row("尺寸 (高×宽×深) mm", f"{dimensions.get('height','—')} × {dimensions.get('width','—')} × {dimensions.get('depth','—')}")}
          {_kv_row("3D 模型", "")}
        </div>
        <div class="glb-link">{escape(str(glb_url))}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">工艺校验 {_badge(passed, auto_fixed)}</div>
    <div class="craft-grid">
      <div><b>状态：</b>{"通过" if passed else "未通过"}</div>
      <div><b>自动修复：</b>{"是" if auto_fixed else "否"}</div>
      <div style="grid-column:1/-1;"><b>遗留 issue：</b>{issues_html}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">设计参数包</div>
    <table class="params-table">
      <thead>
        <tr><th style="width:30%;">字段</th><th>值</th></tr>
      </thead>
      <tbody>
        {params_rows}
      </tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">收货地址</div>
    <div class="address-block">
      <b>{escape(str(ship_to.get("name", "—")))}</b> · {escape(str(ship_to.get("phone", "—")))}<br/>
      {escape(str(ship_to.get("address", "—")))}
    </div>
  </div>

  <div class="seal">陶语已派</div>

  <div class="footer">
    <div>本工单由陶语 ClayWords 平台自动生成</div>
    <div>© {datetime.now().year} 陶语 · 让手艺触手可及</div>
  </div>
</div>
</body>
</html>
"""
    return html


def render_workorder_pdf(workorder: dict) -> bytes:
    """
    渲染工单为 PDF。

    优先使用 weasyprint；如果环境不可用，退化返回 HTML 字节流（前端可直接打印）。
    返回 bytes，调用方负责写入磁盘 / MinIO。
    """
    html = generate_workorder_html(workorder)
    try:
        # weasyprint 在部分 Windows 环境装不上，做软依赖
        from weasyprint import HTML  # type: ignore

        return HTML(string=html).write_pdf()
    except Exception:  # pragma: no cover - fallback path
        return html.encode("utf-8")

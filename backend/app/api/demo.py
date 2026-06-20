"""Demo Mode API Router"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.services.demo import get_demo_service, DEMO_CASES

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoDesignResponse(BaseModel):
    design_id: str
    name: str
    description: str
    glb_url: str
    thumbnail_url: str
    craft_score: float
    price: int
    estimated_days: int
    material: str
    category: str
    tags: list[str]


class DemoStatusResponse(BaseModel):
    enabled: bool
    offline_mode: bool
    cases_count: int


@router.get("/status", response_model=DemoStatusResponse)
async def get_demo_status():
    """Get demo mode status"""
    service = get_demo_service()
    return DemoStatusResponse(
        enabled=service.enabled,
        offline_mode=service.offline_mode,
        cases_count=len(DEMO_CASES)
    )


@router.post("/enable")
async def enable_demo(offline: bool = False):
    """Enable demo mode"""
    service = get_demo_service()
    service.enable(offline=offline)
    return {"message": "Demo mode enabled", "offline": offline}


@router.post("/disable")
async def disable_demo():
    """Disable demo mode"""
    service = get_demo_service()
    service.disable()
    return {"message": "Demo mode disabled"}


@router.get("/cases", response_model=list[DemoDesignResponse])
async def list_demo_cases():
    """List all demo cases"""
    return DEMO_CASES


@router.get("/similar", response_model=DemoDesignResponse)
async def find_similar_case(
    q: str = Query(..., description="User input to match")
):
    """Find a demo case similar to user input"""
    service = get_demo_service()
    case = service.find_similar_case(q)
    
    if not case:
        return {"error": "No matching case found"}
    
    return case


@router.post("/parse-params")
async def mock_parse_params(user_input: str):
    """Mock design parameter parsing for demo"""
    service = get_demo_service()
    params = await service.mock_parse_design_params(user_input)
    return params


# ============================================================
#   P8.1.3 · 降级演示开关
#   评委按下后下一次生成强制 B 路线失败 → 降级 A
# ============================================================
_DEGRADE_FLAG = {"on": False}


@router.post("/degrade")
async def trigger_degrade(on: bool = True):
    """
    模拟 GPU 故障：开启后，生成式路线 (B) 一律失败，强制降级到模板路线 (A)。

    评委按下后立刻见效，前端会显示「GPU 路线降级」提示。
    """
    _DEGRADE_FLAG["on"] = bool(on)
    return {"degrade": _DEGRADE_FLAG["on"]}


@router.get("/degrade")
async def get_degrade_status():
    return {"degrade": _DEGRADE_FLAG["on"]}


def is_degrade_on() -> bool:
    """供 worker / pipeline 查询"""
    return _DEGRADE_FLAG["on"]

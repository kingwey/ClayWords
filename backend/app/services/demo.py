"""Demo Mode Service - Pre-generated case pool and offline fallback"""

import random
from typing import Optional, Protocol
from dataclasses import dataclass


@dataclass
class DemoDesign:
    """Pre-generated design for demo mode"""
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


# Pre-generated demo cases
DEMO_CASES: list[DemoDesign] = [
    DemoDesign(
        design_id="demo-001",
        name="玉兔捧月",
        description="可爱的玉兔造型花瓶，寓意吉祥如意。适用于家居装饰或送礼。",
        glb_url="demos/yutuguan.glb",
        thumbnail_url="demos/yutuguan.png",
        craft_score=0.95,
        price=888,
        estimated_days=10,
        material="porcelain_white",
        category="animal",
        tags=["兔子", "花瓶", "吉祥"]
    ),
    DemoDesign(
        design_id="demo-002",
        name="月形花瓶",
        description="弯月形状的青瓷花瓶，线条优美流畅，富有诗意。",
        glb_url="demos/yuexing.glb",
        thumbnail_url="demos/yuexing.png",
        craft_score=0.92,
        price=1280,
        estimated_days=14,
        material="celadon",
        category="vessel",
        tags=["月亮", "花瓶", "青瓷"]
    ),
    DemoDesign(
        design_id="demo-003",
        name="三孔香插",
        description="三孔设计的香炉，造型独特雅致，适合品茶赏香。",
        glb_url="demos/sankong.glb",
        thumbnail_url="demos/sankong.png",
        craft_score=0.98,
        price=680,
        estimated_days=7,
        material="purple_clay",
        category="vessel",
        tags=["香炉", "茶具", "雅致"]
    ),
    DemoDesign(
        design_id="demo-004",
        name="怀宠橘猫",
        description="慵懒的橘猫摆件，憨态可掬惹人爱，深受年轻人喜爱。",
        glb_url="demos/jumao.glb",
        thumbnail_url="demos/jumao.png",
        craft_score=0.88,
        price=1580,
        estimated_days=14,
        material="porcelain_white",
        category="animal",
        tags=["猫咪", "摆件", "可爱"]
    ),
    DemoDesign(
        design_id="demo-005",
        name="山水意境茶盘",
        description="以山水画为灵感的茶盘，边缘微卷，底部留白，意境深远。",
        glb_url="demos/shanshui.glb",
        thumbnail_url="demos/shanshui.png",
        craft_score=0.94,
        price=1880,
        estimated_days=12,
        material="celadon",
        category="landscape",
        tags=["茶盘", "山水", "意境"]
    ),
]


class MockLLMClient(Protocol):
    """Protocol for mock LLM client in demo mode"""
    async def parse_design_params(self, user_input: str) -> dict:
        ...


class DemoModeService:
    """
    Demo mode service for offline/演示 scenarios.
    
    Provides:
    - Pre-generated case pool for quick responses
    - Mock LLM parsing for offline demo
    - Fallback designs when external services unavailable
    """
    
    def __init__(self):
        self._enabled = False
        self._offline_mode = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @property
    def offline_mode(self) -> bool:
        return self._offline_mode
    
    def enable(self, offline: bool = False):
        """Enable demo mode"""
        self._enabled = True
        self._offline_mode = offline
    
    def disable(self):
        """Disable demo mode"""
        self._enabled = False
        self._offline_mode = False
    
    def find_similar_case(self, user_input: str) -> Optional[DemoDesign]:
        """
        Find the most similar demo case based on user input keywords.
        
        In production, would use embedding similarity search.
        For demo, uses simple keyword matching.
        """
        if not self._enabled:
            return None
        
        # Keywords to case mapping
        keyword_map = {
            "玉兔": "demo-001",
            "兔子": "demo-001",
            "月亮": "demo-002",
            "月形": "demo-002",
            "青瓷": "demo-002",
            "香插": "demo-003",
            "香炉": "demo-003",
            "猫": "demo-004",
            "橘猫": "demo-004",
            "山水": "demo-005",
            "茶盘": "demo-005"
        }
        
        input_lower = user_input.lower()
        for keyword, case_id in keyword_map.items():
            if keyword in input_lower:
                return next((c for c in DEMO_CASES if c.design_id == case_id), None)
        
        # Random fallback
        return random.choice(DEMO_CASES) if DEMO_CASES else None
    
    def get_demo_cases(self) -> list[DemoDesign]:
        """Get all demo cases"""
        return DEMO_CASES
    
    async def mock_parse_design_params(self, user_input: str) -> dict:
        """
        Mock design parameter parsing for offline demo.
        
        Returns realistic design parameters without calling LLM.
        """
        # Simple keyword-based extraction
        result = {
            "shape": "vessel",
            "glaze_color": "celadon",
            "size": "medium",
            "style": "modern",
            "emotion": "peaceful",
            "material": "porcelain",
            "usage": "decorative"
        }
        
        input_lower = user_input.lower()
        
        # Shape detection
        shape_keywords = {
            "花瓶": "vessel",
            "摆件": "figurine",
            "茶宠": "teapot_accessory",
            "香炉": "incense_burner",
            "茶盘": "tea_tray",
            "碗": "bowl",
            "杯": "cup"
        }
        for keyword, shape in shape_keywords.items():
            if keyword in input_lower:
                result["shape"] = shape
                break
        
        # Material detection
        material_keywords = {
            "白瓷": "porcelain_white",
            "青瓷": "celadon",
            "紫砂": "purple_clay",
            "粗陶": "stoneware",
            "骨质瓷": "bone_china"
        }
        for keyword, material in material_keywords.items():
            if keyword in input_lower:
                result["material"] = material
                result["glaze_color"] = material.replace("porcelain_", "").replace("_", " ")
                break
        
        # Style detection
        if any(kw in input_lower for kw in ["简约", "简单", "现代"]):
            result["style"] = "modern"
        elif any(kw in input_lower for kw in ["传统", "古典", "中式"]):
            result["style"] = "traditional"
        elif any(kw in input_lower for kw in ["可爱", "萌"]):
            result["style"] = "cute"
        
        # Size detection
        if any(kw in input_lower for kw in ["大", "大号", "大型"]):
            result["size"] = "large"
        elif any(kw in input_lower for kw in ["小", "小号", "迷你"]):
            result["size"] = "small"
        
        return result


# Global singleton
_demo_service = DemoModeService()


def get_demo_service() -> DemoModeService:
    return _demo_service

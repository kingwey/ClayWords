"""Ceramic Craft Validation Rules"""

from pydantic import BaseModel
from typing import Literal


class CraftRules(BaseModel):
    """Craft validation rules for a specific material"""
    min_wall_thickness_mm: float
    max_height_mm: float
    max_overhang_deg: float
    min_base_ratio: float
    shrinkage_factor: float
    max_aspect_ratio: float


# Default craft rules by material
CRAFT_RULES: dict[str, CraftRules] = {
    "porcelain_white": CraftRules(
        min_wall_thickness_mm=3.0,
        max_height_mm=400,
        max_overhang_deg=30,
        min_base_ratio=0.15,
        shrinkage_factor=1.18,
        max_aspect_ratio=4.0
    ),
    "porcelain_celadon": CraftRules(
        min_wall_thickness_mm=3.5,
        max_height_mm=350,
        max_overhang_deg=30,
        min_base_ratio=0.15,
        shrinkage_factor=1.15,
        max_aspect_ratio=4.0
    ),
    "zisha": CraftRules(
        min_wall_thickness_mm=2.5,
        max_height_mm=300,
        max_overhang_deg=35,
        min_base_ratio=0.18,
        shrinkage_factor=1.08,
        max_aspect_ratio=3.5
    ),
    "stoneware_coarse": CraftRules(
        min_wall_thickness_mm=4.0,
        max_height_mm=500,
        max_overhang_deg=40,
        min_base_ratio=0.20,
        shrinkage_factor=1.10,
        max_aspect_ratio=3.0
    )
}


def get_craft_rules(material: str, studio_overrides: dict | None = None) -> CraftRules:
    """Get craft rules for material, with optional studio overrides"""
    rules = CRAFT_RULES.get(material, CRAFT_RULES["porcelain_white"])

    if studio_overrides:
        # Apply studio-specific overrides
        return CraftRules(
            min_wall_thickness_mm=studio_overrides.get("min_wall_thickness_mm", rules.min_wall_thickness_mm),
            max_height_mm=studio_overrides.get("max_height_mm", rules.max_height_mm),
            max_overhang_deg=studio_overrides.get("max_overhang_deg", rules.max_overhang_deg),
            min_base_ratio=studio_overrides.get("min_base_ratio", rules.min_base_ratio),
            shrinkage_factor=studio_overrides.get("shrinkage_factor", rules.shrinkage_factor),
            max_aspect_ratio=studio_overrides.get("max_aspect_ratio", rules.max_aspect_ratio)
        )

    return rules

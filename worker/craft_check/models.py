"""Craft Check Result Models"""

from pydantic import BaseModel
from typing import Literal


class CraftCheckResult(BaseModel):
    """Result of craft validation"""
    passed: bool
    issues: list[str]
    auto_fixed: bool = False
    fixed_mesh_uri: str | None = None


class WallThicknessResult(BaseModel):
    """Wall thickness check result"""
    passed: bool
    min_thickness_mm: float
    location: str | None = None


class OverhangResult(BaseModel):
    """Overhang check result"""
    passed: bool
    max_angle_deg: float
    locations: list[str] = []


class BaseStabilityResult(BaseModel):
    """Base stability check result"""
    passed: bool
    base_ratio: float
    center_of_mass_z: float | None = None


class AspectRatioResult(BaseModel):
    """Aspect ratio check result"""
    passed: bool
    ratio: float

"""Dispatch Scoring Service - Four-dimensional weighted scoring"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class DesignParams:
    """Design parameters for scoring"""
    material: str
    category: str
    price_range: tuple[float, float]  # (min, max)
    special_requirements: list[str] = None


@dataclass
class StudioInfo:
    """Studio information for scoring"""
    studio_id: str
    name: str
    specialties: list[str]
    capacity: int
    current_load: int
    rating: float
    price_range_min: float
    price_range_max: float
    estimated_days: int
    location: str


@dataclass
class ScoreBreakdown:
    """Detailed score breakdown"""
    craft_score: float      # 工艺匹配度 0-1
    capacity_score: float   # 产能可用度 0-1
    geo_score: float        # 地理位置 0-1
    rating_score: float     # 评分 0-1
    total: float


# Weights for scoring (sum = 1.0)
DEFAULT_WEIGHTS = {
    "craft": 0.35,      # 工艺匹配最重要
    "capacity": 0.25,   # 产能可用
    "geo": 0.15,       # 地理位置
    "rating": 0.25     # 评分
}

# Hard constraints thresholds
MIN_RATING_THRESHOLD = 4.0
MIN_CAPACITY_THRESHOLD = 0  # 工作室有空位即可


def calc_craft_score(params: DesignParams, studio: StudioInfo) -> float:
    """
    Calculate craft/specialty matching score.
    
    工艺匹配度：检查工作室专长是否匹配设计需求
    - 完全匹配: 1.0
    - 部分匹配: 0.6
    - 无匹配: 0.0
    """
    if not studio.specialties:
        return 0.3
    
    # Normalize specialties
    design_materials = {params.material.lower()}
    if params.category:
        design_materials.add(params.category.lower())
    
    matched = 0
    for specialty in studio.specialties:
        specialty_lower = specialty.lower()
        for material in design_materials:
            if material in specialty_lower or specialty_lower in material:
                matched += 1
    
    if matched >= 2:
        return 1.0
    elif matched == 1:
        return 0.7
    else:
        # Check for generic matches (白瓷, 青瓷, etc.)
        generic_materials = {"白瓷", "青瓷", "紫砂", "粗陶"}
        for material in design_materials:
            if material in generic_materials:
                for specialty in studio.specialties:
                    if any(g in specialty.lower() for g in generic_materials if g != material):
                        return 0.5
        return 0.2


def calc_capacity_score(studio: StudioInfo, min_required: int = 1) -> float:
    """
    Calculate capacity availability score.
    
    产能可用度：剩余产能占总产能的比例
    """
    if studio.capacity == 0:
        return 0.0
    
    available = studio.capacity - studio.current_load
    if available <= 0:
        return 0.0
    
    # Score based on how much capacity is available
    ratio = available / studio.capacity
    
    # Prefer studios with moderate load (not too busy, not too idle)
    if 0.3 <= ratio <= 0.8:
        return ratio
    elif ratio > 0.8:
        return 0.9  # Very available but might be underutilized
    else:
        return ratio * 0.7  # Tight capacity


def calc_geo_score(studio_location: str, target_locations: list[str] = None) -> float:
    """
    Calculate geographic score.
    
    地理位置评分：
    - 相同城市: 1.0
    - 相同省份: 0.7
    - 其他: 0.5
    """
    if not target_locations:
        return 0.8  # Default score if no preference
    
    studio_lower = studio_location.lower()
    
    # City match
    for target in target_locations:
        if studio_lower == target.lower():
            return 1.0
        # Province match (simplified - check if target is contained)
        if target.lower() in studio_lower or studio_lower in target.lower():
            return 0.8
    
    # Default
    return 0.5


def calc_rating_score(studio: StudioInfo, min_threshold: float = MIN_RATING_THRESHOLD) -> float:
    """
    Calculate rating score.
    
    评分：将4.0-5.0映射到0-1
    """
    if studio.rating < min_threshold:
        return 0.0  # Hard constraint failure
    
    # Linear mapping: 4.0 -> 0.0, 5.0 -> 1.0
    return (studio.rating - min_threshold) / (5.0 - min_threshold)


def calc_price_alignment(params: DesignParams, studio: StudioInfo) -> float:
    """
    Calculate price range alignment.
    
    价格区间匹配：设计预算与工作室定价范围的匹配度
    """
    budget_min, budget_max = params.price_range
    
    # If budget is within studio range
    if studio.price_range_min <= budget_max and studio.price_range_max >= budget_min:
        overlap_min = max(budget_min, studio.price_range_min)
        overlap_max = min(budget_max, studio.price_range_max)
        overlap = overlap_max - overlap_min
        
        budget_range = budget_max - budget_min
        studio_range = studio.price_range_max - studio.price_range_min
        
        # Calculate how much of the budget fits in studio range
        if budget_range > 0:
            alignment = overlap / budget_range
        else:
            alignment = 1.0
        
        return min(alignment * 1.2, 1.0)  # Boost slightly
    
    # Budget outside range
    distance = 0.0
    if budget_max < studio.price_range_min:
        distance = studio.price_range_min - budget_max
    elif budget_min > studio.price_range_max:
        distance = budget_min - studio.price_range_max
    
    # Exponential decay
    return max(0.1, 1.0 - distance / 1000)


def score_studio(
    studio: StudioInfo,
    params: DesignParams,
    weights: dict = DEFAULT_WEIGHTS,
    target_locations: list[str] = None
) -> ScoreBreakdown:
    """
    Calculate total score for a studio given design parameters.
    
    Returns ScoreBreakdown with individual and total scores.
    """
    # Check hard constraints first
    if studio.rating < MIN_RATING_THRESHOLD:
        return ScoreBreakdown(0, 0, 0, 0, 0)
    
    if studio.capacity - studio.current_load <= 0:
        return ScoreBreakdown(0, 0, 0, 0, 0)
    
    craft = calc_craft_score(params, studio)
    capacity = calc_capacity_score(studio)
    geo = calc_geo_score(studio.location, target_locations)
    rating = calc_rating_score(studio)
    
    # Calculate total weighted score
    total = (
        craft * weights.get("craft", 0.35) +
        capacity * weights.get("capacity", 0.25) +
        geo * weights.get("geo", 0.15) +
        rating * weights.get("rating", 0.25)
    )
    
    return ScoreBreakdown(
        craft_score=round(craft, 3),
        capacity_score=round(capacity, 3),
        geo_score=round(geo, 3),
        rating_score=round(rating, 3),
        total=round(total, 3)
    )


def rank_studios(
    studios: list[StudioInfo],
    params: DesignParams,
    weights: dict = None,
    target_locations: list[str] = None
) -> list[tuple[StudioInfo, ScoreBreakdown]]:
    """
    Rank studios by total score (descending).

    Returns list of (studio, score_breakdown) tuples.
    """
    # 兼容 weights=None：内部 score_studio 期望非 None dict
    effective_weights = weights if weights is not None else DEFAULT_WEIGHTS
    scored = []
    for studio in studios:
        breakdown = score_studio(studio, params, effective_weights, target_locations)
        if breakdown.total > 0:  # Only include studios passing hard constraints
            scored.append((studio, breakdown))
    
    # Sort by total score (descending), then by rating (descending) as tie-breaker
    scored.sort(
        key=lambda x: (x[1].total, x[0].rating),
        reverse=True
    )
    
    return scored

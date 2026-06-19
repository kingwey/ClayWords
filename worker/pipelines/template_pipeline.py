"""Template-based Design Pipeline (Route A)"""

import uuid
from typing import Optional
import numpy as np

from ..craft_check.pipeline import craft_check_pipeline
from ..craft_check.shrinkage import apply_shrinkage_compensation


class TemplatePipelineResult:
    """Result from template pipeline"""

    def __init__(
        self,
        option_id: str,
        name: str,
        description: str,
        glb_url: str,
        thumbnail_url: str,
        craft_check_result: dict,
        estimated_volume: float,
        estimated_weight: float,
        price: float,
        estimated_days: int
    ):
        self.option_id = option_id
        self.name = name
        self.description = description
        self.glb_url = glb_url
        self.thumbnail_url = thumbnail_url
        self.craft_check_result = craft_check_result
        self.estimated_volume = estimated_volume
        self.estimated_weight = estimated_weight
        self.price = price
        self.estimated_days = estimated_days


def template_pipeline(
    template_id: str,
    design_params: dict,
    material: str = "porcelain_white",
    height_mm: Optional[float] = None,
    width_mm: Optional[float] = None
) -> TemplatePipelineResult:
    """
    Route A: Template-based design generation.

    Takes a base template and applies parameter deformations.

    Args:
        template_id: ID of base template to use
        design_params: Design parameters from LLM parser
        material: Material type
        height_mm: Optional height override
        width_mm: Optional width override

    Returns:
        TemplatePipelineResult with generated option
    """
    # Get template metadata (would fetch from database in production)
    template_name = f"template_{template_id}"

    # Mock parameter deformation
    # In production would use actual mesh deformation
    target_height = height_mm or 180.0
    target_width = width_mm or 100.0

    # Create mock mesh vertices (simplified)
    vertices = np.array([
        [-target_width/2, -target_height/2, 0],
        [target_width/2, -target_height/2, 0],
        [target_width/2, target_height/2, 0],
        [-target_width/2, target_height/2, 0],
        [0, 0, target_width/2]  # Peak
    ], dtype=np.float32)

    faces = np.array([
        [0, 1, 4],
        [1, 2, 4],
        [2, 3, 4],
        [3, 0, 4]
    ], dtype=np.int32)

    # Apply shrinkage compensation
    from ..craft_check.rules import get_craft_rules
    rules = get_craft_rules(material)
    vertices_flat = vertices.flatten().tolist()
    compensated = apply_shrinkage_compensation(vertices_flat, rules.shrinkage_factor)

    # Run craft check
    craft_result = craft_check_pipeline(
        vertices,
        faces,
        material=material,
        dimensions_mm=(target_height, target_width, target_width)
    )

    # Calculate pricing
    volume = target_height * target_width * target_width / 1000  # Simplified
    weight = volume * 2.5  # ~2.5g/cm3 for ceramic
    price = max(99, volume * 0.5 + weight * 0.3)

    return TemplatePipelineResult(
        option_id=str(uuid.uuid4()),
        name=design_params.get("shape", template_name),
        description=f"基于模板{template_id}的参数化设计",
        glb_url=f"designs/{str(uuid.uuid4())}.glb",
        thumbnail_url=f"thumbnails/{str(uuid.uuid4())}.png",
        craft_check_result=craft_result.model_dump(),
        estimated_volume=volume,
        estimated_weight=weight,
        price=price,
        estimated_days=7
    )

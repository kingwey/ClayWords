"""Hybrid Design Pipeline (Route C)"""

import uuid
from typing import Optional

from .template_pipeline import template_pipeline
from .generative_pipeline import generative_pipeline


class HybridPipelineResult:
    """Result from hybrid pipeline"""

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


def hybrid_pipeline(
    template_id: str,
    design_params: dict,
    material: str = "porcelain_white"
) -> tuple[Optional[HybridPipelineResult], Optional[str]]:
    """
    Route C: Hybrid template + generative design.

    Uses template as base and applies generative details.

    Args:
        template_id: Base template ID
        design_params: Design parameters from LLM parser
        material: Material type

    Returns:
        (result, error or None)
    """
    # First, get base mesh from template
    template_result = template_pipeline(template_id, design_params, material)

    # Then generate detail mesh
    detail_params = design_params.copy()
    detail_result, error = generative_pipeline(detail_params, material)

    if error:
        # Fallback to template only
        return None, f"Hybrid failed, falling back: {error}"

    # In production would perform boolean operations to combine meshes
    # For now, just use the template result with modified description

    return HybridPipelineResult(
        option_id=str(uuid.uuid4()),
        name=template_result.name,
        description=f"混合设计 - 模板{template_id} + AI细节",
        glb_url=template_result.glb_url,
        thumbnail_url=template_result.thumbnail_url,
        craft_check_result=template_result.craft_check_result,
        estimated_volume=template_result.estimated_volume,
        estimated_weight=template_result.estimated_weight,
        price=template_result.price * 1.2,  # Hybrid costs more
        estimated_days=template_result.estimated_days + 2
    ), None

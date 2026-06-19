"""Generative Design Pipeline (Route B)"""

import uuid
from typing import Optional

from ..craft_check.pipeline import craft_check_pipeline


class GenerativePipelineResult:
    """Result from generative pipeline"""

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


def rewrite_prompt(design_params: dict) -> str:
    """
    Rewrite design params into model-friendly English prompt.

    Args:
        design_params: Design parameters from LLM parser

    Returns:
        English prompt suitable for text-to-3D model
    """
    parts = []

    if design_params.get("shape"):
        parts.append(f"a ceramic {design_params['shape']}")
    if design_params.get("style"):
        parts.append(f"in {design_params['style']} style")
    if design_params.get("glaze_color"):
        parts.append(f"with {design_params['glaze_color']} glaze")

    prompt = " ".join(parts)
    prompt += ", smooth surface, suitable for kiln firing, high detail"

    return prompt


def generative_pipeline(
    design_params: dict,
    material: str = "porcelain_white",
    max_retries: int = 2
) -> tuple[GenerativePipelineResult, Optional[str]]:
    """
    Route B: Generative text-to-3D design.

    Uses text-to-3D model to generate mesh, then validates.

    Args:
        design_params: Design parameters from LLM parser
        material: Material type
        max_retries: Maximum retry attempts on craft failure

    Returns:
        (result, fallback_error or None)
    """
    # Rewrite prompt for text-to-3D model
    prompt = rewrite_prompt(design_params)

    # Mock text-to-3D generation
    # In production would call actual model (Hunyuan3D-2, Trellis, etc.)
    vertices, faces = _mock_text_to_3d(prompt)

    # Check dimensions from generated mesh
    if vertices is not None and len(vertices) > 0:
        import numpy as np
        height = float(np.max(vertices[:, 1]) - np.min(vertices[:, 1]))
        width = float(np.max(vertices[:, 0]) - np.min(vertices[:, 0]))
        depth = float(np.max(vertices[:, 2]) - np.min(vertices[:, 2]))
        dimensions_mm = (height, width, depth)
    else:
        dimensions_mm = None

    # Run craft check
    craft_result = craft_check_pipeline(
        vertices if vertices is not None else _dummy_vertices(),
        faces if faces is not None else _dummy_faces(),
        material=material,
        dimensions_mm=dimensions_mm
    )

    retry_count = 0
    while not craft_result.passed and retry_count < max_retries:
        # Retry generation with modified prompt
        retry_count += 1
        vertices, faces = _mock_text_to_3d(prompt + " compact form")
        craft_result = craft_check_pipeline(
            vertices, faces, material=material, dimensions_mm=dimensions_mm
        )

    # If still failing after retries, return with warning
    if not craft_result.passed:
        return None, "Craft validation failed after retries"

    # Calculate pricing
    if dimensions_mm:
        volume = dimensions_mm[0] * dimensions_mm[1] * dimensions_mm[2] / 1000
    else:
        volume = 500
    weight = volume * 2.5
    price = max(199, volume * 0.8 + weight * 0.5)

    return GenerativePipelineResult(
        option_id=str(uuid.uuid4()),
        name=design_params.get("shape", "创意设计"),
        description=f"AI生成设计 - {prompt[:50]}...",
        glb_url=f"designs/{str(uuid.uuid4())}.glb",
        thumbnail_url=f"thumbnails/{str(uuid.uuid4())}.png",
        craft_check_result=craft_result.model_dump(),
        estimated_volume=volume,
        estimated_weight=weight,
        price=price,
        estimated_days=10
    ), None


def _mock_text_to_3d(prompt: str) -> tuple:
    """Mock text-to-3D generation"""
    import numpy as np

    # Create a simple mock mesh
    vertices = np.array([
        [-50, 0, 0], [50, 0, 0], [50, 100, 0], [-50, 100, 0],
        [0, 150, 0]
    ], dtype=np.float32)

    faces = np.array([
        [0, 1, 4],
        [1, 2, 4],
        [2, 3, 4],
        [3, 0, 4]
    ], dtype=np.int32)

    return vertices, faces


def _dummy_vertices():
    import numpy as np
    return np.array([[0, 0, 0]], dtype=np.float32)


def _dummy_faces():
    import numpy as np
    return np.array([[0, 0, 0]], dtype=np.int32)

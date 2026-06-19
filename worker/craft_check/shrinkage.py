"""Shrinkage Compensation"""


def apply_shrinkage_compensation(
    vertices: list[float],
    shrinkage_factor: float
) -> list[float]:
    """
    Apply shrinkage compensation by scaling mesh.

    Args:
        vertices: List of vertex positions [x1,y1,z1,x2,y2,z2,...]
        shrinkage_factor: Scaling factor (e.g., 1.15 for 15% shrinkage)

    Returns:
        Scaled vertices
    """
    if shrinkage_factor == 1.0:
        return vertices

    scaled = [v * shrinkage_factor for v in vertices]
    return scaled


def calculate_compensated_dimensions(
    target_height_mm: float,
    target_width_mm: float,
    shrinkage_factor: float
) -> tuple[float, float]:
    """
    Calculate compensated dimensions to achieve target size after firing.

    Args:
        target_height_mm: Desired final height in mm
        target_width_mm: Desired final width in mm
        shrinkage_factor: Material shrinkage factor

    Returns:
        (compensated_height_mm, compensated_width_mm)
    """
    compensated_height = target_height_mm * shrinkage_factor
    compensated_width = target_width_mm * shrinkage_factor

    return compensated_height, compensated_width

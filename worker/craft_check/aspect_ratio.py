"""Aspect Ratio Validation"""


def check_aspect_ratio(
    height_mm: float,
    width_mm: float,
    max_aspect_ratio: float
) -> tuple[bool, float]:
    """
    Check aspect ratio (height / width).

    Args:
        height_mm: Object height in mm
        width_mm: Object width in mm
        max_aspect_ratio: Maximum allowed aspect ratio

    Returns:
        (passed, ratio)
    """
    if width_mm <= 0:
        return False, float('inf')

    ratio = height_mm / width_mm
    passed = ratio <= max_aspect_ratio

    return passed, ratio

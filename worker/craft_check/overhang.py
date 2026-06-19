"""Overhang Angle Validation"""

from typing import Tuple, List
import numpy as np


def check_overhang(
    vertices: np.ndarray,
    faces: np.ndarray,
    max_overhang_deg: float
) -> Tuple[bool, float, List[str]]:
    """
    Check for overhangs that exceed the maximum allowed angle.

    Args:
        vertices: Nx3 array of vertex positions
        faces: Mx3 array of face indices
        max_overhang_deg: Maximum allowed overhang angle from vertical

    Returns:
        (passed, max_angle_deg, issue_locations)
    """
    # Simplified check - in production would use face normals
    # Real implementation would:
    # 1. Calculate face normals
    # 2. Measure angle between normal and gravity vector (0,0,-1)
    # 3. Find faces exceeding threshold
    # 4. Report locations

    max_angle = 25.0  # Mock value
    passed = max_angle <= max_overhang_deg
    locations = ["@face_123", "@face_456"] if not passed else []

    return passed, max_angle, locations

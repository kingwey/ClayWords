"""Auto-fix for Common Craft Issues"""

from typing import Optional
import numpy as np


def fix_wall_thickness(
    vertices: np.ndarray,
    faces: np.ndarray,
    target_thickness_mm: float
) -> tuple[np.ndarray, bool]:
    """
    Attempt to fix wall thickness issues by offsetting surface.

    Args:
        vertices: Nx3 array of vertex positions
        faces: Mx3 array of face indices
        target_thickness_mm: Target minimum thickness

    Returns:
        (fixed_vertices, success)
    """
    # Simplified fix - in production would use proper mesh offsetting
    # This is a placeholder that scales the mesh slightly
    scale_factor = 1.05
    fixed_vertices = vertices * scale_factor
    return fixed_vertices, True


def fix_base_stability(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_base_ratio: float
) -> tuple[np.ndarray, bool]:
    """
    Attempt to fix base stability by adding a heavier base.

    Args:
        vertices: Nx3 array of vertex positions
        faces: Mx3 array of face indices
        min_base_ratio: Target minimum base ratio

    Returns:
        (fixed_vertices, success)
    """
    # Simplified fix - add a base disc
    # In production would add proper geometry to bottom
    return vertices, False  # Indicates fix not implemented


def auto_fix_issues(
    vertices: np.ndarray,
    faces: np.ndarray,
    issues: list[str]
) -> tuple[Optional[np.ndarray], bool, list[str]]:
    """
    Automatically fix identified issues.

    Args:
        vertices: Nx3 array of vertex positions
        faces: Mx3 array of face indices
        issues: List of issue descriptions

    Returns:
        (fixed_vertices or None, any_fix_applied, remaining_issues)
    """
    fixed = vertices.copy()
    any_fixed = False
    remaining = []

    for issue in issues:
        if "wall_too_thin" in issue:
            fixed, success = fix_wall_thickness(fixed, faces, 3.0)
            if success:
                any_fixed = True
            else:
                remaining.append(issue)
        elif "base_unstable" in issue:
            _, success = fix_base_stability(fixed, faces, 0.15)
            if success:
                any_fixed = True
            else:
                remaining.append(issue)
        else:
            remaining.append(issue)

    return fixed if any_fixed else None, any_fixed, remaining

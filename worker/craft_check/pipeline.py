"""Main Craft Check Pipeline"""

from typing import Optional
import numpy as np

from .rules import CraftRules, get_craft_rules
from .models import CraftCheckResult
from .wall_thickness import check_wall_thickness
from .overhang import check_overhang
from .base_stability import check_base_stability
from .aspect_ratio import check_aspect_ratio
from .auto_fix import auto_fix_issues


def craft_check_pipeline(
    vertices: np.ndarray,
    faces: np.ndarray,
    material: str = "porcelain_white",
    studio_overrides: dict | None = None,
    dimensions_mm: tuple[float, float, float] | None = None
) -> CraftCheckResult:
    """
    Run craft validation pipeline on a mesh.

    Args:
        vertices: Nx3 array of vertex positions
        faces: Mx3 array of face indices
        material: Material type for rule selection
        studio_overrides: Optional studio-specific rule overrides
        dimensions_mm: Optional (height, width, depth) in mm

    Returns:
        CraftCheckResult with validation status and issues
    """
    rules = get_craft_rules(material, studio_overrides)

    issues = []

    # Check wall thickness
    if len(vertices) > 0 and len(faces) > 0:
        wall_passed, min_thickness = check_wall_thickness(
            vertices, faces, rules.min_wall_thickness_mm
        )
        if not wall_passed:
            issues.append(f"wall_too_thin@min={min_thickness:.1f}mm")

    # Check overhang
    if len(vertices) > 0 and len(faces) > 0:
        overhang_passed, max_angle, locations = check_overhang(
            vertices, faces, rules.max_overhang_deg
        )
        if not overhang_passed:
            issues.append(f"overhang_{max_angle:.0f}deg")

    # Check base stability
    if len(vertices) > 0 and len(faces) > 0:
        base_passed, base_ratio = check_base_stability(
            vertices, faces, rules.min_base_ratio
        )
        if not base_passed:
            issues.append(f"base_unstable@ratio={base_ratio:.2f}")

    # Check aspect ratio
    if dimensions_mm:
        height, width, _ = dimensions_mm
        aspect_passed, ratio = check_aspect_ratio(
            height, width, rules.max_aspect_ratio
        )
        if not aspect_passed:
            issues.append(f"aspect_ratio_{ratio:.1f}")

    passed = len(issues) == 0
    auto_fixed = False
    fixed_mesh_uri = None

    # Attempt auto-fix if issues found
    if not passed and len(vertices) > 0:
        fixed_vertices, any_fixed, remaining = auto_fix_issues(vertices, faces, issues)
        if any_fixed:
            auto_fixed = True
            issues = remaining
            passed = len(issues) == 0

    return CraftCheckResult(
        passed=passed,
        issues=issues,
        auto_fixed=auto_fixed,
        fixed_mesh_uri=fixed_mesh_uri
    )

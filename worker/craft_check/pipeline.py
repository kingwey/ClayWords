"""Main Craft Check Pipeline

整合 4 类几何校验 + 自动修复，产出统一的 CraftCheckResult。
"""

from typing import Optional
import numpy as np

from .rules import CraftRules, get_craft_rules
from .models import CraftCheckResult
from .wall_thickness import check_wall_thickness
from .overhang import check_overhang
from .base_stability import check_base_stability
from .aspect_ratio import check_aspect_ratio
from .auto_fix import auto_fix_issues


def _run_checks(
    vertices: np.ndarray,
    faces: np.ndarray,
    rules: CraftRules,
    dimensions_mm: tuple[float, float, float] | None,
) -> list[str]:
    """跑一遍所有几何校验，返回 issues 列表"""
    issues: list[str] = []

    if len(vertices) == 0 or len(faces) == 0:
        return ["empty_mesh"]

    # 壁厚
    wall_passed, min_thickness = check_wall_thickness(
        vertices, faces, rules.min_wall_thickness_mm
    )
    if not wall_passed:
        issues.append(f"wall_too_thin@min={min_thickness:.1f}mm")

    # 悬臂
    overhang_passed, max_angle, _locations = check_overhang(
        vertices, faces, rules.max_overhang_deg
    )
    if not overhang_passed:
        issues.append(f"overhang_{max_angle:.0f}deg")

    # 底面稳定
    base_passed, base_ratio = check_base_stability(
        vertices, faces, rules.min_base_ratio
    )
    if not base_passed:
        issues.append(f"base_unstable@ratio={base_ratio:.2f}")

    # 长宽比
    if dimensions_mm:
        height, width, _ = dimensions_mm
        aspect_passed, ratio = check_aspect_ratio(
            height, width, rules.max_aspect_ratio
        )
        if not aspect_passed:
            issues.append(f"aspect_ratio_{ratio:.1f}")

    return issues


def craft_check_pipeline(
    vertices: np.ndarray,
    faces: np.ndarray,
    material: str = "porcelain_white",
    studio_overrides: dict | None = None,
    dimensions_mm: tuple[float, float, float] | None = None,
) -> CraftCheckResult:
    """
    工艺校验主流程：检测 → 自动修复 → 复检。

    Args:
        vertices: (N, 3) 顶点
        faces: (M, 3) 三角面片
        material: 材质标识
        studio_overrides: 工作室自定义阈值
        dimensions_mm: (height, width, depth) 用于长宽比校验

    Returns:
        CraftCheckResult
    """
    rules = get_craft_rules(material, studio_overrides)

    issues = _run_checks(vertices, faces, rules, dimensions_mm)
    auto_fixed = False
    fixed_mesh_uri: Optional[str] = None

    # 尝试自动修复
    if issues and len(vertices) > 0:
        fixed_vertices, any_fixed, _remaining = auto_fix_issues(
            vertices, faces, issues
        )
        if any_fixed and fixed_vertices is not None:
            auto_fixed = True
            # 用修复后的 mesh 复检一次
            issues = _run_checks(fixed_vertices, faces, rules, dimensions_mm)

    passed = len(issues) == 0

    return CraftCheckResult(
        passed=passed,
        issues=issues,
        auto_fixed=auto_fixed,
        fixed_mesh_uri=fixed_mesh_uri,
    )

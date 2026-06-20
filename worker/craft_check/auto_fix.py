"""Auto-fix for Common Craft Issues

针对工艺校验失败的 mesh，提供轻量自动修复策略：
- 壁厚不足 → 沿法线外推
- 底面不稳 → 加底座（在最低 z 处增加宽度）
- 悬臂过大 → 通过整体收紧 (按 z 收缩 X/Y) 减少外伸
"""

from typing import Optional, Tuple
import numpy as np


def fix_wall_thickness(
    vertices: np.ndarray,
    faces: np.ndarray,
    target_thickness_mm: float,
    current_thickness_mm: float,
) -> Tuple[np.ndarray, bool]:
    """
    沿法线外推增加壁厚。

    简化策略：每个顶点沿其平均法线外移 (target - current)/2。
    """
    if len(vertices) == 0 or len(faces) == 0:
        return vertices, False

    delta = max(0.0, target_thickness_mm - current_thickness_mm)
    if delta <= 0:
        return vertices, False

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    face_normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(face_normals, axis=1, keepdims=True)
    norms[norms == 0] = 1
    face_normals = face_normals / norms

    # 累加每顶点法线（顶点法线 = 邻接面法线平均）
    vertex_normals = np.zeros_like(vertices, dtype=np.float64)
    for i in range(3):
        np.add.at(vertex_normals, faces[:, i], face_normals)
    vn_norms = np.linalg.norm(vertex_normals, axis=1, keepdims=True)
    vn_norms[vn_norms == 0] = 1
    vertex_normals = vertex_normals / vn_norms

    fixed = vertices + vertex_normals.astype(vertices.dtype) * (delta / 2.0)
    return fixed, True


def fix_base_stability(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_base_ratio: float,
) -> Tuple[np.ndarray, bool]:
    """
    通过将底部顶点向外扩展来增加底面比例。

    策略：选取底部 10% 区域顶点，整体相对中心点扩展放大，形成"底座"。
    """
    if len(vertices) == 0:
        return vertices, False

    fixed = vertices.copy().astype(np.float64)
    z = fixed[:, 2]
    z_min = float(z.min())
    z_max = float(z.max())
    height = z_max - z_min
    if height <= 0:
        return vertices, False

    base_mask = z <= z_min + height * 0.10
    if not base_mask.any():
        return vertices, False

    # 求 XY 中心
    cx = float(fixed[base_mask, 0].mean())
    cy = float(fixed[base_mask, 1].mean())

    # 放大 1.4 倍
    scale = 1.4
    fixed[base_mask, 0] = (fixed[base_mask, 0] - cx) * scale + cx
    fixed[base_mask, 1] = (fixed[base_mask, 1] - cy) * scale + cy

    return fixed.astype(vertices.dtype), True


def fix_overhang(
    vertices: np.ndarray, faces: np.ndarray
) -> Tuple[np.ndarray, bool]:
    """
    悬臂修复：上半部 XY 整体收缩 0.85，向"上窄下宽"形态靠拢。
    """
    if len(vertices) == 0:
        return vertices, False

    fixed = vertices.copy().astype(np.float64)
    z = fixed[:, 2]
    z_min = float(z.min())
    z_max = float(z.max())
    height = z_max - z_min
    if height <= 0:
        return vertices, False

    upper_mask = z >= z_min + height * 0.5
    if not upper_mask.any():
        return vertices, False

    cx = float(fixed[:, 0].mean())
    cy = float(fixed[:, 1].mean())

    # 上半部按高度比例渐变收缩
    z_norm = (z[upper_mask] - (z_min + height * 0.5)) / (height * 0.5)
    z_norm = np.clip(z_norm, 0, 1)
    scale = 1.0 - z_norm * 0.15  # 顶部最多收 15%
    fixed[upper_mask, 0] = (fixed[upper_mask, 0] - cx) * scale + cx
    fixed[upper_mask, 1] = (fixed[upper_mask, 1] - cy) * scale + cy

    return fixed.astype(vertices.dtype), True


def auto_fix_issues(
    vertices: np.ndarray,
    faces: np.ndarray,
    issues: list[str],
) -> Tuple[Optional[np.ndarray], bool, list[str]]:
    """
    根据 issues 列表逐项尝试修复。

    Returns:
        (fixed_vertices or None, any_fix_applied, remaining_issues)
    """
    if len(vertices) == 0:
        return None, False, issues

    fixed = vertices.copy()
    any_fixed = False
    remaining: list[str] = []

    for issue in issues:
        if "wall_too_thin" in issue:
            # 解析 current_thickness
            try:
                current = float(issue.split("min=")[1].rstrip("mm"))
            except (IndexError, ValueError):
                current = 1.0
            new_v, ok = fix_wall_thickness(fixed, faces, 3.0, current)
            if ok:
                fixed = new_v
                any_fixed = True
            else:
                remaining.append(issue)
        elif "base_unstable" in issue:
            new_v, ok = fix_base_stability(fixed, faces, 0.15)
            if ok:
                fixed = new_v
                any_fixed = True
            else:
                remaining.append(issue)
        elif "overhang" in issue:
            new_v, ok = fix_overhang(fixed, faces)
            if ok:
                fixed = new_v
                any_fixed = True
            else:
                remaining.append(issue)
        else:
            remaining.append(issue)

    return (fixed if any_fixed else None), any_fixed, remaining

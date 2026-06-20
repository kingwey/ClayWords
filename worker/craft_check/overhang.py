"""Overhang Angle Validation

通过面法线与重力向量 (0, 0, -1) 夹角检测悬臂区域。
"""

from typing import Tuple, List
import numpy as np


def check_overhang(
    vertices: np.ndarray,
    faces: np.ndarray,
    max_overhang_deg: float,
) -> Tuple[bool, float, List[str]]:
    """
    检测面法线与重力夹角超过阈值的悬臂区域。

    悬臂判定：
        - 法线越接近水平（与 -Z 夹角越接近 90°），悬臂越严重
        - 真正"悬空向外"的区域：法线 z 分量 ≥ 0（向上或水平）
        - 计算 angle = degrees(arccos(-n_z))，向下面 angle=0，水平面 angle=90，朝上面 angle=180

    Args:
        vertices: (N, 3) 顶点
        faces: (M, 3) 三角面片
        max_overhang_deg: 允许最大悬臂角度（与垂直方向）

    Returns:
        (passed, max_angle_deg, locations)
    """
    if len(vertices) == 0 or len(faces) == 0:
        return True, 0.0, []

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normals = normals / norms

    # 重力 = (0, 0, -1)；面法线与重力夹角
    # cos(angle) = n · gravity = -n_z
    cos_angles = -normals[:, 2]
    cos_angles = np.clip(cos_angles, -1.0, 1.0)
    angles_deg = np.degrees(np.arccos(cos_angles))

    # 悬臂阈值：与重力夹角 > 90°-max_overhang_deg 的"朝上/水平外伸"面
    # 这里阈值 max_overhang_deg 表示「面法线偏离向下方向多少度算悬臂」
    threshold = 90.0 + max_overhang_deg  # 朝上面（>90°）超出 max_overhang_deg 视为悬臂
    issue_mask = angles_deg > threshold

    max_angle = float(angles_deg.max()) if len(angles_deg) else 0.0
    locations = [
        f"@face_{i}" for i in np.where(issue_mask)[0][:5]
    ]  # 最多前 5 个

    passed = not bool(issue_mask.any())
    # 报告时返回相对垂直方向的偏角
    reported_max = max(0.0, max_angle - 90.0)
    return passed, reported_max, locations

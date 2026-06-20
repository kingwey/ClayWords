"""Base Stability Validation

通过底面投影面积比和重心高度判断重心稳定性。
"""

from typing import Tuple
import numpy as np


def check_base_stability(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_base_ratio: float,
    base_tolerance: float = 0.05,
) -> Tuple[bool, float]:
    """
    检测底面稳定性。

    评估方法：
        1. 把 z = z_min ~ z_min + tolerance 之间的顶点视为底面
        2. 计算底面 XY 投影包围盒面积
        3. 计算整体 XY 包围盒面积
        4. base_ratio = 底面投影 / 整体投影
        5. 同时检查重心 z 是否过高（z_com / z_total > 0.6 视为头重脚轻）

    Args:
        vertices: (N, 3) 顶点
        faces: (M, 3) 三角面片
        min_base_ratio: 最小底面比例
        base_tolerance: 底面 z 容差比例（占整体高度）

    Returns:
        (passed, base_ratio)
    """
    if len(vertices) == 0:
        return False, 0.0

    z = vertices[:, 2]
    z_min = float(z.min())
    z_max = float(z.max())
    height = z_max - z_min

    if height <= 0:
        return False, 0.0

    # 底面顶点：z 接近最小值
    base_mask = z <= z_min + height * base_tolerance
    base_pts = vertices[base_mask]

    if len(base_pts) == 0:
        return False, 0.0

    # 底面 XY 包围盒面积
    base_xy = base_pts[:, :2]
    base_extent = base_xy.max(axis=0) - base_xy.min(axis=0)
    base_area = float(base_extent[0] * base_extent[1])

    # 整体 XY 包围盒面积
    full_xy = vertices[:, :2]
    full_extent = full_xy.max(axis=0) - full_xy.min(axis=0)
    full_area = float(full_extent[0] * full_extent[1])

    if full_area <= 0:
        return False, 0.0

    base_ratio = base_area / full_area

    # 重心高度比：> 0.6 视为头重脚轻
    com_z = float(z.mean())
    com_ratio = (com_z - z_min) / height
    if com_ratio > 0.6:
        # 重心过高，强制降低评分
        base_ratio = base_ratio * (1.0 - (com_ratio - 0.6) * 2)
        base_ratio = max(0.0, base_ratio)

    passed = base_ratio >= min_base_ratio
    return passed, base_ratio

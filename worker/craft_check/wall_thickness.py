"""Wall Thickness Validation

通过法线方向反向投射射线 (ray casting) 评估壁厚。
没有外部依赖时退化到 bounding box 厚度估计。
"""

from typing import Tuple, Optional
import numpy as np


def _compute_face_centers_and_normals(
    vertices: np.ndarray, faces: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """计算每个三角面片的中心和法线"""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    centers = (v0 + v1 + v2) / 3.0
    normals = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normals = normals / norms
    return centers, normals


def _ray_triangle_intersect_batch(
    origins: np.ndarray,
    directions: np.ndarray,
    v0: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
) -> np.ndarray:
    """
    Möller–Trumbore 算法批量计算射线与所有三角形的相交距离。

    Args:
        origins: (R, 3) 起点
        directions: (R, 3) 单位方向
        v0, v1, v2: (T, 3) 三角形三顶点

    Returns:
        (R,) 数组，每条射线最近正向交点距离；无交点 = inf
    """
    R = origins.shape[0]
    T = v0.shape[0]
    if R == 0 or T == 0:
        return np.full(R, np.inf, dtype=np.float32)

    eps = 1e-6
    edge1 = v1 - v0  # (T, 3)
    edge2 = v2 - v0  # (T, 3)

    # h: (R, T, 3) = directions (R,1,3) cross edge2 (1,T,3)
    h = np.cross(directions[:, None, :], edge2[None, :, :])
    a = np.einsum('tj,rtj->rt', edge1, h)  # (R, T)

    parallel = np.abs(a) < eps
    f = np.where(parallel, 0, 1.0 / np.where(parallel, 1, a))  # (R, T)

    s = origins[:, None, :] - v0[None, :, :]  # (R, T, 3)
    u = f * np.einsum('rtj,rtj->rt', s, h)  # (R, T)

    q = np.cross(s, edge1[None, :, :])  # (R, T, 3)
    v = f * np.einsum('rj,rtj->rt', directions, q)  # (R, T)

    t = f * np.einsum('tj,rtj->rt', edge2, q)  # (R, T)

    # 有效命中：未平行、重心坐标合法、t > eps（排除自身）
    hit = (~parallel) & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > eps)
    t_masked = np.where(hit, t, np.inf)
    return np.min(t_masked, axis=1)


def check_wall_thickness(
    vertices: np.ndarray,
    faces: np.ndarray,
    min_thickness_mm: float,
    sample_size: int = 32,
) -> Tuple[bool, float]:
    """
    通过反向法线投射估算最小壁厚。

    采样若干面片中心，沿 -法线 方向投射，命中的最近距离视为该处壁厚估计。
    取所有采样的最小值作为整体壁厚。

    Args:
        vertices: (N, 3) 顶点
        faces: (M, 3) 三角面片
        min_thickness_mm: 最小允许壁厚 (mm)
        sample_size: 采样面片数（越大越准但越慢）

    Returns:
        (passed, min_thickness_mm)
    """
    if len(vertices) == 0 or len(faces) == 0:
        return False, 0.0

    centers, normals = _compute_face_centers_and_normals(vertices, faces)
    M = centers.shape[0]

    # 均匀采样面片
    if M > sample_size:
        idx = np.linspace(0, M - 1, sample_size, dtype=np.int64)
    else:
        idx = np.arange(M)

    # 起点稍微沿 -法线偏移避免自相交
    eps = 1e-3
    origins = centers[idx] - normals[idx] * eps
    directions = -normals[idx]  # 反向射入实体内部

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    distances = _ray_triangle_intersect_batch(origins, directions, v0, v1, v2)
    valid = distances[np.isfinite(distances)]

    if len(valid) == 0:
        # 无内部命中（开放面或薄片），用 bounding box 最短边作上界估计
        bbox = vertices.max(axis=0) - vertices.min(axis=0)
        min_thickness = float(np.min(bbox)) if bbox.size else 0.0
    else:
        min_thickness = float(np.min(valid))

    passed = min_thickness >= min_thickness_mm
    return passed, min_thickness

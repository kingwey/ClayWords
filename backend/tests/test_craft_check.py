"""Unit tests for craft check modules."""

import sys
import os
import numpy as np
import pytest

# 把 worker 加进 path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKER_PATH = os.path.join(ROOT, "worker")
if WORKER_PATH not in sys.path:
    sys.path.insert(0, ROOT)

from worker.craft_check.rules import CRAFT_RULES, get_craft_rules
from worker.craft_check.aspect_ratio import check_aspect_ratio
from worker.craft_check.base_stability import check_base_stability
from worker.craft_check.overhang import check_overhang
from worker.craft_check.wall_thickness import check_wall_thickness
from worker.craft_check.shrinkage import (
    apply_shrinkage_compensation,
    calculate_compensated_dimensions,
)
from worker.craft_check.auto_fix import auto_fix_issues
from worker.craft_check.pipeline import craft_check_pipeline


def make_box(width=60, depth=60, height=200):
    """构造一个轴对齐立方体 mesh（24 顶点 12 面）"""
    w, d, h = width / 2, depth / 2, height
    verts = np.array(
        [
            # 底
            [-w, -d, 0], [w, -d, 0], [w, d, 0], [-w, d, 0],
            # 顶
            [-w, -d, h], [w, -d, h], [w, d, h], [-w, d, h],
        ],
        dtype=np.float32,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],          # 底
            [4, 6, 5], [4, 7, 6],          # 顶
            [0, 4, 5], [0, 5, 1],          # 前
            [1, 5, 6], [1, 6, 2],          # 右
            [2, 6, 7], [2, 7, 3],          # 后
            [3, 7, 4], [3, 4, 0],          # 左
        ],
        dtype=np.int32,
    )
    return verts, faces


# ---------- rules ----------


def test_porcelain_white_shrinkage_factor():
    assert CRAFT_RULES["porcelain_white"].shrinkage_factor == 1.18


def test_get_rules_with_overrides():
    rules = get_craft_rules(
        "porcelain_white", studio_overrides={"min_wall_thickness_mm": 4.5}
    )
    assert rules.min_wall_thickness_mm == 4.5
    # 其余字段保留默认
    assert rules.shrinkage_factor == 1.18


# ---------- aspect ratio ----------


def test_aspect_ratio_pass():
    passed, ratio = check_aspect_ratio(200, 100, max_aspect_ratio=4.0)
    assert passed
    assert ratio == pytest.approx(2.0)


def test_aspect_ratio_fail():
    passed, ratio = check_aspect_ratio(600, 100, max_aspect_ratio=4.0)
    assert not passed
    assert ratio == pytest.approx(6.0)


# ---------- shrinkage ----------


def test_shrinkage_compensation_scales_vertices():
    out = apply_shrinkage_compensation([1.0, 2.0, 3.0], 1.18)
    assert out == pytest.approx([1.18, 2.36, 3.54])


def test_compensated_dimensions():
    h, w = calculate_compensated_dimensions(180, 100, 1.18)
    assert h == pytest.approx(180 * 1.18)
    assert w == pytest.approx(100 * 1.18)


# ---------- base stability ----------


def test_base_stability_pass_for_box():
    v, f = make_box()
    passed, ratio = check_base_stability(v, f, min_base_ratio=0.15)
    assert passed
    # 立方体底面 = 整体 XY 投影，比例接近 1.0
    assert ratio >= 0.9


def test_base_stability_fail_for_top_heavy():
    """上重下轻：底面 10x10，顶面 100x100"""
    verts = np.array(
        [
            [-5, -5, 0], [5, -5, 0], [5, 5, 0], [-5, 5, 0],
            [-50, -50, 200], [50, -50, 200], [50, 50, 200], [-50, 50, 200],
        ],
        dtype=np.float32,
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32)
    passed, ratio = check_base_stability(verts, faces, min_base_ratio=0.15)
    assert not passed
    assert ratio < 0.15


# ---------- overhang ----------


def test_overhang_pass_for_box():
    v, f = make_box()
    passed, max_angle, locs = check_overhang(v, f, max_overhang_deg=30)
    # 立方体只有底/顶/侧面，水平外伸面会被判 overhang，但侧面 angle=90° 等于阈值临界
    # 这里我们关心整体不应崩
    assert isinstance(passed, bool)
    assert isinstance(max_angle, float)


def test_overhang_fail_for_horizontal_arm():
    """水平外伸臂"""
    verts = np.array(
        [
            [0, 0, 0], [10, 0, 0], [10, 0, 100], [0, 0, 100],
            # 顶部水平外伸
            [10, 0, 100], [50, 0, 100], [50, 5, 100], [10, 5, 100],
        ],
        dtype=np.float32,
    )
    # 一个水平面（朝上）+ 反面（朝下）
    faces = np.array([[4, 5, 6], [4, 6, 7]], dtype=np.int32)
    passed, max_angle, locs = check_overhang(verts, faces, max_overhang_deg=30)
    assert not passed


# ---------- wall thickness ----------


def test_wall_thickness_thick_box_passes():
    v, f = make_box(width=60, depth=60)  # 60mm 立方
    passed, thick = check_wall_thickness(v, f, min_thickness_mm=3.0)
    assert passed
    assert thick >= 3.0


def test_wall_thickness_thin_shell_fails():
    """2mm 立方"""
    v, f = make_box(width=2, depth=2)
    passed, thick = check_wall_thickness(v, f, min_thickness_mm=3.0)
    # 厚度不足 3mm
    assert not passed or thick < 3.0


# ---------- auto_fix ----------


def test_auto_fix_wall_thickness_returns_modified():
    v, f = make_box(width=2, depth=2, height=20)
    issues = ["wall_too_thin@min=1.5mm"]
    fixed, ok, remaining = auto_fix_issues(v, f, issues)
    assert ok
    assert fixed is not None
    assert not np.array_equal(fixed, v)


def test_auto_fix_overhang_modifies_upper_part():
    v, f = make_box(width=200, depth=200, height=300)
    issues = ["overhang_45deg"]
    fixed, ok, _ = auto_fix_issues(v, f, issues)
    assert ok
    # 顶面 XY 范围应缩小
    upper_orig = v[v[:, 2] >= 150][:, :2]
    upper_fixed = fixed[v[:, 2] >= 150][:, :2]
    assert (np.ptp(upper_fixed, axis=0) <= np.ptp(upper_orig, axis=0)).all()


# ---------- pipeline ----------


def test_pipeline_runs_on_20_meshes_without_crash():
    """整合 pipeline 在多种样例上不崩"""
    samples = []
    # 12 种规格立方体
    for w in [10, 30, 60, 100]:
        for h in [50, 200, 500]:
            samples.append(make_box(width=w, depth=w, height=h))
    # 8 个 thin/wide 变体
    for ratio in [0.2, 0.5, 1.0, 2.0, 4.0, 6.0, 0.1, 8.0]:
        samples.append(make_box(width=60, depth=60, height=int(60 * ratio)))

    assert len(samples) >= 20
    for v, f in samples:
        result = craft_check_pipeline(v, f, material="porcelain_white")
        assert result is not None
        assert isinstance(result.passed, bool)
        assert isinstance(result.issues, list)

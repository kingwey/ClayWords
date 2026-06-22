"""派单评分 / 策略单元测试

覆盖：
- 硬约束：评分低于阈值、容量耗尽 → 总分 0
- 工艺匹配：完全/部分/泛匹配
- 排序稳定性：tie-break 用 rating
- dispatch_order 三层 fallback：best > central > manual
"""

import pytest

from app.services.dispatch.scoring import (
    DesignParams,
    StudioInfo,
    score_studio,
    rank_studios,
    calc_craft_score,
    calc_capacity_score,
    MIN_RATING_THRESHOLD,
)
from app.services.dispatch.policy import (
    dispatch_order,
    DISPATCH_THRESHOLD,
)


def _make_studio(**overrides) -> StudioInfo:
    base = dict(
        studio_id="s1",
        name="景德镇 · 测试工作室",
        specialties=["白瓷", "青花"],
        capacity=10,
        current_load=3,
        rating=4.5,
        price_range_min=100,
        price_range_max=2000,
        estimated_days=7,
        location="景德镇",
    )
    base.update(overrides)
    return StudioInfo(**base)


def _make_params(**overrides) -> DesignParams:
    base = dict(material="白瓷", category="花瓶", price_range=(200, 800))
    base.update(overrides)
    return DesignParams(**base)


class TestScoreHardConstraints:
    def test_rating_below_threshold_yields_zero(self):
        studio = _make_studio(rating=MIN_RATING_THRESHOLD - 0.1)
        breakdown = score_studio(studio, _make_params())
        assert breakdown.total == 0

    def test_full_capacity_yields_zero(self):
        studio = _make_studio(capacity=5, current_load=5)
        breakdown = score_studio(studio, _make_params())
        assert breakdown.total == 0

    def test_zero_capacity_yields_zero(self):
        studio = _make_studio(capacity=0, current_load=0)
        breakdown = score_studio(studio, _make_params())
        assert breakdown.total == 0


class TestCraftScore:
    def test_full_match_two_specialties(self):
        studio = _make_studio(specialties=["白瓷", "花瓶器型"])
        params = _make_params(material="白瓷", category="花瓶")
        # category="花瓶" 与 "花瓶器型" substring 命中，material="白瓷" 也命中 → matched>=2
        assert calc_craft_score(params, studio) == 1.0

    def test_no_specialties_returns_default(self):
        studio = _make_studio(specialties=[])
        assert calc_craft_score(_make_params(), studio) == 0.3

    def test_no_match_returns_low(self):
        studio = _make_studio(specialties=["紫砂", "粗陶"])
        params = _make_params(material="景泰蓝", category="壁画")
        # 两个领域无任何关联词
        assert calc_craft_score(params, studio) == 0.2


class TestCapacityScore:
    def test_no_capacity(self):
        assert calc_capacity_score(_make_studio(capacity=0)) == 0.0

    def test_moderate_load_returns_ratio(self):
        # current_load=5, capacity=10 → ratio=0.5（在 [0.3, 0.8]）
        score = calc_capacity_score(_make_studio(capacity=10, current_load=5))
        assert score == pytest.approx(0.5)

    def test_very_idle_capped_at_0_9(self):
        # current_load=0, capacity=10 → ratio=1.0 → 触发 >0.8 分支
        assert calc_capacity_score(_make_studio(capacity=10, current_load=0)) == 0.9


class TestRankStudios:
    def test_tie_breaker_prefers_higher_rating(self):
        s1 = _make_studio(studio_id="s1", rating=4.6)
        s2 = _make_studio(studio_id="s2", rating=4.9)
        ranked = rank_studios([s1, s2], _make_params())
        assert ranked[0][0].studio_id == "s2"

    def test_filters_out_zero_total(self):
        good = _make_studio(studio_id="ok")
        bad = _make_studio(studio_id="overload", current_load=10, capacity=10)
        ranked = rank_studios([good, bad], _make_params())
        ids = [s.studio_id for s, _ in ranked]
        assert "overload" not in ids
        assert "ok" in ids


class TestDispatchPolicy:
    def test_best_studio_above_threshold(self):
        s1 = _make_studio(studio_id="best")
        result = dispatch_order([s1], _make_params())
        assert result.dispatched is True
        assert result.studio_id == "best"
        assert result.score >= DISPATCH_THRESHOLD

    def test_no_studio_marks_manual(self):
        result = dispatch_order([], _make_params())
        assert result.dispatched is False
        assert result.requires_manual is True

    def test_central_studio_fallback_when_below_threshold(self):
        # 工作室专长完全不匹配 → 总分会偏低；指定一个已有的 studio_id 作为兜底
        weak = _make_studio(
            studio_id="weak",
            specialties=["紫砂"],
            rating=4.0,  # rating_score 映射为 0
            current_load=9,
            capacity=10,
        )
        central = _make_studio(
            studio_id="central",
            specialties=["紫砂"],
            rating=4.0,
            current_load=9,
            capacity=10,
        )
        params = _make_params(material="景泰蓝", category="壁画")
        result = dispatch_order(
            [weak, central],
            params,
            central_studio_id="central",
            threshold=0.99,  # 强制走兜底分支
        )
        # 最佳分数 < 0.99 → 走兜底
        assert result.dispatched is True
        assert result.studio_id == "central"
        assert "Fallback" in result.reason

    def test_no_central_no_fallback_marks_manual(self):
        weak = _make_studio(studio_id="weak", specialties=["紫砂"], rating=4.0)
        params = _make_params(material="景泰蓝", category="壁画")
        result = dispatch_order([weak], params, threshold=0.99)
        assert result.dispatched is False
        assert result.requires_manual is True

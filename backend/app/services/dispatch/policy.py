"""Dispatch Policy Service - Selection and fallback logic"""

from dataclasses import dataclass
from typing import Optional
from .scoring import (
    StudioInfo, DesignParams, ScoreBreakdown, 
    rank_studios, MIN_RATING_THRESHOLD
)


# Score threshold for automatic dispatch
DISPATCH_THRESHOLD = 0.55

# Central studio fallback ID (platform's own studio)
CENTRAL_STUDIO_ID = "8672f323-7dc0-48af-ac56-482fc8c48628"


@dataclass
class DispatchResult:
    """Result of dispatch decision"""
    dispatched: bool
    studio_id: Optional[str]
    studio_name: Optional[str]
    score: float
    reason: str
    requires_manual: bool = False


def should_dispatch(score: float, threshold: float = DISPATCH_THRESHOLD) -> bool:
    """Check if score is above dispatch threshold."""
    return score >= threshold


def select_best_studio(
    ranked_studios: list[tuple[StudioInfo, ScoreBreakdown]],
    threshold: float = DISPATCH_THRESHOLD
) -> Optional[tuple[StudioInfo, ScoreBreakdown]]:
    """
    Select the best studio from ranked list.
    
    Returns None if no studio meets the threshold.
    """
    if not ranked_studios:
        return None
    
    best = ranked_studios[0]
    if should_dispatch(best[1].total, threshold):
        return best
    
    return None


def dispatch_order(
    studios: list[StudioInfo],
    params: DesignParams,
    central_studio_id: str = CENTRAL_STUDIO_ID,
    threshold: float = DISPATCH_THRESHOLD
) -> DispatchResult:
    """
    Main dispatch logic with fallback chain.
    
    Fallback chain:
    1. Best scoring studio above threshold
    2. Central studio (if not already selected)
    3. Manual dispatch required
    
    Returns DispatchResult with decision details.
    """
    # Rank all studios
    ranked = rank_studios(studios, params)
    
    if not ranked:
        return DispatchResult(
            dispatched=False,
            studio_id=None,
            studio_name=None,
            score=0,
            reason="No studios available with required capacity",
            requires_manual=True
        )
    
    # Try best studio
    best_studio, best_score = ranked[0]
    
    if should_dispatch(best_score.total, threshold):
        return DispatchResult(
            dispatched=True,
            studio_id=best_studio.studio_id,
            studio_name=best_studio.name,
            score=best_score.total,
            reason=f"Best match with score {best_score.total:.2f}"
        )
    
    # Try central studio as fallback
    central = next(
        (s for s, _ in ranked if s.studio_id == central_studio_id),
        None
    )
    
    if central:
        central_score = next(
            (score for s, score in ranked if s.studio_id == central_studio_id),
            None
        )
        return DispatchResult(
            dispatched=True,
            studio_id=central.studio_id,
            studio_name=central.name,
            score=central_score.total if central_score else 0,
            reason=f"Fallback to central studio (best score {best_score.total:.2f} below threshold)"
        )
    
    # No suitable studio - requires manual intervention
    return DispatchResult(
        dispatched=False,
        studio_id=None,
        studio_name=None,
        score=best_score.total,
        reason=f"All studios below threshold {threshold}. Best: {best_studio.name} ({best_score.total:.2f})",
        requires_manual=True
    )


def get_top_n_studios(
    studios: list[StudioInfo],
    params: DesignParams,
    n: int = 3
) -> list[tuple[StudioInfo, ScoreBreakdown]]:
    """
    Get top N studios for display/selection.
    
    Used for frontend visualization.
    """
    ranked = rank_studios(studios, params)
    return ranked[:n]

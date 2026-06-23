"""Time utilities - timezone-aware UTC helpers

替代裸 datetime.utcnow()，消除 naive datetime 风险。
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    返回 timezone-aware UTC now。

    替代 datetime.utcnow()（返回 naive datetime，tzinfo=None）。
    使用 timezone.utc 确保时区语义明确，避免 naive/aware 混用导致的 TypeError。

    Returns:
        datetime: UTC 当前时间，tzinfo=timezone.utc
    """
    return datetime.now(timezone.utc)

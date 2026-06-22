"""Unit tests for logging middleware (sanitization)"""

import pytest
from app.core.logging_middleware import (
    sanitize_phone, sanitize_email, sanitize_address, sanitize_text,
    PHONE_PATTERN, EMAIL_PATTERN
)


@pytest.mark.unit
class TestPhoneSanitization:
    """手机号脱敏测试"""

    def test_sanitize_valid_phone(self):
        """测试有效手机号脱敏"""
        assert sanitize_phone("13912345678") == "139****5678"
        assert sanitize_phone("15812345678") == "158****5678"
        assert sanitize_phone("18612345678") == "186****5678"

    def test_sanitize_short_phone(self):
        """测试短手机号（不脱敏）"""
        assert sanitize_phone("1234567") == "1234567"

    def test_phone_pattern_match(self):
        """测试手机号正则匹配"""
        text = "联系电话: 13912345678 或 15887654321"
        matches = PHONE_PATTERN.findall(text)
        assert len(matches) == 2


@pytest.mark.unit
class TestEmailSanitization:
    """邮箱脱敏测试"""

    def test_sanitize_normal_email(self):
        """测试普通邮箱脱敏"""
        assert sanitize_email("user@example.com") == "u***@example.com"
        assert sanitize_email("alice@test.org") == "a***@test.org"

    def test_sanitize_short_local_part(self):
        """测试短本地部分的邮箱"""
        assert sanitize_email("a@example.com") == "a@example.com"

    def test_sanitize_invalid_email(self):
        """测试无效邮箱"""
        assert sanitize_email("invalid_email") == "invalid_email"


@pytest.mark.unit
class TestAddressSanitization:
    """地址脱敏测试"""

    def test_sanitize_long_address(self):
        """测试长地址脱敏"""
        assert sanitize_address("北京市朝阳区xxxxx") == "北京市朝阳区***"

    def test_sanitize_short_address(self):
        """测试短地址（不脱敏）"""
        assert sanitize_address("北京") == "北京"


@pytest.mark.unit
class TestTextSanitization:
    """文本脱敏测试"""

    def test_sanitize_phone_in_text(self):
        """测试文本中的手机号脱敏"""
        text = "用户 13912345678 下单"
        sanitized = sanitize_text(text)

        assert "13912345678" not in sanitized
        assert "139****5678" in sanitized

    def test_sanitize_email_in_text(self):
        """测试文本中的邮箱脱敏"""
        text = "邮件发送至 test@example.com"
        sanitized = sanitize_text(text)

        assert "test@example.com" not in sanitized
        assert "t***@example.com" in sanitized

    def test_sanitize_mixed_sensitive_info(self):
        """测试混合敏感信息脱敏"""
        text = "用户张三 (13912345678, alice@test.com) 下单"
        sanitized = sanitize_text(text)

        assert "13912345678" not in sanitized
        assert "alice@test.com" not in sanitized
        assert "张三" in sanitized  # 姓名不脱敏（业务决定）

    def test_sanitize_non_string(self):
        """测试非字符串输入"""
        assert sanitize_text(123) == 123
        assert sanitize_text(None) is None

"""auth API 端点单元测试 (nickname / profile)"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from fastapi import FastAPI
    from app.api import auth

    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1/auth")
    return TestClient(app)


class TestAuthRouterMounted:
    def test_profile_route_registered(self, client):
        spec = client.get("/openapi.json").json()
        paths = set(spec.get("paths", {}).keys())
        assert "/api/v1/auth/profile" in paths
        assert "/api/v1/auth/user" in paths

    def test_social_routes_registered(self, client):
        spec = client.get("/openapi.json").json()
        paths = set(spec.get("paths", {}).keys())
        assert "/api/v1/auth/social/bind" in paths
        assert "/api/v1/auth/social/unbind" in paths

    def test_openapi_userinfo_has_nickname(self, client):
        spec = client.get("/openapi.json").json()
        schema = spec["components"]["schemas"]["UserInfo"]
        assert "nickname" in schema["properties"]
        assert "social_bindings" in schema["properties"]


class TestProfileGuard:
    def test_patch_profile_without_cookie_is_401(self, client):
        r = client.patch("/api/v1/auth/profile", json={"nickname": "test"})
        assert r.status_code == 401

    def test_get_user_without_cookie_is_401(self, client):
        r = client.get("/api/v1/auth/user")
        assert r.status_code == 401

    def test_bind_social_without_cookie_is_401(self, client):
        r = client.post("/api/v1/auth/social/bind", json={"provider": "wechat"})
        assert r.status_code == 401

    def test_unbind_social_without_cookie_is_401(self, client):
        r = client.post("/api/v1/auth/social/unbind", json={"provider": "wechat"})
        assert r.status_code == 401


class TestSupportedProviders:
    def test_five_providers_supported(self):
        from app.api.auth import SUPPORTED_SOCIAL_PROVIDERS
        assert set(SUPPORTED_SOCIAL_PROVIDERS) == {
            "wechat", "feishu", "qq", "dingtalk", "douyin"
        }


class TestUpdateProfileRequest:
    """UpdateProfileRequest Pydantic 校验"""

    def test_accepts_string_nickname(self):
        from app.api.auth import UpdateProfileRequest
        req = UpdateProfileRequest(nickname="陶语用户")
        assert req.nickname == "陶语用户"

    def test_accepts_empty_string(self):
        # 空串语义是"清空昵称"
        from app.api.auth import UpdateProfileRequest
        req = UpdateProfileRequest(nickname="")
        assert req.nickname == ""

    def test_accepts_null(self):
        from app.api.auth import UpdateProfileRequest
        req = UpdateProfileRequest(nickname=None)
        assert req.nickname is None

    def test_accepts_omitted(self):
        from app.api.auth import UpdateProfileRequest
        req = UpdateProfileRequest()
        assert req.nickname is None
        assert req.phone is None

    def test_accepts_phone(self):
        from app.api.auth import UpdateProfileRequest
        req = UpdateProfileRequest(phone="13900001234")
        assert req.phone == "13900001234"


class TestBindSocialRequest:
    def test_requires_provider(self):
        from app.api.auth import BindSocialRequest
        req = BindSocialRequest(provider="wechat")
        assert req.provider == "wechat"
        assert req.external_id is None


class TestUserInfoSchema:
    """UserInfo 应包含 nickname / social_bindings 字段"""

    def test_userinfo_has_nickname_default_none(self):
        from app.api.auth import UserInfo
        u = UserInfo(user_id="u1", phone="139****1234", role="user")
        assert u.nickname is None
        assert u.social_bindings == {}

    def test_userinfo_round_trip_with_nickname(self):
        from app.api.auth import UserInfo
        u = UserInfo(user_id="u1", phone="139****1234", role="user", nickname="陶语")
        assert u.nickname == "陶语"
        # JSON round-trip
        data = u.model_dump()
        assert data["nickname"] == "陶语"

    def test_userinfo_with_social_bindings(self):
        from app.api.auth import UserInfo
        u = UserInfo(
            user_id="u1", phone="139****1234", role="user",
            social_bindings={"wechat": {"openid": "x", "bound_at": "2026-01-01"}},
        )
        assert "wechat" in u.social_bindings

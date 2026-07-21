"""Smoke tests - basic smoke tests that should always pass"""

import pytest


@pytest.mark.smoke
class TestSmoke:
    """烟雾测试 - 验证基本功能"""

    def test_import_app(self):
        """测试应用可以导入"""
        try:
            from app import main
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app: {e}")

    def test_import_models(self):
        """测试模型可以导入"""
        from app.models.entities import (
            User, Studio, Session, Order, Upload, Task,
            DesignTemplate, IdempotencyKey
        )
        assert User is not None
        assert Studio is not None
        assert Order is not None

    def test_import_services(self):
        """测试服务可以导入"""
        from app.services.payment.payment_service import PaymentService
        from app.services.alerting.alerting_service import AlertingService
        from app.services.tasks.task_service import TaskService

        assert PaymentService is not None
        assert AlertingService is not None
        assert TaskService is not None

    def test_import_apis(self):
        """测试 API 可以导入"""
        from app.api import (
            auth, sessions, orders, uploads, payments,
            logistics, studio_onboarding, studio_orders
        )
        assert all([auth, sessions, orders, uploads, payments])

    def test_config_loads(self):
        """测试配置加载"""
        from app.core.config import settings
        assert settings.VERSION is not None
        assert settings.DATABASE_URL is not None


@pytest.mark.smoke
class TestUtilities:
    """工具函数烟雾测试"""

    def test_metrics_singleton(self):
        """测试 metrics 单例"""
        from app.core.metrics import get_metrics
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_alerting_singleton(self):
        """测试 alerting 单例"""
        from app.services.alerting.alerting_service import get_alerting_service
        a1 = get_alerting_service()
        a2 = get_alerting_service()
        assert a1 is a2

"""Production Application Configuration

Phase Q10 P0: 生产环境配置
- DEBUG 关闭
- JWT 过期时间配置
- 环境区分
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Literal


# 生产环境必须替换的默认值前缀（开发期占位符）
_DEV_PLACEHOLDERS = (
    "dev_pepper_change_in_production",
    "dev_secret_key_change_in_production",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VERSION: str = "1.0.0"

    # 环境配置
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False  # P0: 生产环境默认关闭

    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"  # P0: 生产需覆盖

    # Database (默认 Postgres，测试可用 SQLite)
    DATABASE_URL: str = "postgresql+asyncpg://claywords:claywords_secret@localhost:5432/claywords"
    # 连接池：默认 5/10 在 SSE 长连接 + 多副本下偏小
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 10
    DB_POOL_RECYCLE: int = 1800

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "claywords"
    MINIO_SECRET_KEY: str = "claywords_secret"
    MINIO_BUCKET: str = "claywords"
    MINIO_SECURE: bool = False  # P0: 生产环境需设为 True

    # Crypto (加密 pepper)
    CRYPTO_PEPPER: str = "dev_pepper_change_in_production"

    # JWT (P0: 配置过期时间)
    JWT_SECRET_KEY: str = "dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 天 = 7 * 24 * 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 天

    # LLM
    LLM_PROVIDER: str = "tongyi"
    TONGYI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Alipay
    ALIPAY_APP_ID: str = "2021000000000000"  # 生产需覆盖
    ALIPAY_PRIVATE_KEY: str = ""  # RSA2 私钥
    ALIPAY_PUBLIC_KEY: str = ""  # 支付宝公钥
    ALIPAY_NOTIFY_URL: str = "https://api.claywords.com/api/v1/payments/callback"  # P0: HTTPS
    ALIPAY_RETURN_URL: str = "https://claywords.com/orders"  # P0: HTTPS

    # 中央兜底工作室（派单 fallback 时使用）。生产环境通过环境变量注入实际 ID
    CENTRAL_STUDIO_ID: str = ""

    # Hunyuan3D
    HUNYUAN3D_API_KEY: str = ""
    HUNYUAN3D_BASE_URL: str = "https://api.ai3d.cloud.tencent.com"
    HUNYUAN3D_POLL_INTERVAL: int = 5  # 轮询间隔（秒）
    HUNYUAN3D_MAX_POLL_ATTEMPTS: int = 120  # 最大轮询次数（10 分钟）
    ENABLE_HUNYUAN3D: bool = True  # 功能开关

    # ClamAV 文件扫描（uploads.confirm 接入）
    # 开发环境默认关闭以省去本地依赖；生产环境必须开启，否则启动校验拒启。
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: int = 30  # 扫描超时（大文件需要更长）

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def cors_origins_list(self) -> list:
        """CORS 允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """生产环境启动时强校验：占位密钥/演示账号未替换 → 直接拒启。"""
        if self.is_production:
            problems: list[str] = []
            if self.CRYPTO_PEPPER in _DEV_PLACEHOLDERS or not self.CRYPTO_PEPPER:
                problems.append("CRYPTO_PEPPER")
            if self.JWT_SECRET_KEY in _DEV_PLACEHOLDERS or not self.JWT_SECRET_KEY:
                problems.append("JWT_SECRET_KEY")
            if self.DEBUG:
                problems.append("DEBUG must be False in production")
            if self.ALIPAY_APP_ID == "2021000000000000":
                problems.append("ALIPAY_APP_ID")
            if self.MINIO_SECRET_KEY == "claywords_secret":
                problems.append("MINIO_SECRET_KEY")
            # P0: 生产环境 MinIO 必须走 TLS，否则预签名 URL 暴露在 HTTP 明文中
            if not self.MINIO_SECURE:
                problems.append("MINIO_SECURE must be True in production")
            # 生产环境支付/前端回跳 URL 必须 HTTPS
            if not self.ALIPAY_NOTIFY_URL.startswith("https://"):
                problems.append("ALIPAY_NOTIFY_URL must be HTTPS in production")
            if not self.ALIPAY_RETURN_URL.startswith("https://"):
                problems.append("ALIPAY_RETURN_URL must be HTTPS in production")
            # 兜底工作室必须显式注入（防派单全部失败时静默回退到空 ID）
            if not self.CENTRAL_STUDIO_ID:
                problems.append("CENTRAL_STUDIO_ID must be set in production")
            # 生产环境必须开启 ClamAV，否则 uploads.confirm 直接标 clean，等于无扫描
            if not self.CLAMAV_ENABLED:
                problems.append("CLAMAV_ENABLED must be True in production")
            if problems:
                raise ValueError(
                    "Insecure production configuration: "
                    + ", ".join(problems)
                    + ". Override via env vars / secrets before launching."
                )
        return self


settings = Settings()

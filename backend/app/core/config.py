"""Production Application Configuration

Phase Q10 P0: 生产环境配置
- DEBUG 关闭
- JWT 过期时间配置
- 环境区分
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


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


settings = Settings()

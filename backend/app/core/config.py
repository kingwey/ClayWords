"""Application Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database (默认 Postgres，测试可用 SQLite)
    DATABASE_URL: str = "postgresql+asyncpg://claywords:claywords_secret@localhost:5432/claywords"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "claywords"
    MINIO_SECRET_KEY: str = "claywords_secret"
    MINIO_BUCKET: str = "claywords"
    MINIO_SECURE: bool = False

    # Crypto (加密 pepper)
    CRYPTO_PEPPER: str = "dev_pepper_change_in_production"

    # JWT
    JWT_SECRET_KEY: str = "dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    LLM_PROVIDER: str = "tongyi"
    TONGYI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Alipay (Sandbox)
    ALIPAY_APP_ID: str = "2021000000000000"  # 沙箱 AppID
    ALIPAY_PRIVATE_KEY: str = ""  # RSA2 私钥
    ALIPAY_PUBLIC_KEY: str = ""  # 支付宝公钥
    ALIPAY_NOTIFY_URL: str = "http://localhost:8000/api/v1/payments/callback"
    ALIPAY_RETURN_URL: str = "http://localhost:3000/orders"


settings = Settings()

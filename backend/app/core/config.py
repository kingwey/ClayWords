"""Application Configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 允许的前端来源（逗号分隔）；同源部署时无需额外配置
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # 前端构建产物目录；设置后由后端同源托管（SPA）
    STATIC_DIR: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "claywords"
    MINIO_SECRET_KEY: str = "claywords_secret"
    MINIO_BUCKET: str = "claywords"

    # JWT
    JWT_SECRET_KEY: str = "dev_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    LLM_PROVIDER: str = "tongyi"
    TONGYI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""


settings = Settings()

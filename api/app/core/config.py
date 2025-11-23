"""
Configuration for FastAPI application.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# Explicitly load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
if env_path.exists():
    print(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RFP Bid Generation Dashboard"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./rfp_dashboard.db"
    # For PostgreSQL: postgresql://user:password@localhost/dbname

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000", "http://localhost:3300"]

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # WebSocket
    WS_MESSAGE_QUEUE: str = "websocket_messages"

    # Submission Settings
    MAX_CONCURRENT_SUBMISSIONS: int = 5
    SUBMISSION_RETRY_ATTEMPTS: int = 3
    SUBMISSION_RETRY_BACKOFF: int = 2

    # Portal Credentials (from environment)
    SAM_GOV_API_KEY: Optional[str] = None
    GSA_EBUY_USERNAME: Optional[str] = None
    GSA_EBUY_PASSWORD: Optional[str] = None

    # Notification Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@rfpbid.com"

    SLACK_WEBHOOK_URL: Optional[str] = None

    # Paths
    DATA_DIR: str = "./data"
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )

    def __init__(self, **kwargs):
        # Try to load from parent directory if not found in current
        import os
        from pathlib import Path
        
        parent_env = Path(__file__).parent.parent.parent.parent / ".env"
        if parent_env.exists():
            self.Config.env_file = str(parent_env)
            
        super().__init__(**kwargs)


settings = Settings()

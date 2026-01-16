from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    API_KEY: Optional[str] = None
    MODEL_NAME: str = "mistralai/devstral-2512:free"
    MAX_STEPS: int = 6
    LOG_LEVEL: str = "INFO"
    RATE_LIMIT_CALLS: int = 10
    RATE_LIMIT_PERIOD: int = 60
    
    # Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: Optional[str] = None
    AWS_ENDPOINT_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra env vars like langfuse_*

settings = Settings()

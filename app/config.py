# File: /app/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    DATABASE_URL: str = "postgresql://myuser:mysecretpassword@localhost:5432/trading_platform"
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT configuration
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Encryption configuration
    FERNET_KEY: str = "your-fernet-key-for-credential-encryption-change-this-in-production"
    
    # Optional additional settings
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Trading Platform API"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

# Create a global settings instance
settings = Settings()
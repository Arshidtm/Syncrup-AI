"""
Configuration management using Pydantic for type-safe settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Neo4j Database Configuration
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    
    # Groq API Configuration
    groq_api_key: str
    
    # Worker URLs
    python_worker_url: str = "http://localhost:8001"
    typescript_worker_url: str = "http://localhost:8002"
    
    # Logging Configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

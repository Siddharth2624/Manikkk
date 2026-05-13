"""Application configuration using Pydantic Settings."""

import json
from dataclasses import dataclass
from typing import Annotated, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


@dataclass
class TelemetryConfig:
    """Telemetry storage configuration."""

    enabled: bool = True
    """Master switch for telemetry"""

    persistence_enabled: bool = True
    """Whether to persist to database"""

    retention_days: int = 30
    """How long to keep telemetry records"""

    max_records: int = 10000
    """Maximum records before auto-cleanup"""

    cleanup_interval_hours: int = 24
    """How often to run cleanup job"""


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    environment: str = Field(default="development", description="Application environment")

    # Application
    app_name: str = Field(default="Academic Management System", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URL")
    mongodb_database: str = Field(default="academic_system", description="Database name")

    # JWT
    jwt_secret_key: str = Field(default="change-this-secret-key", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, description="Access token expiration")
    jwt_refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration")
    jwt_refresh_enabled: bool = Field(default=True, description="Enable refresh tokens")

    # CORS
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # File Upload
    max_upload_size: int = Field(default=10485760, description="Max upload size in bytes (10MB)")
    allowed_file_extensions: Annotated[List[str], NoDecode] = Field(
        default=[".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar"],
        description="Allowed file extensions"
    )
    upload_dir: str = Field(default="uploads", description="Upload directory")

    # Pagination
    default_page_size: int = Field(default=20, description="Default page size")
    max_page_size: int = Field(default=100, description="Maximum page size")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Parse CORS origins from JSON string, comma-separated string, or list."""
        if isinstance(v, str):
            v = v.strip()
            # Check if it's a JSON array format: ["url1", "url2"]
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass  # Fall through to comma-separated parsing
            # Comma-separated format: url1,url2
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_file_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v: str | List[str]) -> List[str]:
        """Parse file extensions from string or list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v


# Global settings instance
settings = Settings()

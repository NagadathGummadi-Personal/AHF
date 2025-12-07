"""
Middleware Configuration

Environment-based configuration for the API middleware.

Version: 1.0.0
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class AWSConfig(BaseModel):
    """AWS configuration."""
    region: str = Field(default="us-west-2")
    access_key_id: Optional[str] = Field(default=None)
    secret_access_key: Optional[str] = Field(default=None)
    endpoint_url: Optional[str] = Field(default=None)  # For LocalStack
    
    @classmethod
    def from_env(cls) -> "AWSConfig":
        """Load AWS config from environment variables."""
        return cls(
            region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
            access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        )


class S3StorageConfig(BaseModel):
    """S3 storage configuration."""
    tools_bucket: str = Field(default="ahf-tools")
    agents_bucket: str = Field(default="ahf-agents")
    workflows_bucket: str = Field(default="ahf-workflows")
    prompts_bucket: str = Field(default="ahf-prompts")
    
    @classmethod
    def from_env(cls) -> "S3StorageConfig":
        """Load S3 config from environment variables."""
        return cls(
            tools_bucket=os.environ.get("S3_TOOLS_BUCKET", "ahf-tools"),
            agents_bucket=os.environ.get("S3_AGENTS_BUCKET", "ahf-agents"),
            workflows_bucket=os.environ.get("S3_WORKFLOWS_BUCKET", "ahf-workflows"),
            prompts_bucket=os.environ.get("S3_PROMPTS_BUCKET", "ahf-prompts"),
        )


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_prefix: str = Field(default="/api/v1")
    
    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load API config from environment variables."""
        return cls(
            host=os.environ.get("API_HOST", "0.0.0.0"),
            port=int(os.environ.get("API_PORT", "8000")),
            debug=os.environ.get("API_DEBUG", "false").lower() == "true",
            cors_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
            api_prefix=os.environ.get("API_PREFIX", "/api/v1"),
        )


class Settings(BaseModel):
    """Application settings."""
    aws: AWSConfig = Field(default_factory=AWSConfig)
    s3: S3StorageConfig = Field(default_factory=S3StorageConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load all settings from environment."""
        return cls(
            aws=AWSConfig.from_env(),
            s3=S3StorageConfig.from_env(),
            api=APIConfig.from_env(),
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings.from_env()
    return _settings

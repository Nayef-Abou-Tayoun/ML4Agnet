"""Configuration management for ML Registry MCP Server."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    server_name: str = "ml-registry-mcp-server"
    server_version: str = "0.1.0"
    log_level: str = "INFO"
    
    # MCP Server Settings
    mcp_transport: str = "stdio"  # stdio, sse, or websocket
    mcp_port: int = 8080
    
    # Web UI Settings
    ui_enabled: bool = True
    ui_port: int = 8081
    ui_host: str = "0.0.0.0"
    
    # Database (for caching model metadata)
    database_url: str = "sqlite:///./ml_registry.db"
    
    # watsonx.ai Configuration (Phase 1)
    watsonx_enabled: bool = True
    watsonx_api_key: Optional[str] = None
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_project_id: Optional[str] = None
    watsonx_space_id: Optional[str] = None  # Alternative to project_id
    
    # Azure ML Configuration (Phase 2 - Future)
    azure_ml_enabled: bool = False
    azure_subscription_id: Optional[str] = None
    azure_resource_group: Optional[str] = None
    azure_workspace_name: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    
    # AWS SageMaker Configuration (Phase 3 - Future)
    sagemaker_enabled: bool = False
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    
    # Google Vertex AI Configuration (Phase 4 - Future)
    vertex_ai_enabled: bool = False
    gcp_project_id: Optional[str] = None
    gcp_location: str = "us-central1"
    gcp_credentials_path: Optional[str] = None
    
    # Performance Settings
    cache_ttl_seconds: int = 300  # Cache model list for 5 minutes
    request_timeout_seconds: int = 30
    max_concurrent_requests: int = 10
    
    # Security
    enable_auth: bool = False
    api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()


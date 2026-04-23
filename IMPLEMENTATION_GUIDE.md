# ML Registry MCP Server - Implementation Guide

## Overview

This guide provides complete implementation for a standalone MCP server that discovers and exposes **custom ML models** deployed to cloud platforms (watsonx.ai, Azure ML, AWS SageMaker, etc.) as MCP tools.

**Important**: This is for **ML inference models** (classification, regression, forecasting, anomaly detection, etc.), NOT for LLMs/foundation models.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              MCP Client (Claude, Cline, etc.)           │
└─────────────────────────────────────────────────────────┘
                         │
                         │ MCP Protocol
                         ▼
┌─────────────────────────────────────────────────────────┐
│           ML Registry MCP Server (This Project)         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Provider Plugins (Extensible)                    │  │
│  │  - watsonx.ai (Phase 1)                          │  │
│  │  - Azure ML (Phase 2)                            │  │
│  │  - AWS SageMaker (Phase 3)                       │  │
│  │  - Google Vertex AI (Phase 4)                    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Cloud ML Platform APIs
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Your Deployed ML Models                    │
│  - Fraud detection model                               │
│  - Customer churn predictor                            │
│  - Demand forecasting model                            │
│  - Sentiment classifier                                │
│  - Anomaly detector                                    │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: watsonx.ai Custom ML Models

### File 1: `src/config.py`

```python
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
        case_sensitive = False


settings = Settings()
```

### File 2: `src/providers/base.py`

```python
"""Base provider interface for ML model platforms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class ModelType(str, Enum):
    """Types of ML models."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    FORECASTING = "forecasting"
    CLUSTERING = "clustering"
    ANOMALY_DETECTION = "anomaly_detection"
    RECOMMENDATION = "recommendation"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    TIME_SERIES = "time_series"
    OTHER = "other"


@dataclass
class ModelMetadata:
    """Metadata for a deployed ML model."""
    
    # Identity
    id: str  # Unique identifier (deployment ID)
    name: str  # Human-readable name
    provider: str  # watsonx, azure_ml, sagemaker, etc.
    
    # Model Information
    model_type: ModelType
    framework: str  # scikit-learn, tensorflow, pytorch, xgboost, etc.
    version: Optional[str] = None
    description: Optional[str] = None
    
    # Deployment Information
    endpoint_url: str
    deployment_id: str
    status: str  # deployed, failed, pending, etc.
    
    # Input/Output Schema
    input_schema: Dict[str, Any]  # JSON schema for input
    output_schema: Dict[str, Any]  # JSON schema for output
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    
    # Performance Metrics (if available)
    accuracy: Optional[float] = None
    latency_ms: Optional[float] = None
    
    def to_mcp_tool_schema(self) -> Dict[str, Any]:
        """Convert model metadata to MCP tool schema."""
        return {
            "name": f"{self.provider}_{self.name.lower().replace(' ', '_').replace('-', '_')}",
            "description": self.description or f"{self.model_type.value} model: {self.name}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_data": {
                        "type": "object",
                        "description": "Input data for prediction",
                        "properties": self.input_schema
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Optional inference parameters",
                        "properties": {
                            "timeout": {
                                "type": "integer",
                                "description": "Request timeout in seconds",
                                "default": 30
                            }
                        }
                    }
                },
                "required": ["input_data"]
            }
        }


class MLProvider(ABC):
    """Abstract base class for ML platform providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration."""
        self.config = config
        self._client = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelMetadata]:
        """List all deployed models in the platform."""
        pass
    
    @abstractmethod
    async def get_model(self, model_id: str) -> ModelMetadata:
        """Get metadata for a specific model."""
        pass
    
    @abstractmethod
    async def predict(
        self,
        model_id: str,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a prediction using the model."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
```

### File 3: `src/providers/watsonx.py`

```python
"""watsonx.ai provider for custom ML models."""

import logging
from typing import Dict, List, Any, Optional
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.deployments import Deployments
from .base import MLProvider, ModelMetadata, ModelType

logger = logging.getLogger(__name__)


class WatsonxProvider(MLProvider):
    """Provider for watsonx.ai deployed ML models."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.url = config.get("url", "https://us-south.ml.cloud.ibm.com")
        self.project_id = config.get("project_id")
        self.space_id = config.get("space_id")
        
        if not self.api_key:
            raise ValueError("watsonx.ai API key is required")
        if not self.project_id and not self.space_id:
            raise ValueError("Either project_id or space_id is required")
    
    async def initialize(self) -> None:
        """Initialize watsonx.ai client."""
        try:
            credentials = Credentials(
                api_key=self.api_key,
                url=self.url
            )
            self._client = APIClient(credentials)
            
            if self.project_id:
                self._client.set.default_project(self.project_id)
            elif self.space_id:
                self._client.set.default_space(self.space_id)
            
            logger.info("watsonx.ai provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize watsonx.ai provider: {e}")
            raise
    
    async def list_models(self) -> List[ModelMetadata]:
        """List all deployed models in watsonx.ai."""
        if not self._client:
            await self.initialize()
        
        try:
            deployments = Deployments(self._client)
            deployment_list = deployments.get_details()
            
            models = []
            for deployment in deployment_list.get("resources", []):
                try:
                    metadata = self._parse_deployment(deployment)
                    models.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to parse deployment: {e}")
                    continue
            
            logger.info(f"Found {len(models)} deployed models in watsonx.ai")
            return models
            
        except Exception as e:
            logger.error(f"Failed to list watsonx.ai models: {e}")
            return []
    
    async def get_model(self, model_id: str) -> ModelMetadata:
        """Get metadata for a specific model."""
        if not self._client:
            await self.initialize()
        
        try:
            deployments = Deployments(self._client)
            deployment = deployments.get_details(model_id)
            return self._parse_deployment(deployment)
        except Exception as e:
            logger.error(f"Failed to get model {model_id}: {e}")
            raise
    
    async def predict(
        self,
        model_id: str,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a prediction using the deployed model."""
        if not self._client:
            await self.initialize()
        
        try:
            # Get deployment details
            deployments = Deployments(self._client)
            
            # Prepare scoring payload
            scoring_payload = {
                "input_data": [input_data]
            }
            
            if parameters:
                scoring_payload["parameters"] = parameters
            
            # Make prediction
            result = deployments.score(model_id, scoring_payload)
            
            return {
                "predictions": result.get("predictions", []),
                "model_id": model_id,
                "provider": "watsonx",
                "metadata": {
                    "scoring_id": result.get("scoring_id"),
                    "deployment_id": model_id
                }
            }
            
        except Exception as e:
            logger.error(f"Prediction failed for model {model_id}: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if watsonx.ai is accessible."""
        try:
            if not self._client:
                await self.initialize()
            
            # Try to list deployments as a health check
            deployments = Deployments(self._client)
            deployments.get_details()
            return True
        except Exception as e:
            logger.error(f"watsonx.ai health check failed: {e}")
            return False
    
    @property
    def provider_name(self) -> str:
        return "watsonx"
    
    def _parse_deployment(self, deployment: Dict[str, Any]) -> ModelMetadata:
        """Parse watsonx.ai deployment into ModelMetadata."""
        metadata = deployment.get("metadata", {})
        entity = deployment.get("entity", {})
        
        # Extract model information
        asset = entity.get("asset", {})
        model_id = asset.get("id", "")
        
        # Determine model type from tags or metadata
        tags = metadata.get("tags", [])
        model_type = self._infer_model_type(tags, entity)
        
        # Extract input/output schema
        input_schema = self._extract_input_schema(entity)
        output_schema = self._extract_output_schema(entity)
        
        return ModelMetadata(
            id=metadata.get("id", ""),
            name=metadata.get("name", "Unknown Model"),
            provider="watsonx",
            model_type=model_type,
            framework=entity.get("custom", {}).get("framework", "unknown"),
            version=metadata.get("asset_version"),
            description=metadata.get("description"),
            endpoint_url=entity.get("scoring_url", ""),
            deployment_id=metadata.get("id", ""),
            status=entity.get("status", {}).get("state", "unknown"),
            input_schema=input_schema,
            output_schema=output_schema,
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("modified_at"),
            tags={tag: "true" for tag in tags}
        )
    
    def _infer_model_type(self, tags: List[str], entity: Dict[str, Any]) -> ModelType:
        """Infer model type from tags and metadata."""
        tags_lower = [tag.lower() for tag in tags]
        
        if any(t in tags_lower for t in ["classification", "classifier"]):
            return ModelType.CLASSIFICATION
        elif any(t in tags_lower for t in ["regression", "regressor"]):
            return ModelType.REGRESSION
        elif any(t in tags_lower for t in ["forecasting", "forecast", "time-series"]):
            return ModelType.FORECASTING
        elif any(t in tags_lower for t in ["clustering", "cluster"]):
            return ModelType.CLUSTERING
        elif any(t in tags_lower for t in ["anomaly", "outlier"]):
            return ModelType.ANOMALY_DETECTION
        elif any(t in tags_lower for t in ["recommendation", "recommender"]):
            return ModelType.RECOMMENDATION
        elif any(t in tags_lower for t in ["nlp", "text", "sentiment"]):
            return ModelType.NLP
        elif any(t in tags_lower for t in ["vision", "image", "cv"]):
            return ModelType.COMPUTER_VISION
        else:
            return ModelType.OTHER
    
    def _extract_input_schema(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract input schema from deployment entity."""
        # Try to get schema from deployment metadata
        input_data_schema = entity.get("input_data_schema", {})
        
        if input_data_schema:
            return input_data_schema
        
        # Default schema if not available
        return {
            "fields": {
                "type": "array",
                "description": "Input features for prediction"
            }
        }
    
    def _extract_output_schema(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Extract output schema from deployment entity."""
        # Try to get schema from deployment metadata
        output_data_schema = entity.get("output_data_schema", {})
        
        if output_data_schema:
            return output_data_schema
        
        # Default schema if not available
        return {
            "predictions": {
                "type": "array",
                "description": "Model predictions"
            }
        }
```

## Usage Example

### 1. Deploy Your Custom Model to watsonx.ai

```python
# Example: Deploy a scikit-learn fraud detection model
from sklearn.ensemble import RandomForestClassifier
from ibm_watsonx_ai import APIClient

# Train your model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Deploy to watsonx.ai
client = APIClient(credentials)
client.set.default_project(project_id)

# Store model
model_details = client.repository.store_model(
    model=model,
    meta_props={
        "name": "fraud_detection_model",
        "type": "scikit-learn_1.0",
        "software_spec_uid": client.software_specifications.get_id_by_name("runtime-22.1-py3.9")
    }
)

# Deploy model
deployment = client.deployments.create(
    artifact_uid=model_details["metadata"]["id"],
    meta_props={
        "name": "fraud_detection_deployment",
        "online": {}
    }
)
```

### 2. Start ML Registry MCP Server

```bash
cd ml-registry-mcp-server
export WATSONX_API_KEY="your-api-key"
export WATSONX_PROJECT_ID="your-project-id"
python -m src.server
```

### 3. Use from MCP Client

```python
# The model is automatically discovered and exposed as an MCP tool
import mcp

client = mcp.Client("http://localhost:8080")

# List available models
tools = await client.list_tools()
# Returns: ["watsonx_fraud_detection_model", "watsonx_churn_predictor", ...]

# Make prediction
result = await client.call_tool(
    "watsonx_fraud_detection_model",
    {
        "input_data": {
            "fields": ["amount", "merchant_category", "time_of_day"],
            "values": [[150.00, "retail", "14:30"]]
        }
    }
)

print(result)
# Output: {"predictions": [{"fraud_probability": 0.85, "is_fraud": true}]}
```

### 4. Use from Claude Desktop

```json
// ~/.config/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "ml-models": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/ml-registry-mcp-server",
      "env": {
        "WATSONX_API_KEY": "your-key",
        "WATSONX_PROJECT_ID": "your-project"
      }
    }
  }
}
```

Then in Claude:
```
You: "Check if this transaction is fraudulent: amount=$500, merchant=electronics, time=2am"

Claude: [Calls watsonx_fraud_detection_model tool]
"Based on the fraud detection model, this transaction has an 85% probability of being fraudulent."
```

## Next Steps

1. Implement remaining files:
   - `src/__init__.py`
   - `src/registry.py` - Model registry with caching
   - `src/server.py` - Main MCP server
   - `src/mcp/tools.py` - MCP tool generation

2. Add support for more model types:
   - Batch prediction
   - Model versioning
   - A/B testing

3. Implement additional providers:
   - Azure ML (Phase 2)
   - AWS SageMaker (Phase 3)
   - Google Vertex AI (Phase 4)

## Key Differences from LLM Models

| Aspect | LLM Models | Custom ML Models |
|--------|-----------|------------------|
| Input | Text prompts | Structured data (JSON) |
| Output | Generated text | Predictions (numbers, classes) |
| Use Case | Chat, generation | Classification, regression, forecasting |
| Schema | Flexible | Strict input/output schema |
| Examples | GPT, Claude, Llama | Fraud detection, churn prediction, demand forecasting |

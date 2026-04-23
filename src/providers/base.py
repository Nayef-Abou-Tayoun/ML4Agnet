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
    
    # Deployment Information
    endpoint_url: str
    deployment_id: str
    status: str  # deployed, failed, pending, etc.
    
    # Input/Output Schema
    input_schema: Dict[str, Any]  # JSON schema for input
    output_schema: Dict[str, Any]  # JSON schema for output
    
    # Optional fields with defaults
    version: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    accuracy: Optional[float] = None
    latency_ms: Optional[float] = None
    
    def to_mcp_tool_schema(self) -> Dict[str, Any]:
        """Convert model metadata to MCP tool schema.
        
        Exposes each input field directly at the top level so agents like WxO
        can see individual parameters with their types (string, number, etc.).
        """
        # Start with the input schema properties (flattened)
        properties = {}
        required_fields = []
        
        # If input_schema has a 'fields' property (watsonx format), extract field definitions
        if "fields" in self.input_schema:
            fields_def = self.input_schema["fields"]
            if isinstance(fields_def, dict) and fields_def.get("type") == "array":
                # This is a generic array schema - create individual field parameters
                # For now, we'll create a generic 'values' parameter
                properties["values"] = {
                    "type": "array",
                    "description": "Input values for prediction (array of numbers or strings)",
                    "items": {
                        "oneOf": [
                            {"type": "number"},
                            {"type": "string"}
                        ]
                    }
                }
                required_fields.append("values")
            else:
                # Direct field definitions
                properties.update(self.input_schema)
        else:
            # Use input_schema properties directly
            properties.update(self.input_schema)
        
        # Add optional parameters field
        properties["parameters"] = {
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
        
        return {
            "name": f"{self.provider}_{self.name.lower().replace(' ', '_').replace('-', '_')}",
            "description": self.description or f"{self.model_type.value} model: {self.name}",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required_fields if required_fields else []
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

# Made with Bob

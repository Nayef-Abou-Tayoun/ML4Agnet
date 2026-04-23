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
    
    def to_mcp_tool_schema(self, custom_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert model metadata to MCP tool schema.
        
        Args:
            custom_schema: Optional custom schema from schema manager
        
        If custom_schema is provided, uses it to generate a more specific schema.
        Otherwise, accepts the full watsonx.ai input_data structure directly.
        """
        # Check if we have a custom schema
        if custom_schema and custom_schema.get("fields"):
            # Build schema from custom field definitions
            field_properties = {}
            required_fields = []
            
            for field in custom_schema["fields"]:
                field_name = field["name"]
                field_type = field["type"]
                
                # Map custom types to JSON schema types
                type_mapping = {
                    "string": "string",
                    "integer": "integer",
                    "float": "number",
                    "boolean": "boolean"
                }
                
                field_properties[field_name] = {
                    "type": type_mapping.get(field_type, "string"),
                    "description": field.get("description", f"{field_name} field")
                }
                
                if field.get("required", False):
                    required_fields.append(field_name)
            
            properties = {
                "input_data": {
                    "type": "array",
                    "description": "Array of input data objects",
                    "items": {
                        "type": "object",
                        "properties": field_properties,
                        "required": required_fields
                    }
                }
            }
        else:
            # Default schema - accepts full watsonx.ai input_data structure
            properties = {
                "input_data": {
                    "type": "array",
                    "description": "Array of input data objects with fields and values",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fields": {
                                "type": "array",
                                "description": "Array of field names",
                                "items": {"type": "string"}
                            },
                            "values": {
                                "type": "array",
                                "description": "Array of value arrays (one per row)",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "oneOf": [
                                            {"type": "number"},
                                            {"type": "string"}
                                        ]
                                    }
                                }
                            }
                        },
                        "required": ["fields", "values"]
                    }
                }
            }
        
        # Add optional parameters
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

# Made with Bob

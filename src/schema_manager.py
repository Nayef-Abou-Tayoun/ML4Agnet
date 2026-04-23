"""Model schema management for custom input field definitions."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FieldSchema(BaseModel):
    """Schema for a single input field."""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Data type: string, integer, float, boolean")
    required: bool = Field(default=True, description="Whether field is required")
    description: Optional[str] = Field(None, description="Field description")


class ModelSchema(BaseModel):
    """Schema for a model's input fields."""
    model_id: str = Field(..., description="Model deployment ID")
    model_name: str = Field(..., description="Model name")
    fields: List[FieldSchema] = Field(default_factory=list, description="Input fields")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class SchemaManager:
    """Manages custom schemas for ML models."""
    
    def __init__(self, schema_file: str = "model_schemas.json"):
        """Initialize schema manager.
        
        Args:
            schema_file: Path to JSON file storing schemas
        """
        self.schema_file = Path(schema_file)
        self.schemas: Dict[str, ModelSchema] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load schemas from file."""
        if self.schema_file.exists():
            try:
                with open(self.schema_file, 'r') as f:
                    data = json.load(f)
                    for model_id, schema_data in data.items():
                        self.schemas[model_id] = ModelSchema(**schema_data)
                logger.info(f"Loaded {len(self.schemas)} model schemas")
            except Exception as e:
                logger.error(f"Failed to load schemas: {e}")
                self.schemas = {}
        else:
            logger.info("No existing schema file found, starting fresh")
    
    def _save_schemas(self):
        """Save schemas to file."""
        try:
            data = {
                model_id: schema.model_dump()
                for model_id, schema in self.schemas.items()
            }
            with open(self.schema_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.schemas)} model schemas")
        except Exception as e:
            logger.error(f"Failed to save schemas: {e}")
    
    def get_schema(self, model_id: str) -> Optional[ModelSchema]:
        """Get schema for a model.
        
        Args:
            model_id: Model deployment ID
            
        Returns:
            ModelSchema if exists, None otherwise
        """
        return self.schemas.get(model_id)
    
    def set_schema(self, schema: ModelSchema) -> bool:
        """Set or update schema for a model.
        
        Args:
            schema: Model schema to save
            
        Returns:
            True if successful
        """
        try:
            from datetime import datetime
            schema.updated_at = datetime.utcnow().isoformat()
            self.schemas[schema.model_id] = schema
            self._save_schemas()
            logger.info(f"Updated schema for model {schema.model_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set schema: {e}")
            return False
    
    def delete_schema(self, model_id: str) -> bool:
        """Delete schema for a model.
        
        Args:
            model_id: Model deployment ID
            
        Returns:
            True if deleted, False if not found
        """
        if model_id in self.schemas:
            del self.schemas[model_id]
            self._save_schemas()
            logger.info(f"Deleted schema for model {model_id}")
            return True
        return False
    
    def list_schemas(self) -> List[ModelSchema]:
        """List all schemas.
        
        Returns:
            List of all model schemas
        """
        return list(self.schemas.values())
    
    def generate_mcp_schema(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Generate MCP tool input schema from custom schema.
        
        Args:
            model_id: Model deployment ID
            
        Returns:
            MCP input schema dict or None if no custom schema
        """
        schema = self.get_schema(model_id)
        if not schema or not schema.fields:
            return None
        
        # Build properties for each field
        properties = {}
        required_fields = []
        
        for field in schema.fields:
            field_schema = {
                "description": field.description or f"{field.name} field"
            }
            
            # Map types
            if field.type == "integer":
                field_schema["type"] = "integer"
            elif field.type == "float":
                field_schema["type"] = "number"
            elif field.type == "boolean":
                field_schema["type"] = "boolean"
            else:  # string
                field_schema["type"] = "string"
            
            properties[field.name] = field_schema
            
            if field.required:
                required_fields.append(field.name)
        
        # Return schema in MCP format
        return {
            "type": "object",
            "properties": {
                "input_data": {
                    "type": "array",
                    "description": f"Input data for {schema.model_name}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fields": {
                                "type": "array",
                                "description": "Field names",
                                "items": {"type": "string"},
                                "default": [f.name for f in schema.fields]
                            },
                            "values": {
                                "type": "array",
                                "description": "Field values (one array per row)",
                                "items": {
                                    "type": "array",
                                    "description": f"Values for fields: {', '.join(f.name for f in schema.fields)}"
                                }
                            }
                        },
                        "required": ["fields", "values"]
                    }
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


# Global schema manager instance
_schema_manager: Optional[SchemaManager] = None


def get_schema_manager() -> SchemaManager:
    """Get global schema manager instance."""
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = SchemaManager()
    return _schema_manager

# Made with Bob

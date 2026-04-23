"""watsonx.ai provider for custom ML models."""

import json
import logging
from typing import Dict, List, Any, Optional
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.deployments import Deployments
from .base import MLProvider, ModelMetadata, ModelType

logger = logging.getLogger(__name__)


def convert_to_numeric(value):
    """Convert a value to numeric type if possible.
    
    Args:
        value: Value to convert (can be string, int, float, or other)
        
    Returns:
        Numeric value (int or float) if conversion possible, otherwise original value
    """
    if isinstance(value, (int, float)):
        return value
    
    if isinstance(value, str):
        try:
            # Try int first
            if '.' not in value:
                return int(value)
            # Try float
            return float(value)
        except (ValueError, TypeError):
            return value
    
    return value


def convert_values_to_numeric(data):
    """Recursively convert string numbers to numeric types in nested structures.
    
    Args:
        data: Data structure (list, dict, or primitive)
        
    Returns:
        Data with string numbers converted to numeric types
    """
    if isinstance(data, list):
        return [convert_values_to_numeric(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_values_to_numeric(value) for key, value in data.items()}
    else:
        return convert_to_numeric(data)


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
            # Log the incoming request
            logger.info(f"watsonx provider received input_data type: {type(input_data)}")
            logger.info(f"watsonx provider received input_data: {json.dumps(input_data, indent=2)}")
            
            # Get deployment details
            deployments = Deployments(self._client)
            
            # Handle different input formats
            # Check if input_data is already a list (from tools.py transformation)
            if isinstance(input_data, list):
                # Already in correct watsonx.ai format: [{"fields": [...], "values": [...]}]
                logger.info("Input is already a list - using directly")
                scoring_payload = {"input_data": input_data}
                if parameters:
                    scoring_payload["parameters"] = parameters
            # Check if input_data has nested "input_data" key
            elif isinstance(input_data, dict) and "input_data" in input_data:
                # WxO format: {"input_data": {"fields": [...]}, "parameters": {...}}
                wxo_input = input_data["input_data"]
                wxo_params = input_data.get("parameters", {})
                
                # Check if wxo_input is already a list (correct watsonx format)
                if isinstance(wxo_input, list):
                    # Already in correct format: [{"fields": [...], "values": [...]}]
                    scoring_payload = {"input_data": wxo_input}
                    if parameters:
                        scoring_payload["parameters"] = parameters
                    elif wxo_params:
                        scoring_payload["parameters"] = wxo_params
                # Check if already in correct watsonx.ai format (both fields and values present)
                elif isinstance(wxo_input, dict) and "fields" in wxo_input and "values" in wxo_input:
                    # Already in correct watsonx.ai format
                    # Convert any string numbers to numeric types
                    try:
                        values = convert_values_to_numeric(wxo_input["values"])
                        scoring_payload = {
                            "input_data": [{
                                "fields": wxo_input["fields"],
                                "values": values
                            }]
                        }
                    except KeyError as e:
                        logger.error(f"KeyError accessing 'values': {e}")
                        logger.error(f"wxo_input keys: {wxo_input.keys()}")
                        logger.error(f"wxo_input content: {wxo_input}")
                        raise
                elif isinstance(wxo_input, dict) and "fields" in wxo_input and "records" in wxo_input:
                    # Convert records to values format (records is an alias for values)
                    # Also convert any string numbers to numeric types
                    records = convert_values_to_numeric(wxo_input["records"])
                    scoring_payload = {
                        "input_data": [{
                            "fields": wxo_input["fields"],
                            "values": records
                        }]
                    }
                elif "fields" in wxo_input:
                    # Convert fields to values format
                    fields = wxo_input["fields"]
                    if isinstance(fields, list) and len(fields) > 0:
                        # Convert list of dicts to list of values
                        if isinstance(fields[0], dict):
                            # Get field names and values
                            field_names = list(fields[0].keys())
                            values = [[record[field] for field in field_names] for record in fields]
                            
                            scoring_payload = {
                                "input_data": [{
                                    "fields": field_names,
                                    "values": values
                                }]
                            }
                        else:
                            # Already in array format
                            scoring_payload = {
                                "input_data": [{
                                    "values": fields
                                }]
                            }
                    else:
                        scoring_payload = {
                            "input_data": [wxo_input]
                        }
                elif "values" in wxo_input:
                    # Only values present - need to wrap and convert
                    values = wxo_input["values"]
                    # Convert string numbers to numeric types
                    values = convert_values_to_numeric(values)
                    # Wrap single array into list(list) format
                    if isinstance(values, list) and len(values) > 0:
                        if not isinstance(values[0], list):
                            # Single row: [1129, 0] -> [[1129, 0]]
                            values = [values]
                    scoring_payload = {
                        "input_data": [{
                            "values": values
                        }]
                    }
                else:
                    # Unknown format, pass as-is
                    scoring_payload = {
                        "input_data": [wxo_input]
                    }
                
                # Merge parameters
                if parameters:
                    scoring_payload["parameters"] = parameters
                elif wxo_params:
                    scoring_payload["parameters"] = wxo_params
            else:
                # Direct format: check if input_data is already a list
                if isinstance(input_data, list) and len(input_data) > 0:
                    # If it's already a list of dicts with fields/values, use as-is
                    if isinstance(input_data[0], dict) and ("fields" in input_data[0] or "values" in input_data[0]):
                        scoring_payload = {"input_data": input_data}
                        if parameters:
                            scoring_payload["parameters"] = parameters
                    else:
                        # Otherwise wrap it
                        scoring_payload = {"input_data": [input_data]}
                        if parameters:
                            scoring_payload["parameters"] = parameters
                else:
                    # Single item, wrap it
                    scoring_payload = {"input_data": [input_data]}
                    if parameters:
                        scoring_payload["parameters"] = parameters
            
            # Make prediction
            logger.info(f"Calling watsonx.ai with payload: {scoring_payload}")
            result = deployments.score(model_id, scoring_payload)
            logger.info(f"watsonx.ai response: {result}")
            
            if result is None:
                logger.error("watsonx.ai returned None")
                raise ValueError("watsonx.ai API returned None")
            
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
            endpoint_url=entity.get("scoring_url", ""),
            deployment_id=metadata.get("id", ""),
            status=entity.get("status", {}).get("state", "unknown"),
            input_schema=input_schema,
            output_schema=output_schema,
            version=metadata.get("asset_version"),
            description=metadata.get("description"),
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

# Made with Bob

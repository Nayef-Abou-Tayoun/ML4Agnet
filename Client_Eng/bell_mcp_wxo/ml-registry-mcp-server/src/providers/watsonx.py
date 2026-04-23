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

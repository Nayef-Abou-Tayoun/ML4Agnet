"""Model registry with caching and provider management."""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .config import settings
from .providers.base import MLProvider, ModelMetadata

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Central registry for ML models across all providers."""
    
    def __init__(self):
        self.providers: Dict[str, MLProvider] = {}
        self._cache: Dict[str, List[ModelMetadata]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all enabled providers."""
        if self._initialized:
            logger.info("Registry already initialized")
            return
        
        logger.info("Initializing model registry...")
        
        # Initialize watsonx.ai provider if enabled
        if settings.watsonx_enabled:
            try:
                from .providers.watsonx import WatsonxProvider
                logger.info("Initializing watsonx.ai provider...")
                provider = WatsonxProvider({
                    "api_key": settings.watsonx_api_key,
                    "url": settings.watsonx_url,
                    "project_id": settings.watsonx_project_id,
                    "space_id": settings.watsonx_space_id
                })
                await provider.initialize()
                self.providers["watsonx"] = provider
                logger.info("watsonx.ai provider initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize watsonx.ai provider: {e}")
        
        # Initialize Azure ML provider if enabled (Phase 2)
        if settings.azure_ml_enabled:
            logger.warning("Azure ML provider not yet implemented")
        
        # Initialize AWS SageMaker provider if enabled (Phase 3)
        if settings.sagemaker_enabled:
            logger.warning("AWS SageMaker provider not yet implemented")
        
        # Initialize Google Vertex AI provider if enabled (Phase 4)
        if settings.vertex_ai_enabled:
            logger.warning("Google Vertex AI provider not yet implemented")
        
        self._initialized = True
        logger.info(f"Registry initialized with {len(self.providers)} provider(s)")
    
    async def list_all_models(self, force_refresh: bool = False) -> List[ModelMetadata]:
        """List models from all providers with caching.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of all discovered models across all providers
        """
        if not self._initialized:
            await self.initialize()
        
        all_models = []
        
        for provider_name, provider in self.providers.items():
            try:
                # Check cache
                if not force_refresh and provider_name in self._cache:
                    cache_age = datetime.now() - self._cache_timestamps[provider_name]
                    if cache_age < timedelta(seconds=settings.cache_ttl_seconds):
                        logger.debug(f"Using cached models for {provider_name}")
                        all_models.extend(self._cache[provider_name])
                        continue
                
                # Fetch from provider
                logger.info(f"Fetching models from {provider_name}...")
                models = await provider.list_models()
                self._cache[provider_name] = models
                self._cache_timestamps[provider_name] = datetime.now()
                all_models.extend(models)
                logger.info(f"Fetched {len(models)} models from {provider_name}")
                
            except Exception as e:
                logger.error(f"Failed to list models from {provider_name}: {e}")
                continue
        
        logger.info(f"Total models discovered: {len(all_models)}")
        return all_models
    
    async def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get a specific model by ID.
        
        Args:
            model_id: Unique model identifier
            
        Returns:
            Model metadata if found, None otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        for provider_name, provider in self.providers.items():
            try:
                logger.debug(f"Searching for model {model_id} in {provider_name}")
                model = await provider.get_model(model_id)
                if model:
                    logger.info(f"Found model {model_id} in {provider_name}")
                    return model
            except Exception as e:
                logger.debug(f"Model {model_id} not found in {provider_name}: {e}")
                continue
        
        logger.warning(f"Model {model_id} not found in any provider")
        return None
    
    async def predict(
        self,
        model_id: str,
        input_data: dict,
        parameters: Optional[dict] = None
    ) -> dict:
        """Make prediction using a model.
        
        Args:
            model_id: Unique model identifier
            input_data: Input data for prediction
            parameters: Optional inference parameters
            
        Returns:
            Prediction result
            
        Raises:
            ValueError: If model not found
        """
        if not self._initialized:
            await self.initialize()
        
        for provider_name, provider in self.providers.items():
            try:
                logger.info(f"Attempting prediction with {provider_name} for model {model_id}")
                result = await provider.predict(model_id, input_data, parameters)
                logger.info(f"Prediction successful with {provider_name}")
                return result
            except Exception as e:
                logger.debug(f"Prediction failed with {provider_name}: {e}")
                continue
        
        error_msg = f"Model {model_id} not found in any provider"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers.
        
        Returns:
            Dictionary mapping provider names to health status
        """
        if not self._initialized:
            await self.initialize()
        
        health_status = {}
        
        for provider_name, provider in self.providers.items():
            try:
                is_healthy = await provider.health_check()
                health_status[provider_name] = is_healthy
                logger.info(f"{provider_name} health check: {'OK' if is_healthy else 'FAILED'}")
            except Exception as e:
                logger.error(f"{provider_name} health check error: {e}")
                health_status[provider_name] = False
        
        return health_status
    
    def clear_cache(self, provider_name: Optional[str] = None):
        """Clear model cache.
        
        Args:
            provider_name: If specified, clear cache for specific provider only
        """
        if provider_name:
            if provider_name in self._cache:
                del self._cache[provider_name]
                del self._cache_timestamps[provider_name]
                logger.info(f"Cleared cache for {provider_name}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("Cleared all cache")
    
    def get_provider_stats(self) -> Dict[str, dict]:
        """Get statistics about providers and cached models.
        
        Returns:
            Dictionary with provider statistics
        """
        stats = {}
        
        for provider_name, provider in self.providers.items():
            cached_models = len(self._cache.get(provider_name, []))
            cache_age = None
            
            if provider_name in self._cache_timestamps:
                cache_age = (datetime.now() - self._cache_timestamps[provider_name]).total_seconds()
            
            stats[provider_name] = {
                "provider_type": provider.provider_name,
                "cached_models": cached_models,
                "cache_age_seconds": cache_age,
                "cache_valid": cache_age < settings.cache_ttl_seconds if cache_age else False
            }
        
        return stats

# Made with Bob

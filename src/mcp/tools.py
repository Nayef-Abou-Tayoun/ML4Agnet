"""MCP tool generation from ML models."""

import logging
from typing import List, Dict, Any
from ..providers.base import ModelMetadata
from ..registry import ModelRegistry

logger = logging.getLogger(__name__)


def generate_mcp_tools(models: List[ModelMetadata]) -> List[Dict[str, Any]]:
    """Convert ML models to MCP tool definitions.
    
    Args:
        models: List of model metadata objects
        
    Returns:
        List of MCP tool schemas
    """
    tools = []
    
    for model in models:
        try:
            tool = model.to_mcp_tool_schema()
            tools.append(tool)
            logger.debug(f"Generated MCP tool for model: {model.name}")
        except Exception as e:
            logger.error(f"Failed to generate tool for model {model.name}: {e}")
            continue
    
    logger.info(f"Generated {len(tools)} MCP tools from {len(models)} models")
    return tools


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    registry: ModelRegistry
) -> Dict[str, Any]:
    """Execute an MCP tool (call ML model).
    
    Args:
        tool_name: Name of the tool to execute (format: provider_model_name)
        arguments: Tool arguments with flattened input fields and optional parameters
        registry: Model registry instance
        
    Returns:
        Prediction result from the model
        
    Raises:
        ValueError: If tool/model not found
    """
    logger.info(f"Executing tool: {tool_name}")
    logger.debug(f"Tool arguments: {arguments}")
    
    # Get all models
    models = await registry.list_all_models()
    
    # Find matching model
    for model in models:
        expected_tool_name = f"{model.provider}_{model.name.lower().replace(' ', '_').replace('-', '_')}"
        
        if tool_name == expected_tool_name:
            logger.info(f"Found matching model: {model.name} (ID: {model.id})")
            
            # Extract parameters (if present)
            parameters = arguments.get("parameters")
            
            # Reconstruct input_data from flattened arguments
            # Remove 'parameters' from arguments to get just the input fields
            input_data = {k: v for k, v in arguments.items() if k != "parameters"}
            
            # If there's a 'values' field, wrap it properly for watsonx
            if "values" in input_data and len(input_data) == 1:
                values = input_data["values"]
                # watsonx expects list(list), so if we have a single list, wrap it
                if isinstance(values, list) and len(values) > 0:
                    # Check if it's already list(list) or just list
                    if not isinstance(values[0], list):
                        # Single row - wrap it: [1129, 0] -> [[1129, 0]]
                        values = [values]
                input_data = {"values": values}
            
            logger.debug(f"Reconstructed input_data: {input_data}")
            
            # Make prediction
            try:
                result = await registry.predict(
                    model.id,
                    input_data,
                    parameters
                )
                logger.info(f"Prediction successful for {tool_name}")
                return result
            except Exception as e:
                logger.error(f"Prediction failed for {tool_name}: {e}")
                raise
    
    # Tool not found
    available_tools = [f"{m.provider}_{m.name.lower().replace(' ', '_').replace('-', '_')}" for m in models[:5]]
    error_msg = f"Tool {tool_name} not found. Available tools: {available_tools}"
    logger.error(error_msg)
    raise ValueError(error_msg)


def format_tool_result(result: Dict[str, Any]) -> str:
    """Format prediction result for MCP response.
    
    Args:
        result: Raw prediction result from model
        
    Returns:
        Formatted string representation
    """
    import json
    
    try:
        # Pretty print JSON result
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Failed to format result: {e}")
        return str(result)


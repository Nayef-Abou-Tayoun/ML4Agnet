"""MCP tool generation from ML models."""

import logging
from typing import List, Dict, Any
from ..providers.base import ModelMetadata
from ..registry import ModelRegistry


def convert_to_numeric(value):
    """Convert a value to numeric type if possible."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            if '.' not in value:
                return int(value)
            return float(value)
        except (ValueError, TypeError):
            return value
    return value


def convert_values_to_numeric(data):
    """Recursively convert string numbers to numeric types."""
    if isinstance(data, list):
        return [convert_values_to_numeric(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_values_to_numeric(value) for key, value in data.items()}
    else:
        return convert_to_numeric(data)

logger = logging.getLogger(__name__)


def generate_mcp_tools(models: List[ModelMetadata]) -> List[Dict[str, Any]]:
    """Convert ML models to MCP tool definitions.
    
    Args:
        models: List of model metadata objects
        
    Returns:
        List of MCP tool schemas
    """
    from ..schema_manager import get_schema_manager
    
    tools = []
    schema_mgr = get_schema_manager()
    
    for model in models:
        try:
            # Check if there's a custom schema for this model
            custom_schema_obj = schema_mgr.get_schema(model.id)
            if custom_schema_obj:
                logger.info(f"Using custom schema for model: {model.name}")
                # Convert ModelSchema to dict
                custom_schema_dict = {
                    "model_id": custom_schema_obj.model_id,
                    "model_name": custom_schema_obj.model_name,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.type,
                            "required": f.required,
                            "description": f.description
                        }
                        for f in custom_schema_obj.fields
                    ]
                }
                tool = model.to_mcp_tool_schema(custom_schema=custom_schema_dict)
            else:
                logger.debug(f"Using default schema for model: {model.name}")
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
            
            logger.info(f"Raw arguments received: {arguments}")
            
            # Check if we need to transform from custom schema format to watsonx.ai format
            if "input_data" not in arguments:
                # Custom schema format: individual fields sent by WxO
                # Need to transform to watsonx.ai format: {fields: [...], values: [[...]]}
                
                # Remove parameters from the field data
                field_data = {k: v for k, v in arguments.items() if k != "parameters"}
                
                if field_data:
                    # Transform individual fields to watsonx.ai format
                    fields = list(field_data.keys())
                    values = [list(field_data.values())]
                    
                    # Convert string numbers to numeric types before creating the structure
                    values = convert_values_to_numeric(values)
                    
                    input_data = [{
                        "fields": fields,
                        "values": values
                    }]
                    logger.info(f"Transformed {len(fields)} individual fields to watsonx.ai format")
                    logger.info(f"Fields: {fields}")
                    logger.info(f"Values: {values}")
                else:
                    # No fields provided
                    raise ValueError("No input fields provided")
            else:
                # input_data is already provided
                input_data = arguments.get("input_data")
                # Convert string numbers to numeric types
                input_data = convert_values_to_numeric(input_data)
            
            logger.info(f"Final input_data for prediction: {input_data}")
            
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


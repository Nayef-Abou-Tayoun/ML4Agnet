# MCP Tool Schema Changes for WxO Integration

## Problem
WxO was showing input parameters as a single nested `input_data` object, preventing the agent from seeing individual input fields with their proper types (string, number, etc.).

**Before:**
```json
{
  "name": "watsonx_model_name",
  "inputSchema": {
    "type": "object",
    "properties": {
      "input_data": {
        "type": "object",
        "description": "Input data for prediction",
        "properties": { ... }
      },
      "parameters": { ... }
    },
    "required": ["input_data"]
  }
}
```

## Solution
Flattened the MCP tool schema to expose each input field directly at the top level, allowing WxO to see individual parameters with their types.

**After:**
```json
{
  "name": "watsonx_model_name",
  "inputSchema": {
    "type": "object",
    "properties": {
      "values": {
        "type": "array",
        "description": "Input values for prediction (array of numbers or strings)",
        "items": {
          "oneOf": [
            {"type": "number"},
            {"type": "string"}
          ]
        }
      },
      "parameters": { ... }
    },
    "required": ["values"]
  }
}
```

## Changes Made

### 1. Updated `src/providers/base.py`
Modified `ModelMetadata.to_mcp_tool_schema()` method:
- Flattens input_schema properties to top level
- Extracts field definitions from watsonx format
- Creates individual parameters with proper types
- Maintains backward compatibility

### 2. Updated `src/mcp/tools.py`
Modified `execute_tool()` function:
- Handles flattened input format from WxO
- Reconstructs `input_data` for watsonx provider
- Separates `parameters` from input fields
- Supports both `values` array format and individual fields

## Benefits
1. **Better Agent Understanding**: WxO can now see each input field with its type
2. **Type Safety**: String vs number types are explicit in the schema
3. **Improved UX**: Users can provide inputs field-by-field instead of nested objects
4. **Flexibility**: Supports both array format (`values`) and individual fields

## Testing
After deployment, verify in WxO that:
1. Individual input fields are visible (not nested in `input_data`)
2. Each field shows its proper type (string, number, array)
3. Predictions work correctly with the new format
4. String-to-number conversion still functions properly

## Deployment
- Committed: a9c212d
- GitHub: https://github.com/Nayef-Abou-Tayoun/ML4Agnet
- IBM Cloud Code Engine: Deploying revision mlregistry12-00020
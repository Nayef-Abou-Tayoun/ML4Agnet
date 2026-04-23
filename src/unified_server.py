"""Unified server supporting both MCP (Context Forge) and REST API (direct WxO).

This server provides:
1. MCP protocol endpoints (HTTP/SSE) for Context Forge
2. REST API endpoints for direct watsonx Orchestrate integration
3. Web UI for model discovery and documentation

All running on a single port with different endpoint paths.
"""

import logging
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json

from .config import settings
from .registry import ModelRegistry
from .mcp.tools import generate_mcp_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Registry Unified Server",
    description="Supports both MCP (Context Forge) and REST API (watsonx Orchestrate)",
    version=settings.server_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = ModelRegistry()


@app.on_event("startup")
async def startup():
    """Initialize registry on startup."""
    logger.info("Starting Unified ML Registry Server...")
    await registry.initialize()
    logger.info("Unified server started - MCP + REST API + UI ready")


# ============================================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint showing all available integrations."""
    models = await registry.list_all_models()
    return {
        "name": "ML Registry Unified Server",
        "version": settings.server_version,
        "description": "Multi-protocol ML model registry",
        "models_count": len(models),
        "integrations": {
            "context_forge": {
                "description": "MCP protocol for Context Forge",
                "endpoints": {
                    "mcp": "/mcp",
                    "sse": "/sse",
                    "tools": "/mcp/tools"
                }
            },
            "watsonx_orchestrate": {
                "description": "Direct REST API integration",
                "endpoints": {
                    "models": "/api/models",
                    "predict": "/api/models/{model_name}/predict",
                    "openapi": "/api/openapi.json",
                    "docs": "/api/docs"
                }
            },
            "web_ui": {
                "description": "Web interface for model discovery",
                "url": "/ui"
            }
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        provider_health = await registry.health_check()
        models = await registry.list_all_models()
        return {
            "status": "healthy",
            "providers": provider_health,
            "models_count": len(models),
            "protocols": ["mcp", "rest", "ui"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


# ============================================================================
# MCP PROTOCOL ENDPOINTS (for Context Forge)
# ============================================================================

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP JSON-RPC endpoint for Context Forge."""
    body: Optional[Dict[str, Any]] = None
    try:
        body = await request.json()
        if body:
            logger.info(f"MCP request: {body.get('method')}")
            response = await handle_mcp_request(body)
            return JSONResponse(content=response)
        else:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                },
                status_code=400
            )
    except Exception as e:
        logger.error(f"MCP error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": body.get("id") if body else None
            },
            status_code=500
        )


@app.get("/sse")
async def sse_endpoint():
    """Server-Sent Events endpoint for MCP streaming."""
    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'server': 'ml-registry'})}\n\n"
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE connection closed")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/mcp/tools")
async def mcp_tools_list():
    """List MCP tools (for Context Forge discovery)."""
    try:
        models = await registry.list_all_models()
        tools = generate_mcp_tools(models)
        return {"tools": tools, "count": len(tools)}
    except Exception as e:
        logger.error(f"Error listing MCP tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REST API ENDPOINTS (for direct watsonx Orchestrate)
# ============================================================================

@app.get("/api/models")
async def list_models():
    """List all models - REST API for watsonx Orchestrate."""
    try:
        models = await registry.list_all_models()
        return {
            "models": [
                {
                    "name": m.name,
                    "id": m.id,
                    "description": m.description or f"{m.model_type.value} model",
                    "type": m.model_type.value,
                    "framework": m.framework,
                    "version": m.version,
                    "status": m.status,
                    "provider": m.provider,
                    "predict_endpoint": f"/api/models/{m.name}/predict",
                    "input_schema": m.input_schema,
                    "output_schema": m.output_schema
                }
                for m in models
            ],
            "count": len(models)
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_name}")
async def get_model_details(model_name: str):
    """Get model details - REST API for watsonx Orchestrate."""
    try:
        models = await registry.list_all_models()
        model = next((m for m in models if m.name == model_name), None)
        
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
        
        return {
            "name": model.name,
            "id": model.id,
            "description": model.description,
            "type": model.model_type.value,
            "framework": model.framework,
            "version": model.version,
            "status": model.status,
            "provider": model.provider,
            "predict_endpoint": f"/api/models/{model.name}/predict",
            "input_schema": model.input_schema,
            "output_schema": model.output_schema
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_name}/predict")
async def predict(model_name: str, input_data: Dict[str, Any]):
    """Make prediction - REST API for watsonx Orchestrate."""
    try:
        logger.info(f"REST API prediction: {model_name}")
        
        models = await registry.list_all_models()
        model = next((m for m in models if m.name == model_name), None)
        
        if not model:
            raise HTTPException(status_code=404, detail=f"Model not found: {model_name}")
        
        provider = registry.providers.get(model.provider)
        if not provider:
            raise HTTPException(status_code=500, detail=f"Provider not found: {model.provider}")
        
        result = await provider.predict(model.id, input_data)
        
        return {
            "model": model_name,
            "prediction": result,
            "status": "success"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ============================================================================
# WEB UI ENDPOINT
# ============================================================================

@app.get("/ui", response_class=HTMLResponse)
async def web_ui():
    """Simple web UI showing integration options."""
    models = await registry.list_all_models()
    models_count = len(models)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ML Registry - Integration Guide</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #1976d2; }}
            .integration {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }}
            .endpoint {{ background: #263238; color: #aed581; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }}
            .status {{ color: #4caf50; font-weight: bold; }}
            code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>🤖 ML Registry Unified Server</h1>
        <p class="status">✅ Server Running | {models_count} Models Discovered</p>
        
        <div class="integration">
            <h2>Option 1: Context Forge (MCP Protocol)</h2>
            <p>Use this for MCP-based integration with Context Forge middleware.</p>
            <h3>Configuration:</h3>
            <div class="endpoint">
{{
  "name": "ml-registry",
  "url": "https://your-server-url",
  "transport": "http",
  "endpoints": {{
    "mcp": "/mcp",
    "sse": "/sse"
  }}
}}</div>
            <h3>Test:</h3>
            <div class="endpoint">curl https://your-server-url/mcp/tools</div>
        </div>
        
        <div class="integration">
            <h2>Option 2: Direct watsonx Orchestrate (REST API)</h2>
            <p>Use this for direct REST API integration without middleware.</p>
            <h3>Import OpenAPI:</h3>
            <div class="endpoint">https://your-server-url/api/openapi.json</div>
            <h3>List Models:</h3>
            <div class="endpoint">GET https://your-server-url/api/models</div>
            <h3>Make Prediction:</h3>
            <div class="endpoint">POST https://your-server-url/api/models/{{model_name}}/predict</div>
        </div>
        
        <div class="integration">
            <h2>📚 Documentation</h2>
            <ul>
                <li><a href="/api/docs">Interactive API Documentation</a></li>
                <li><a href="/api/openapi.json">OpenAPI Schema</a></li>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/api/models">Models List</a></li>
            </ul>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


# ============================================================================
# MCP REQUEST HANDLER
# ============================================================================

async def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC requests."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "ml-registry-unified",
                        "version": settings.server_version
                    },
                    "capabilities": {"tools": {}, "resources": {}}
                },
                "id": request_id
            }
        
        elif method == "tools/list":
            models = await registry.list_all_models()
            tools = generate_mcp_tools(models)
            return {
                "jsonrpc": "2.0",
                "result": {"tools": tools},
                "id": request_id
            }
        
        elif method == "tools/call":
            return await handle_mcp_tool_call(request_id, params)
        
        elif method == "resources/list":
            models = await registry.list_all_models()
            resources = [
                {
                    "uri": f"model://{m.provider}/{m.name}",
                    "name": m.name,
                    "description": m.description or f"{m.model_type.value} model",
                    "mimeType": "application/json"
                }
                for m in models
            ]
            return {
                "jsonrpc": "2.0",
                "result": {"resources": resources},
                "id": request_id
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": request_id
            }
    
    except Exception as e:
        logger.error(f"MCP handler error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            "id": request_id
        }


async def handle_mcp_tool_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tool call."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name or not isinstance(tool_name, str):
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid tool name"},
            "id": request_id
        }
    
    # Extract model name from tool name
    # Tool names are in format: provider_model_name (e.g., "watsonx_demand_forecasting_ml")
    models = await registry.list_all_models()
    
    # Try to find model by matching tool name pattern
    model = None
    for m in models:
        # Tool name format: {provider}_{model_name_with_underscores}
        expected_tool_name = f"{m.provider}_{m.name.replace('-', '_')}"
        if tool_name == expected_tool_name:
            model = m
            break
    
    if not model:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": f"Model not found for tool: {tool_name}"},
            "id": request_id
        }
    
    provider = registry.providers.get(model.provider)
    if not provider:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Provider not found: {model.provider}"},
            "id": request_id
        }
    
    try:
        logger.info(f"Calling predict for model {model.id}")
        logger.info(f"Arguments received: {json.dumps(arguments, indent=2)}")
        
        result = await provider.predict(model.id, arguments)
        
        if result is None:
            logger.error(f"Prediction returned None for model {model.id}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Prediction returned None - check server logs"},
                "id": request_id
            }
        
        if not isinstance(result, dict):
            logger.error(f"Prediction returned non-dict type: {type(result)}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Invalid result type: {type(result)}"},
                "id": request_id
            }
        
        logger.info(f"Prediction successful for model {model.id}")
        logger.info(f"Result: {json.dumps(result, indent=2)}")
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            },
            "id": request_id
        }
    except Exception as e:
        logger.error(f"Prediction error for model {model.id}: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": f"Prediction failed: {str(e)}"},
            "id": request_id
        }


def run_unified_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the unified server with all protocols."""
    logger.info(f"Starting Unified Server on {host}:{port}")
    logger.info("Protocols: MCP (Context Forge) + REST API (watsonx Orchestrate) + Web UI")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_unified_server()

# Made with Bob

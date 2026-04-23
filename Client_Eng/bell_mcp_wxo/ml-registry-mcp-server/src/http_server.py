"""HTTP/SSE MCP Server for watsonx Orchestrate and Context Forge integration.

This server provides HTTP endpoints with Server-Sent Events (SSE) transport,
making it compatible with Context Forge and deployable to cloud environments.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import settings
from .registry import ModelRegistry
from .mcp.tools import generate_mcp_tools

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Registry MCP Server",
    description="MCP Server for ML Model Registry with HTTP/SSE transport",
    version=settings.server_version
)

# Enable CORS for watsonx Orchestrate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = ModelRegistry()


@app.on_event("startup")
async def startup():
    """Initialize registry on startup."""
    logger.info("Starting MCP HTTP Server...")
    await registry.initialize()
    logger.info("MCP HTTP Server started")


@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "ml-registry-mcp-server",
        "version": settings.server_version,
        "protocol": "mcp",
        "transport": "http/sse",
        "description": "ML Model Registry MCP Server for watsonx Orchestrate",
        "endpoints": {
            "mcp": "/mcp",
            "sse": "/sse",
            "health": "/health",
            "models": "/api/models"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        provider_health = await registry.health_check()
        return {
            "status": "healthy",
            "providers": provider_health,
            "models_count": len(await registry.list_all_models())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Main MCP endpoint for JSON-RPC requests."""
    body: Optional[Dict[str, Any]] = None
    try:
        body = await request.json()
        if body:
            logger.info(f"Received MCP request: {body.get('method')}")
            response = await handle_mcp_request(body)
            return JSONResponse(content=response)
        else:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    },
                    "id": None
                },
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": body.get("id") if body else None
            },
            status_code=500
        )


@app.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for streaming MCP responses."""
    async def event_generator():
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'server': 'ml-registry-mcp-server'})}\n\n"
            
            # Keep connection alive
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


@app.get("/api/models")
async def list_models():
    """List all discovered models."""
    try:
        models = await registry.list_all_models()
        return {
            "models": [
                {
                    "id": m.id,
                    "name": m.name,
                    "provider": m.provider,
                    "model_type": m.model_type.value,
                    "framework": m.framework,
                    "version": m.version,
                    "description": m.description,
                    "status": m.status,
                    "endpoint_url": m.endpoint_url,
                    "input_schema": m.input_schema,
                    "output_schema": m.output_schema
                }
                for m in models
            ],
            "count": len(models)
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/tools")
async def list_tools():
    """List all MCP tools (for Context Forge discovery)."""
    try:
        models = await registry.list_all_models()
        tools = generate_mcp_tools(models)
        return {
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        logger.error(f"Error listing tools: {e}", exc_info=True)
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


async def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "initialize":
            return await handle_initialize(request_id, params)
        
        elif method == "tools/list":
            return await handle_tools_list(request_id)
        
        elif method == "tools/call":
            return await handle_tools_call(request_id, params)
        
        elif method == "resources/list":
            return await handle_resources_list(request_id)
        
        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "result": {"prompts": []},
                "id": request_id
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
    
    except Exception as e:
        logger.error(f"Error handling method {method}: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": request_id
        }


async def handle_initialize(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle initialize request."""
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "ml-registry-mcp-server",
                "version": settings.server_version
            },
            "capabilities": {
                "tools": {},
                "resources": {}
            }
        },
        "id": request_id
    }


async def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """Handle tools/list request."""
    models = await registry.list_all_models()
    tools = generate_mcp_tools(models)
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools
        },
        "id": request_id
    }


async def handle_tools_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
    
    # Validate tool name
    if not tool_name or not isinstance(tool_name, str):
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": "Invalid parameters: tool name is required"
            },
            "id": request_id
        }
    
    # Extract model name from tool name (format: predict_<model_name>)
    if not tool_name.startswith("predict_"):
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": f"Invalid tool name: {tool_name}"
            },
            "id": request_id
        }
    
    model_name = tool_name.replace("predict_", "").replace("_", "-")
    
    # Find the model
    models = await registry.list_all_models()
    model = next((m for m in models if m.name == model_name), None)
    
    if not model:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32602,
                "message": f"Model not found: {model_name}"
            },
            "id": request_id
        }
    
    # Get the provider and make prediction
    provider = registry.providers.get(model.provider)
    if not provider:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Provider not found: {model.provider}"
            },
            "id": request_id
        }
    
    try:
        result = await provider.predict(model.id, arguments)
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            },
            "id": request_id
        }
    
    except Exception as e:
        logger.error(f"Error making prediction: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Prediction failed: {str(e)}"
            },
            "id": request_id
        }


async def handle_resources_list(request_id: Any) -> Dict[str, Any]:
    """Handle resources/list request."""
    models = await registry.list_all_models()
    
    resources = [
        {
            "uri": f"model://{model.provider}/{model.name}",
            "name": model.name,
            "description": model.description or f"{model.model_type.value} model",
            "mimeType": "application/json"
        }
        for model in models
    ]
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "resources": resources
        },
        "id": request_id
    }


def run_http_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the HTTP MCP server."""
    logger.info(f"Starting MCP HTTP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_http_server()

# Made with Bob

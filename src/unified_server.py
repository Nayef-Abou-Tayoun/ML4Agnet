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
from .schema_manager import get_schema_manager, ModelSchema

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
async def sse_get_endpoint(request: Request):
    """Server-Sent Events GET endpoint for MCP streaming connection."""
    async def event_generator():
        try:
            # Send initial connection message
            logger.info("SSE connection established")
            yield f"data: {json.dumps({'type': 'endpoint', 'endpoint': '/sse'})}\n\n"
            
            # Keep connection alive with periodic pings
            while True:
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE connection closed")
        except Exception as e:
            logger.error(f"SSE error: {e}", exc_info=True)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )


@app.post("/sse")
async def sse_post_endpoint(request: Request):
    """Server-Sent Events POST endpoint for MCP JSON-RPC requests.
    
    This handles MCP protocol requests sent to the SSE endpoint.
    """
    body: Optional[Dict[str, Any]] = None
    try:
        body = await request.json()
        if body:
            logger.info(f"SSE MCP request: {body.get('method')}")
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
        logger.error(f"SSE MCP error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": body.get("id") if body else None
            },
            status_code=500
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
# SCHEMA MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/schemas")
async def list_schemas():
    """List all custom model schemas."""
    try:
        schema_mgr = get_schema_manager()
        schemas = schema_mgr.list_schemas()
        return {
            "schemas": [s.model_dump() for s in schemas],
            "count": len(schemas)
        }
    except Exception as e:
        logger.error(f"Error listing schemas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schemas/{model_id}")
async def get_schema(model_id: str):
    """Get schema for a specific model."""
    try:
        schema_mgr = get_schema_manager()
        schema = schema_mgr.get_schema(model_id)
        if schema:
            return schema.model_dump()
        raise HTTPException(status_code=404, detail="Schema not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/schemas")
async def create_or_update_schema(request: Request):
    """Create or update a model schema."""
    try:
        data = await request.json()
        schema_mgr = get_schema_manager()
        schema = ModelSchema(**data)
        success = schema_mgr.set_schema(schema)
        if success:
            return {"success": True, "schema": schema.model_dump()}
        raise HTTPException(status_code=500, detail="Failed to save schema")
    except Exception as e:
        logger.error(f"Error saving schema: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/schemas/{model_id}")
async def delete_schema(model_id: str):
    """Delete a model schema."""
    try:
        schema_mgr = get_schema_manager()
        success = schema_mgr.delete_schema(model_id)
        if success:
            return {"success": True, "message": "Schema deleted"}
        raise HTTPException(status_code=404, detail="Schema not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schema: {e}", exc_info=True)
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
# WEB UI ENDPOINTS
# ============================================================================

@app.get("/ui", response_class=HTMLResponse)
async def web_ui(request: Request):
    """Full dashboard UI with model discovery and management."""
    try:
        models = await registry.list_all_models()
        mcp_tools = generate_mcp_tools(models)
        provider_stats = registry.get_provider_stats()
        
        total_models = len(models)
        total_providers = len(registry.providers)
        model_types = len(set(m.model_type.value for m in models)) if models else 0
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ML Model Registry</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: #f5f5f5;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                }}
                header {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 30px;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 10px;
                    font-size: 28px;
                }}
                .subtitle {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .nav-links {{
                    display: flex;
                    gap: 10px;
                }}
                .nav-links a {{
                    color: #1976d2;
                    text-decoration: none;
                    font-weight: 500;
                }}
                .nav-links a:hover {{
                    text-decoration: underline;
                }}
                .tabs {{
                    background: white;
                    padding: 0;
                    border-radius: 10px 10px 0 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 0;
                }}
                .tab-list {{
                    display: flex;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 0 30px;
                }}
                .tab {{
                    padding: 15px 20px;
                    cursor: pointer;
                    border-bottom: 3px solid transparent;
                    color: #666;
                    font-weight: 500;
                    transition: all 0.2s;
                }}
                .tab:hover {{
                    color: #333;
                }}
                .tab.active {{
                    color: #1976d2;
                    border-bottom-color: #1976d2;
                }}
                .tab-content {{
                    background: white;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    min-height: 400px;
                }}
                .tab-pane {{
                    display: none;
                }}
                .tab-pane.active {{
                    display: block;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .stat-number {{
                    font-size: 48px;
                    font-weight: bold;
                    color: #1976d2;
                    margin-bottom: 10px;
                }}
                .stat-label {{
                    color: #666;
                    font-size: 16px;
                }}
                .empty-state {{
                    text-align: center;
                    padding: 60px 20px;
                }}
                .empty-state h2 {{
                    color: #333;
                    margin-bottom: 15px;
                    font-size: 24px;
                }}
                .empty-state p {{
                    color: #666;
                    margin-bottom: 25px;
                }}
                .btn {{
                    background: #1976d2;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: 500;
                    text-decoration: none;
                    display: inline-block;
                    transition: background 0.2s;
                }}
                .btn:hover {{
                    background: #1565c0;
                }}
                .btn-secondary {{
                    background: #4caf50;
                }}
                .btn-secondary:hover {{
                    background: #45a049;
                }}
                .model-card {{
                    background: #f9f9f9;
                    border-radius: 8px;
                    padding: 25px;
                    border: 1px solid #e0e0e0;
                }}
                .model-name {{
                    font-size: 22px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 10px;
                }}
                .model-type {{
                    display: inline-block;
                    padding: 4px 12px;
                    background: #e3f2fd;
                    color: #1976d2;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                .settings-form {{
                    max-width: 600px;
                }}
                .form-group {{
                    margin-bottom: 20px;
                }}
                .form-group label {{
                    display: block;
                    margin-bottom: 8px;
                    color: #333;
                    font-weight: 500;
                }}
                .form-group input {{
                    width: 100%;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 6px;
                    font-size: 14px;
                }}
                .form-group input:focus {{
                    outline: none;
                    border-color: #1976d2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🤖 ML Model Registry</h1>
                    <div class="subtitle">Discover and manage your deployed machine learning models</div>
                    <div class="nav-links">
                        <a href="#dashboard">Dashboard</a>
                        <a href="/api/models">API</a>
                        <a href="#settings">Settings</a>
                    </div>
                </header>
                
                <div class="tabs">
                    <div class="tab-list">
                        <div class="tab active" onclick="switchTab(event, 'dashboard')">Dashboard</div>
                        <div class="tab" onclick="switchTab(event, 'models')">Discovered Models</div>
                        <div class="tab" onclick="switchTab(event, 'settings')">Settings</div>
                    </div>
                </div>
                
                <div class="tab-content">
                    <!-- Dashboard Tab -->
                    <div id="dashboard" class="tab-pane active">
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-number">{total_models}</div>
                                <div class="stat-label">Total Models</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">{total_providers}</div>
                                <div class="stat-label">Providers</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">{model_types}</div>
                                <div class="stat-label">Model Types</div>
                            </div>
                        </div>
                        
                        {_render_dashboard_content(models)}
                    </div>
                    
                    <!-- Discovered Models Tab -->
                    <div id="models" class="tab-pane">
                        <h2 style="margin-bottom: 30px;">Discovered Models</h2>
                        {_render_models_list(models)}
                    </div>
                    
                    <!-- Settings Tab -->
                    <div id="settings" class="tab-pane">
                        <h2 style="margin-bottom: 10px;">⚙️ Settings</h2>
                        <p style="color: #666; margin-bottom: 30px;">Configure your watsonx.ai credentials</p>
                        
                        <div class="settings-form">
                            <div class="form-group">
                                <label>watsonx.ai API Key</label>
                                <input type="password" placeholder="Enter your IBM Cloud API key" value="{'***' if settings.watsonx_api_key else ''}">
                            </div>
                            <div class="form-group">
                                <label>Space ID</label>
                                <input type="text" placeholder="Enter your watsonx.ai space ID" value="{settings.watsonx_space_id or ''}">
                            </div>
                            <div class="form-group">
                                <label>watsonx.ai URL</label>
                                <input type="text" placeholder="https://us-south.ml.cloud.ibm.com" value="{settings.watsonx_url}">
                            </div>
                            <button class="btn" onclick="alert('Settings are configured via .env file. Please edit .env and restart the server.')">Save Settings</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                function switchTab(event, tabName) {{
                    // Hide all tabs
                    document.querySelectorAll('.tab-pane').forEach(pane => {{
                        pane.classList.remove('active');
                    }});
                    document.querySelectorAll('.tab').forEach(tab => {{
                        tab.classList.remove('active');
                    }});
                    
                    // Show selected tab
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    
    except Exception as e:
        logger.error(f"Error rendering UI: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Error</h1><p>Failed to load models: {str(e)}</p>",
            status_code=500
        )


def _render_dashboard_content(models):
    """Render dashboard content."""
    if not models:
        return """
        <div class="empty-state">
            <h2>No Models Found</h2>
            <p>Deploy models to watsonx.ai to see them here</p>
        </div>
        """
    
    cards = []
    for model in models[:6]:
        cards.append(f"""
        <div class="model-card">
            <div class="model-name">{model.name}</div>
            <span class="model-type">{model.model_type.value}</span>
            <p style="color: #666; margin-top: 10px; font-size: 14px;">{model.description or 'No description'}</p>
            <button class="btn btn-secondary" style="margin-top: 15px;" onclick="switchTab(event, 'models')">View Details</button>
        </div>
        """)
    
    return f'<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px;">{"".join(cards)}</div>'


def _render_models_list(models):
    """Render simple models list."""
    if not models:
        return """
        <div class="empty-state">
            <h2>No Models Discovered</h2>
            <p>Configure your watsonx.ai credentials to discover deployed models</p>
            <button class="btn" onclick="switchTab(event, 'settings')">Go to Settings</button>
        </div>
        """
    
    cards = []
    for model in models:
        cards.append(f"""
        <div class="model-card" style="margin-bottom: 20px;">
            <div class="model-name">{model.name}</div>
            <span class="model-type">{model.model_type.value}</span>
            <p style="color: #666; margin-top: 10px; font-size: 14px;">{model.description or 'No description'}</p>
            <div style="margin-top: 15px; font-size: 13px; color: #666;">
                <div><strong>Provider:</strong> {model.provider}</div>
                <div><strong>Framework:</strong> {model.framework}</div>
                <div><strong>Status:</strong> {model.status}</div>
            </div>
        </div>
        """)
    
    return "".join(cards)

@app.get("/schemas", response_class=HTMLResponse)
async def schema_editor_page(request: Request):
    """Schema editor UI page."""
    from .schema_ui import get_schema_editor_html
    try:
        html = await get_schema_editor_html(request, registry)
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Error rendering schema editor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MCP REQUEST HANDLER
# ============================================================================

async def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC requests."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    logger.info(f"MCP request: {method}")
    if method == "tools/call":
        logger.info(f"Tool call params: {json.dumps(params, indent=2)}")
    
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

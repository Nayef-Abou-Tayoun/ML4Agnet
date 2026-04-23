"""Web UI for ML Registry with detailed schema and MCP integration info."""

import logging
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from .config import settings
from .registry import ModelRegistry
from .mcp.tools import generate_mcp_tools

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ML Registry UI",
    description="Web interface for ML Model Registry",
    version=settings.server_version
)

registry = ModelRegistry()


@app.on_event("startup")
async def startup():
    """Initialize registry on startup."""
    logger.info("Starting ML Registry UI...")
    await registry.initialize()
    logger.info("ML Registry UI started")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Dashboard page with statistics."""
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
                .model-list {{
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }}
                .model-card {{
                    background: #f9f9f9;
                    border-radius: 8px;
                    padding: 25px;
                    border: 1px solid #e0e0e0;
                }}
                .model-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: start;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #e0e0e0;
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
                .model-details {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .detail-item {{
                    font-size: 14px;
                }}
                .detail-label {{
                    color: #666;
                    font-weight: 500;
                    margin-bottom: 5px;
                }}
                .detail-value {{
                    color: #333;
                }}
                .schema-section {{
                    margin-top: 20px;
                    padding: 20px;
                    background: white;
                    border-radius: 6px;
                    border: 1px solid #e0e0e0;
                }}
                .schema-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #333;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .schema-content {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 13px;
                    overflow-x: auto;
                    max-height: 300px;
                    overflow-y: auto;
                }}
                .mcp-integration {{
                    margin-top: 20px;
                    padding: 20px;
                    background: #e8f5e9;
                    border-radius: 6px;
                    border: 1px solid #4caf50;
                }}
                .mcp-title {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #2e7d32;
                    margin-bottom: 15px;
                }}
                .mcp-info {{
                    font-size: 14px;
                    color: #333;
                    line-height: 1.6;
                }}
                .code-block {{
                    background: #263238;
                    color: #aed581;
                    padding: 15px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    font-size: 13px;
                    overflow-x: auto;
                    margin: 10px 0;
                }}
                .copy-btn {{
                    background: #666;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    margin-top: 10px;
                }}
                .copy-btn:hover {{
                    background: #555;
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
                        <a href="/">Dashboard</a>
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
                        <h2 style="margin-bottom: 10px;">🔍 Discovered Models</h2>
                        <p style="color: #666; margin-bottom: 30px;">Detailed information, schemas, and MCP integration instructions</p>
                        
                        {_render_models_with_schema(models, mcp_tools)}
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
                
                function copyToClipboard(text, btnId) {{
                    navigator.clipboard.writeText(text).then(() => {{
                        const btn = document.getElementById(btnId);
                        const originalText = btn.textContent;
                        btn.textContent = '✓ Copied!';
                        setTimeout(() => {{
                            btn.textContent = originalText;
                        }}, 2000);
                    }});
                }}
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    
    except Exception as e:
        logger.error(f"Error rendering home page: {e}", exc_info=True)
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


def _render_models_with_schema(models, mcp_tools):
    """Render discovered models with detailed schema information."""
    if not models:
        return """
        <div class="empty-state">
            <h2>No Models Discovered</h2>
            <p>Configure your watsonx.ai credentials to discover deployed models</p>
            <button class="btn" onclick="switchTab(event, 'settings')">Go to Settings</button>
        </div>
        """
    
    cards = []
    for i, (model, tool) in enumerate(zip(models, mcp_tools)):
        tool_name = tool['name']
        input_schema = json.dumps(tool['inputSchema'], indent=2)
        output_schema = json.dumps(model.output_schema, indent=2)
        
        # MCP integration code
        mcp_config = json.dumps({
            "mcpServers": {
                "ml-models": {
                    "command": "python",
                    "args": ["-m", "src.server"],
                    "cwd": "/path/to/ml-registry-mcp-server"
                }
            }
        }, indent=2)
        
        cards.append(f"""
        <div class="model-card">
            <div class="model-header">
                <div>
                    <div class="model-name">{model.name}</div>
                    <span class="model-type">{model.model_type.value}</span>
                </div>
            </div>
            
            <div class="model-details">
                <div class="detail-item">
                    <div class="detail-label">Provider</div>
                    <div class="detail-value">{model.provider}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Framework</div>
                    <div class="detail-value">{model.framework}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">{model.status}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Deployment ID</div>
                    <div class="detail-value" style="font-size: 11px;">{model.id}</div>
                </div>
            </div>
            
            <div class="schema-section">
                <div class="schema-title">📥 Input Schema</div>
                <div class="schema-content">{input_schema}</div>
                <button class="copy-btn" id="copy-input-{i}" onclick="copyToClipboard(`{input_schema.replace('`', '\\`')}`, 'copy-input-{i}')">Copy Schema</button>
            </div>
            
            <div class="schema-section">
                <div class="schema-title">📤 Output Schema</div>
                <div class="schema-content">{output_schema}</div>
                <button class="copy-btn" id="copy-output-{i}" onclick="copyToClipboard(`{output_schema.replace('`', '\\`')}`, 'copy-output-{i}')">Copy Schema</button>
            </div>
            
            <div class="mcp-integration">
                <div class="mcp-title">🔌 MCP Integration</div>
                <div class="mcp-info">
                    <strong>Tool Name:</strong> <code>{tool_name}</code><br><br>
                    <strong>For Claude Desktop:</strong> Add this to your config:
                    <div class="code-block">{mcp_config}</div>
                    <button class="copy-btn" id="copy-mcp-{i}" onclick="copyToClipboard(`{mcp_config.replace('`', '\\`')}`, 'copy-mcp-{i}')">Copy Config</button>
                    <br><br>
                    <strong>For watsonx Orchestrate:</strong><br>
                    • Tool name: <code>{tool_name}</code><br>
                    • Endpoint: MCP server at <code>python -m src.server</code><br>
                    • Schema: See input/output schemas above
                </div>
            </div>
        </div>
        """)
    
    return f'<div class="model-list">{"".join(cards)}</div>'


@app.get("/api/models")
async def list_models():
    """API endpoint to list all models."""
    try:
        models = await registry.list_all_models()
        return JSONResponse(content={
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
        })
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        provider_health = await registry.health_check()
        return JSONResponse(content={
            "status": "healthy",
            "providers": provider_health
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


def run_ui(host: str = "0.0.0.0", port: int = 8081):
    """Run the web UI server."""
    logger.info(f"Starting ML Registry UI on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_ui()

# Made with Bob

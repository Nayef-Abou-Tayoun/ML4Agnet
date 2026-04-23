# ML Registry MCP Server - stdio Usage Guide

## Overview
The ML Registry MCP Server now supports both **stdio** and **SSE** transports, giving you flexibility in how you connect to watsonx Orchestrate.

## Installation

### Option 1: Using uvx (Recommended)
```bash
# Install from GitHub
uvx --from git+https://github.com/Nayef-Abou-Tayoun/ML4Agnet ml-registry-mcp-server --transport stdio --wxo

# Or install locally
pip install -e .
```

### Option 2: Direct Python
```bash
# Clone and install
git clone https://github.com/Nayef-Abou-Tayoun/ML4Agnet.git
cd ML4Agnet
pip install -e .
```

## Usage

### stdio Transport (for watsonx Orchestrate)
```bash
# Basic stdio mode
ml-registry-mcp-server --transport stdio

# With WxO compatibility flag
ml-registry-mcp-server --transport stdio --wxo

# Using Python module
python -m src --transport stdio --wxo

# Using uvx
uvx ml-registry-mcp-server --transport stdio --wxo
```

### SSE Transport (HTTP endpoint)
```bash
# Start SSE server on default port 8080
ml-registry-mcp-server --transport sse

# Custom host and port
ml-registry-mcp-server --transport sse --host 0.0.0.0 --port 8000

# Using Python module
python -m src --transport sse --port 8000
```

## Environment Variables
Create a `.env` file with your watsonx.ai credentials:

```env
WATSONX_API_KEY=your_api_key_here
WATSONX_SPACE_ID=your_space_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

## watsonx Orchestrate Configuration

### Using stdio Transport
In watsonx Orchestrate, configure the MCP server:

```json
{
  "mcpServers": {
    "ml-registry": {
      "command": "uvx",
      "args": [
        "ml-registry-mcp-server",
        "--transport",
        "stdio",
        "--wxo"
      ],
      "env": {
        "WATSONX_API_KEY": "your_api_key",
        "WATSONX_SPACE_ID": "your_space_id",
        "WATSONX_URL": "https://us-south.ml.cloud.ibm.com"
      }
    }
  }
}
```

### Using SSE Transport
In watsonx Orchestrate, configure the MCP server:

```json
{
  "mcpServers": {
    "ml-registry": {
      "url": "https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/mcp",
      "transport": "sse"
    }
  }
}
```

## Command-Line Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--transport` | `stdio`, `sse` | `stdio` | Transport protocol |
| `--wxo` | flag | false | Enable watsonx Orchestrate compatibility |
| `--host` | string | `0.0.0.0` | Host for SSE transport |
| `--port` | integer | `8080` | Port for SSE transport |

## Available Models

The server automatically discovers models from your watsonx.ai space. Each model is exposed as an MCP tool:

- **Tool Name**: `predict_{model_name}` (underscores replace hyphens)
- **Example**: `predict_demand_forecasting_ml`

## Testing

### Test stdio locally
```bash
# Start the server
ml-registry-mcp-server --transport stdio --wxo

# In another terminal, send a test request
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | ml-registry-mcp-server --transport stdio
```

### Test SSE endpoint
```bash
# Start the server
ml-registry-mcp-server --transport sse --port 8080

# Test health endpoint
curl http://localhost:8080/health

# Test MCP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Comparison with IBM watsonx.data MCP Server

| Feature | IBM watsonx.data | ML Registry |
|---------|------------------|-------------|
| Purpose | Data queries & catalogs | ML model predictions |
| Command | `uvx ibm-watsonx-data-intelligence-mcp-server` | `uvx ml-registry-mcp-server` |
| Transport | stdio | stdio + SSE |
| Platform | watsonx.data | watsonx.ai |
| Tools | Data operations | Model predictions |

## Troubleshooting

### stdio not working
- Ensure environment variables are set
- Check logs in stderr (stdio uses stdout for protocol)
- Verify watsonx.ai credentials

### SSE not connecting
- Check firewall rules
- Verify the server is running: `curl http://localhost:8080/health`
- Check server logs for errors

### Models not discovered
- Verify WATSONX_SPACE_ID is correct
- Check API key has access to the space
- Ensure models are deployed in watsonx.ai

## Support

- GitHub: https://github.com/Nayef-Abou-Tayoun/ML4Agnet
- Issues: https://github.com/Nayef-Abou-Tayoun/ML4Agnet/issues

## License

MIT License - see LICENSE file for details
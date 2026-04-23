# ML Registry MCP Server

A Model Context Protocol (MCP) server that exposes watsonx.ai ML models for consumption by AI agents and orchestration platforms like watsonx Orchestrate.

## Features

- ✅ **watsonx.ai Integration**: Automatically discovers and exposes deployed ML models
- ✅ **MCP Protocol**: Standard protocol for AI agent tool integration
- ✅ **SSE Transport**: Server-Sent Events for remote access
- ✅ **Format Handling**: Automatically converts input formats for watsonx.ai
- ✅ **Cloud Deployed**: Ready-to-use deployment on IBM Cloud Code Engine

## Quick Start for watsonx Orchestrate

### Configuration

Add this to your watsonx Orchestrate MCP servers configuration:

```json
{
  "mcpServers": {
    "ml-registry": {
      "command": "uvx",
      "args": [
        "mcp-proxy",
        "https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/mcp"
      ]
    }
  }
}
```

### Available Tools

- **`predict_demand_forecasting_ml`**: Demand forecasting predictions using watsonx.ai

### Example Usage

```json
{
  "date": "2024-01-01",
  "day_of_week": 1,
  "holiday": false,
  "price": 19.99,
  "product_id": "A123",
  "promotion": 0,
  "stock": 120,
  "store_id": "S001"
}
```

## Architecture

```
WxO (stdio) → uvx mcp-proxy → SSE → ML Registry → watsonx.ai
```

- **mcp-proxy**: Bridges stdio (WxO) to SSE (ML Registry)
- **ML Registry**: Discovers models and handles predictions
- **watsonx.ai**: Provides ML model inference

## Deployment

**Deployed URL**: https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud

**Health Check**:
```bash
curl https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/health
```

## Repository Structure

```
ml-registry-mcp-server/
├── src/
│   ├── __main__.py          # CLI entry point
│   ├── server.py            # MCP stdio server
│   ├── unified_server.py    # SSE server
│   ├── registry.py          # Model registry
│   ├── config.py            # Configuration
│   ├── mcp/
│   │   └── tools.py         # MCP tool definitions
│   └── providers/
│       ├── base.py          # Provider interface
│       └── watsonx.py       # watsonx.ai provider
├── Dockerfile               # Container image
├── pyproject.toml          # Package configuration
└── requirements.txt        # Dependencies
```

## Environment Variables

```env
WATSONX_API_KEY=your_api_key
WATSONX_SPACE_ID=your_space_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

## License

MIT License - see LICENSE file for details

## Support

- **GitHub**: https://github.com/Nayef-Abou-Tayoun/ML4Agnet
- **Issues**: https://github.com/Nayef-Abou-Tayoun/ML4Agnet/issues
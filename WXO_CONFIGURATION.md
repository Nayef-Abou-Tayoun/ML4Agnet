# watsonx Orchestrate Configuration for ML Registry MCP Server

## ✅ Solution: Use mcp-proxy to Bridge SSE to stdio

### Configuration for watsonx Orchestrate

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

### Alternative: Direct SSE (if supported by your WxO version)

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

### Why SSE is Better for WxO
1. ✅ No Git required
2. ✅ Already deployed and operational
3. ✅ Handles WxO input format correctly
4. ✅ Accessible from anywhere
5. ✅ No installation needed

## Available Model
- **Tool Name**: `predict_demand_forecasting_ml`
- **Model**: demand-forecasting-ml
- **Provider**: watsonx.ai
- **Deployment**: 019db7a0-c668-70a0-8a32-6dcc5a1041df

## Testing the Connection

### 1. Verify Server Health
```bash
curl https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/health
```

Expected response:
```json
{
  "status": "healthy",
  "providers": {
    "watsonx": true
  },
  "models_count": 1,
  "protocols": ["mcp", "rest", "ui"]
}
```

### 2. List Available Tools
```bash
curl -X POST https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### 3. Call Prediction Tool from WxO
Once configured in WxO, use the tool:
- **Tool**: `predict_demand_forecasting_ml`
- **Input**: Your demand forecasting data

## Alternative: stdio Transport (Local Only)

If you want to use stdio transport locally (not in WxO):

```bash
# Clone the repository locally
git clone https://github.com/Nayef-Abou-Tayoun/ML4Agnet.git
cd ML4Agnet

# Install dependencies
pip install -e .

# Run with stdio
ml-registry-mcp-server --transport stdio --wxo
```

Or use Python directly:
```bash
python -m src --transport stdio --wxo
```

## Summary

| Transport | Use Case | WxO Compatible | Requires Git |
|-----------|----------|----------------|--------------|
| **SSE** | Remote/Cloud | ✅ Yes | ❌ No |
| **stdio** | Local/Development | ❌ No (Git issue) | ✅ Yes |

**Recommendation**: Use SSE transport for watsonx Orchestrate integration.

## Support
- Deployed URL: https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud
- GitHub: https://github.com/Nayef-Abou-Tayoun/ML4Agnet
- Health Check: https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/health
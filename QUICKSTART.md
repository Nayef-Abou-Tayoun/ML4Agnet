# ML Registry MCP Server - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.11+
- watsonx.ai account with API key
- Deployed ML models in watsonx.ai

### Step 1: Install Dependencies

```bash
cd ml-registry-mcp-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure

```bash
cp .env.example .env
```

Edit `.env` and add your watsonx.ai credentials:

```bash
WATSONX_API_KEY=your-api-key-here
WATSONX_PROJECT_ID=your-project-id-here
```

### Step 3: Run

#### Option A: MCP Server (for Claude Desktop, Cline, etc.)

```bash
python -m src.server
```

The server will:
1. Connect to watsonx.ai
2. Discover all your deployed models
3. Expose them as MCP tools
4. Wait for requests on stdio

#### Option B: Web UI

```bash
python -m src.ui
```

Then open: http://localhost:8081

### Step 4: Use with Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ml-models": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/ml-registry-mcp-server",
      "env": {
        "WATSONX_API_KEY": "your-key",
        "WATSONX_PROJECT_ID": "your-project"
      }
    }
  }
}
```

Restart Claude Desktop and your models will appear as available tools!

## 📝 Example Usage

### In Claude Desktop

```
You: "List available ML models"

Claude: "I can see these models:
- watsonx_fraud_detection_model (classification)
- watsonx_churn_predictor (classification)
- watsonx_demand_forecaster (regression)"

You: "Use the fraud detection model to check if this transaction is fraudulent:
     amount=$500, merchant=electronics, time=2am"

Claude: [Calls the model]
"Based on your fraud detection model, this transaction has an 85% 
probability of being fraudulent due to unusual time and high amount."
```

### Via Python

```python
import asyncio
from src.registry import ModelRegistry

async def main():
    registry = ModelRegistry()
    await registry.initialize()
    
    # List models
    models = await registry.list_all_models()
    for model in models:
        print(f"{model.name} ({model.model_type.value})")
    
    # Make prediction
    result = await registry.predict(
        model_id="your-model-id",
        input_data={
            "fields": ["amount", "merchant", "time"],
            "values": [[500, "electronics", 2]]
        }
    )
    print(result)

asyncio.run(main())
```

## 🎯 What You Get

✅ **Automatic Discovery**: Finds all your watsonx.ai models  
✅ **MCP Integration**: Works with Claude, Cline, any MCP client  
✅ **Web UI**: Visual interface to browse models  
✅ **Type Safety**: Structured input/output schemas  
✅ **Multi-Cloud Ready**: Easy to add Azure ML, SageMaker, Vertex AI

## 🔧 Troubleshooting

### "No models found"
- Check your watsonx.ai credentials
- Ensure you have deployed models in your project/space
- Check logs for connection errors

### "Import errors"
- Make sure you activated the virtual environment
- Run `pip install -r requirements.txt` again

### "Connection timeout"
- Check your internet connection
- Verify watsonx.ai URL is correct
- Check firewall settings

## 📚 Next Steps

- See `README.md` for full documentation
- See `IMPLEMENTATION_GUIDE.md` for architecture details
- Add more cloud providers (Azure ML, SageMaker, etc.)
- Integrate with ContextForge for governance

## 🆘 Support

For issues or questions, see the main README.md or check the logs in the console.
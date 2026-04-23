# ML Registry MCP Server

A standalone, multi-cloud ML model registry that exposes machine learning models as MCP (Model Context Protocol) tools. This server provides a unified interface to discover and invoke ML models across multiple cloud platforms.

## 🌟 Features

- **Multi-Cloud Support**: Unified access to models from watsonx.ai, Azure ML, AWS SageMaker, Google Vertex AI
- **MCP Native**: Exposes models as MCP tools for seamless integration with MCP clients
- **Plugin Architecture**: Extensible provider system for adding new ML platforms
- **Lightweight**: No Kubernetes required, simple deployment
- **Auto-Discovery**: Automatically discovers deployed models from configured providers
- **Flexible Authentication**: Supports various auth methods per provider
- **Local Registry**: SQLite-based model metadata cache
- **Performance Tracking**: Basic metrics for model usage and latency

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- API credentials for your ML platform(s)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/ml-registry-mcp-server
cd ml-registry-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your credentials
# For watsonx.ai (Phase 1):
WATSONX_API_KEY=your-api-key
WATSONX_PROJECT_ID=your-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Enable providers
ENABLED_PROVIDERS=watsonx
```

### Running the Server

```bash
# Start the MCP server
python -m src.server

# Or with custom config
python -m src.server --config config.yaml
```

The server will start on `http://localhost:8080` by default.

## 📖 Usage

### With MCP Clients

Once running, the server exposes all discovered models as MCP tools:

```python
# Example with MCP Python SDK
import mcp

client = mcp.Client("http://localhost:8080")

# List available tools (models)
tools = await client.list_tools()

# Invoke a model
result = await client.call_tool(
    "watsonx_granite_13b_chat",
    {
        "input": "What is machine learning?",
        "parameters": {
            "max_new_tokens": 100,
            "temperature": 0.7
        }
    }
)
```

### With Claude Desktop

Add to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "ml-registry": {
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

## 🔌 Supported Providers

### Phase 1: watsonx.ai (Available Now)

- Foundation models (Granite, Llama, etc.)
- Custom deployed models
- Prompt templates
- Auto-discovery of deployments

### Phase 2: Azure ML (Coming Soon)

- Azure ML endpoints
- Managed online endpoints
- Batch endpoints

### Phase 3: AWS SageMaker (Coming Soon)

- SageMaker endpoints
- Real-time inference
- Batch transform jobs

### Phase 4: Google Vertex AI (Coming Soon)

- Vertex AI endpoints
- AutoML models
- Custom models

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              ML Registry MCP Server                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   MCP API   │  │   Registry   │  │   Metrics    │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│         │                 │                  │          │
│  ┌──────▼─────────────────▼──────────────────▼──────┐  │
│  │           Provider Plugin System                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
    │watsonx  │    │Azure ML │   │SageMaker│
    │Provider │    │Provider │   │Provider │
    └─────────┘    └─────────┘   └─────────┘
```

## 📁 Project Structure

```
ml-registry-mcp-server/
├── src/
│   ├── server.py              # Main MCP server
│   ├── config.py              # Configuration management
│   ├── registry.py            # Model registry
│   ├── discovery.py           # Model discovery
│   ├── inference.py           # Inference handler
│   ├── metrics.py             # Usage tracking
│   ├── providers/             # Provider plugins
│   │   ├── base.py            # Base provider interface
│   │   ├── watsonx.py         # watsonx.ai provider
│   │   ├── azure_ml.py        # Azure ML provider
│   │   └── sagemaker.py       # AWS SageMaker provider
│   └── mcp/
│       ├── tools.py           # MCP tool generation
│       ├── resources.py       # MCP resources
│       └── prompts.py         # MCP prompts
├── tests/
├── docs/
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ENABLED_PROVIDERS` | Comma-separated list of providers | Yes | `watsonx` |
| `MCP_TRANSPORT` | Transport protocol (sse, stdio) | No | `sse` |
| `MCP_PORT` | Server port | No | `8080` |
| `REGISTRY_DB_PATH` | SQLite database path | No | `./registry.db` |
| `CACHE_TTL` | Model metadata cache TTL (seconds) | No | `300` |
| `LOG_LEVEL` | Logging level | No | `INFO` |

### watsonx.ai Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `WATSONX_API_KEY` | IBM Cloud API key | Yes |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | Yes |
| `WATSONX_URL` | watsonx.ai API URL | No |

### Azure ML Configuration (Phase 2)

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | Yes |
| `AZURE_RESOURCE_GROUP` | Resource group name | Yes |
| `AZURE_WORKSPACE` | ML workspace name | Yes |
| `AZURE_TENANT_ID` | Azure AD tenant ID | Yes |

### AWS SageMaker Configuration (Phase 3)

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `AWS_REGION` | AWS region | Yes |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific provider tests
pytest tests/providers/test_watsonx.py
```

## 📊 Metrics

The server tracks basic metrics:

- Total model invocations
- Success/failure rates
- Average response times
- Per-model usage statistics

Access metrics via:

```bash
curl http://localhost:8080/metrics
```

## 🔐 Security

- API keys are never logged or exposed
- Credentials stored in environment variables only
- HTTPS support for production deployments
- Rate limiting per provider (configurable)

## 🤝 Contributing

Contributions are welcome! To add a new provider:

1. Create a new provider class in `src/providers/`
2. Implement the `MLProvider` interface
3. Add provider configuration
4. Add tests
5. Update documentation

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Built on the [Model Context Protocol](https://modelcontextprotocol.io/)
- Inspired by MLflow, Seldon, and BentoML
- Part of the ContextForge ecosystem

## 📞 Support

- Issues: [GitHub Issues](https://github.com/your-org/ml-registry-mcp-server/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/ml-registry-mcp-server/discussions)
- Documentation: [docs/](docs/)

## 🗺️ Roadmap

- [x] Phase 1: watsonx.ai provider
- [ ] Phase 2: Azure ML provider
- [ ] Phase 3: AWS SageMaker provider
- [ ] Phase 4: Google Vertex AI provider
- [ ] Phase 5: Custom REST API provider
- [ ] Phase 6: Model versioning support
- [ ] Phase 7: A/B testing capabilities
- [ ] Phase 8: ContextForge integration (optional governance)

---

**Status**: Phase 1 (watsonx.ai) - Active Development

**Version**: 0.1.0

**Last Updated**: 2025-01-15
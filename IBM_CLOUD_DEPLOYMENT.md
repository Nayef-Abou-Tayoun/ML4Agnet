# IBM Cloud Deployment Guide

Deploy the ML Registry MCP Server to IBM Cloud Code Engine for use with Context Forge and watsonx Orchestrate.

## Prerequisites

- IBM Cloud account
- IBM Cloud CLI installed
- Docker installed locally
- Your IBM Cloud API key: `BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_`
- Your watsonx.ai Space ID: `518df0d5-9615-41a3-a56f-30f1d0bfae24`

## Quick Deployment (5 minutes)

### Step 1: Login to IBM Cloud

```bash
# Login with your API key
ibmcloud login --apikey BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_

# Target your region (choose one)
ibmcloud target -r us-south  # or us-east, eu-gb, eu-de, jp-tok, etc.
```

### Step 2: Create Code Engine Project

```bash
# Create a new project
ibmcloud ce project create --name ml-registry

# Select the project
ibmcloud ce project select --name ml-registry
```

### Step 3: Build and Deploy

```bash
# Navigate to your project directory
cd /Users/nayefaboutayoun/Desktop/Client_Eng/bell_mcp_wxo/ml-registry-mcp-server

# Build the container image
ibmcloud ce build create \
  --name ml-registry-build \
  --source . \
  --strategy dockerfile \
  --size medium

# Wait for build to complete (check status)
ibmcloud ce buildrun list

# Deploy the application
ibmcloud ce application create \
  --name ml-registry-mcp \
  --build-source . \
  --strategy dockerfile \
  --port 8080 \
  --min-scale 1 \
  --max-scale 3 \
  --cpu 1 \
  --memory 2G \
  --env WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_ \
  --env WATSONX_SPACE_ID=518df0d5-9615-41a3-a56f-30f1d0bfae24 \
  --env WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Get your application URL
ibmcloud ce application get --name ml-registry-mcp --output url
```

### Step 4: Get Your Server URL

```bash
# Your server will be available at:
# https://ml-registry-mcp.<random-id>.<region>.codeengine.appdomain.cloud

# Save this URL - you'll need it for Context Forge and watsonx Orchestrate
export ML_REGISTRY_URL=$(ibmcloud ce application get --name ml-registry-mcp --output url)
echo "Your ML Registry URL: $ML_REGISTRY_URL"
```

## Test Your Deployment

```bash
# Test health endpoint
curl $ML_REGISTRY_URL/health

# Test model discovery
curl $ML_REGISTRY_URL/api/models

# Test MCP endpoint (for Context Forge)
curl $ML_REGISTRY_URL/mcp/tools

# View web UI
open $ML_REGISTRY_URL/ui
```

## Integration Options

### Option 1: Context Forge Integration

Configure Context Forge with your server URL:

```json
{
  "name": "ml-registry",
  "url": "https://ml-registry-mcp.<your-id>.<region>.codeengine.appdomain.cloud",
  "transport": "http",
  "endpoints": {
    "mcp": "/mcp",
    "sse": "/sse",
    "tools": "/mcp/tools"
  }
}
```

**Then in watsonx Orchestrate:**
- Context Forge will automatically expose your models as skills
- No additional configuration needed in WxO
- Skills will appear in the catalog automatically

### Option 2: Direct watsonx Orchestrate Integration

Import the OpenAPI schema directly into watsonx Orchestrate:

1. Go to watsonx Orchestrate
2. Navigate to Skills → Import
3. Use OpenAPI URL: `https://ml-registry-mcp.<your-id>.<region>.codeengine.appdomain.cloud/api/openapi.json`
4. Your models will be imported as individual skills

**Available endpoints:**
- List models: `GET /api/models`
- Get model details: `GET /api/models/{model_name}`
- Make prediction: `POST /api/models/{model_name}/predict`

## Update Deployment

```bash
# Update environment variables
ibmcloud ce application update ml-registry-mcp \
  --env WATSONX_API_KEY=<new-key> \
  --env WATSONX_SPACE_ID=<new-space-id>

# Update code (rebuild and redeploy)
ibmcloud ce application update ml-registry-mcp \
  --build-source .

# Scale up/down
ibmcloud ce application update ml-registry-mcp \
  --min-scale 2 \
  --max-scale 5
```

## Monitor Your Deployment

```bash
# View logs
ibmcloud ce application logs --name ml-registry-mcp --follow

# Check status
ibmcloud ce application get --name ml-registry-mcp

# View metrics
ibmcloud ce application events --name ml-registry-mcp
```

## Security Best Practices

### 1. Use Secrets for API Keys

```bash
# Create secret for API key
ibmcloud ce secret create --name watsonx-credentials \
  --from-literal WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_

# Update application to use secret
ibmcloud ce application update ml-registry-mcp \
  --env-from-secret watsonx-credentials
```

### 2. Enable Authentication (Optional)

Add API key authentication to your endpoints by updating `src/unified_server.py`:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API key")

# Add to endpoints
@app.get("/api/models", dependencies=[Depends(verify_api_key)])
```

### 3. Configure CORS (if needed)

Update allowed origins in `src/unified_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-wxo-instance.ibm.com",
        "https://context-forge.ibm.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Issue: Application won't start

```bash
# Check logs
ibmcloud ce application logs --name ml-registry-mcp --tail 100

# Common issues:
# - Invalid API key → Update secret
# - Port mismatch → Ensure Dockerfile exposes 8080
# - Memory issues → Increase memory allocation
```

### Issue: Models not discovered

```bash
# Test watsonx.ai connection
curl $ML_REGISTRY_URL/health

# Verify credentials
ibmcloud ce application get --name ml-registry-mcp | grep WATSONX
```

### Issue: Slow response times

```bash
# Scale up
ibmcloud ce application update ml-registry-mcp \
  --min-scale 2 \
  --cpu 2 \
  --memory 4G
```

## Cost Optimization

```bash
# Scale to zero when not in use
ibmcloud ce application update ml-registry-mcp --min-scale 0

# Use smaller resources for testing
ibmcloud ce application update ml-registry-mcp \
  --cpu 0.5 \
  --memory 1G
```

## Your Deployed Endpoints

Once deployed, your server provides:

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/` | Server info | Documentation |
| `/health` | Health check | Monitoring |
| `/ui` | Web interface | Humans |
| `/mcp` | MCP protocol | Context Forge |
| `/sse` | Event stream | Context Forge |
| `/mcp/tools` | Tool discovery | Context Forge |
| `/api/models` | List models | watsonx Orchestrate |
| `/api/models/{name}/predict` | Make prediction | watsonx Orchestrate |
| `/api/openapi.json` | OpenAPI schema | watsonx Orchestrate |
| `/api/docs` | API documentation | Developers |

## Next Steps

1. ✅ Deploy to IBM Cloud Code Engine
2. ✅ Test all endpoints
3. ✅ Choose integration method:
   - **Option A**: Configure Context Forge → Connect to WxO
   - **Option B**: Import OpenAPI directly to WxO
4. ✅ Test model predictions
5. ✅ Monitor and scale as needed

## Support

- View logs: `ibmcloud ce application logs --name ml-registry-mcp`
- Check status: `ibmcloud ce application get --name ml-registry-mcp`
- IBM Cloud docs: https://cloud.ibm.com/docs/codeengine
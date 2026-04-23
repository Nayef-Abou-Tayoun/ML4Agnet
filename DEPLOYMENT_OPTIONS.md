# ML Registry Deployment Options

Since you don't have Code Engine project creation permissions, here are alternative deployment options:

## Option 1: Request Code Engine Access (Recommended)

Contact your IBM Cloud administrator to:
1. Grant you Code Engine Editor/Manager role
2. Create a Code Engine project for you
3. Give you deployment permissions

Once you have access, use the commands in `IBM_CLOUD_DEPLOYMENT.md`.

## Option 2: Deploy with Docker Locally (Quick Test)

Run the server locally with Docker:

```bash
# Build the image
cd /Users/nayefaboutayoun/Desktop/Client_Eng/bell_mcp_wxo/ml-registry-mcp-server
docker build -t ml-registry-mcp .

# Run the container
docker run -d \
  --name ml-registry \
  -p 8080:8080 \
  -e WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_ \
  -e WATSONX_SPACE_ID=518df0d5-9615-41a3-a56f-30f1d0bfae24 \
  -e WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  ml-registry-mcp

# Test it
curl http://localhost:8080/health
curl http://localhost:8080/api/models

# View logs
docker logs -f ml-registry
```

**Then expose with ngrok for testing:**

```bash
# Install ngrok if needed
brew install ngrok

# Expose your local server
ngrok http 8080

# Use the ngrok URL with Context Forge or watsonx Orchestrate
# Example: https://abc123.ngrok.io
```

## Option 3: Deploy to IBM Cloud Kubernetes Service

If you have access to IKS:

```bash
# Create deployment.yaml
cat > deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-registry-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-registry-mcp
  template:
    metadata:
      labels:
        app: ml-registry-mcp
    spec:
      containers:
      - name: ml-registry-mcp
        image: ml-registry-mcp:latest
        ports:
        - containerPort: 8080
        env:
        - name: WATSONX_API_KEY
          value: "BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_"
        - name: WATSONX_SPACE_ID
          value: "518df0d5-9615-41a3-a56f-30f1d0bfae24"
        - name: WATSONX_URL
          value: "https://us-south.ml.cloud.ibm.com"
---
apiVersion: v1
kind: Service
metadata:
  name: ml-registry-mcp
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
  selector:
    app: ml-registry-mcp
EOF

# Deploy
kubectl apply -f deployment.yaml

# Get external IP
kubectl get service ml-registry-mcp
```

## Option 4: Deploy to Other Cloud Providers

### AWS ECS/Fargate

```bash
# Push to ECR
aws ecr create-repository --repository-name ml-registry-mcp
docker tag ml-registry-mcp:latest <account>.dkr.ecr.us-east-1.amazonaws.com/ml-registry-mcp:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/ml-registry-mcp:latest

# Create ECS task definition and service
# Use AWS Console or CLI
```

### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project>/ml-registry-mcp
gcloud run deploy ml-registry-mcp \
  --image gcr.io/<project>/ml-registry-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_,WATSONX_SPACE_ID=518df0d5-9615-41a3-a56f-30f1d0bfae24
```

### Azure Container Instances

```bash
az container create \
  --resource-group myResourceGroup \
  --name ml-registry-mcp \
  --image ml-registry-mcp:latest \
  --dns-name-label ml-registry-mcp \
  --ports 8080 \
  --environment-variables \
    WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_ \
    WATSONX_SPACE_ID=518df0d5-9615-41a3-a56f-30f1d0bfae24
```

## Option 5: Run Locally (Development/Testing)

```bash
cd /Users/nayefaboutayoun/Desktop/Client_Eng/bell_mcp_wxo/ml-registry-mcp-server

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export WATSONX_API_KEY=BZNoEtfZ8HUtRwZQeSvJkWwTqZJaNyyAE5b1xilVwoD_
export WATSONX_SPACE_ID=518df0d5-9615-41a3-a56f-30f1d0bfae24
export WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Run the unified server
python -m src.unified_server

# Server runs on http://localhost:8080
```

**Expose with ngrok for external access:**

```bash
# In another terminal
ngrok http 8080

# Your public URL: https://abc123.ngrok.io
```

## Current Status: Running Locally

Your ML Registry is currently ready to run. Here's what you can do RIGHT NOW:

### 1. Test Locally

```bash
# The server is already configured with your credentials in .env
cd /Users/nayefaboutayoun/Desktop/Client_Eng/bell_mcp_wxo/ml-registry-mcp-server
source venv/bin/activate
python -m src.unified_server
```

### 2. Access the Server

- **Web UI**: http://localhost:8080/ui
- **Health Check**: http://localhost:8080/health
- **List Models**: http://localhost:8080/api/models
- **MCP Tools**: http://localhost:8080/mcp/tools
- **API Docs**: http://localhost:8080/api/docs

### 3. Expose Publicly (for WxO/Context Forge)

```bash
# Install ngrok
brew install ngrok

# Expose your server
ngrok http 8080

# You'll get a URL like: https://abc123.ngrok.io
# Use this URL in Context Forge or watsonx Orchestrate
```

### 4. Integration

**For Context Forge:**
```json
{
  "name": "ml-registry",
  "url": "https://abc123.ngrok.io",
  "transport": "http",
  "endpoints": {
    "mcp": "/mcp",
    "sse": "/sse"
  }
}
```

**For watsonx Orchestrate (direct):**
- Import OpenAPI: `https://abc123.ngrok.io/api/openapi.json`
- Or use REST endpoints directly

## Recommended Next Steps

1. **Immediate**: Run locally with ngrok for testing
   ```bash
   python -m src.unified_server &
   ngrok http 8080
   ```

2. **Short-term**: Request Code Engine access from your admin

3. **Long-term**: Deploy to Code Engine for production use

## What You Have Now

✅ **Fully functional ML Registry MCP Server**
- Discovers models from watsonx.ai
- Supports MCP protocol (Context Forge)
- Supports REST API (direct WxO)
- Web UI for documentation
- Ready to deploy

✅ **Your discovered model**: `demand-forecasting-ml`
- 19 input parameters
- Complete schema available
- Ready for predictions

✅ **Multiple deployment options**
- Local with ngrok (immediate)
- Docker (portable)
- Code Engine (when you get access)
- Other clouds (AWS, GCP, Azure)

## Need Help?

Contact your IBM Cloud administrator to:
- Grant Code Engine permissions
- Create a project for you
- Or provide alternative deployment infrastructure
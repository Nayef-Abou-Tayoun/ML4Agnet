# Deployment Guide

## Quick Deployment to IBM Cloud Code Engine

### Prerequisites

1. **IBM Cloud CLI** installed
   ```bash
   curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
   ```

2. **Docker** installed and running

3. **IBM Cloud Account** with Code Engine access

### Step 1: Login to IBM Cloud

```bash
ibmcloud login
```

### Step 2: Set up watsonx credentials as secrets

```bash
# Select your Code Engine project
ibmcloud ce project select --name ml-registry

# Create secret with watsonx credentials
ibmcloud ce secret create --name watsonx-credentials \
  --from-literal WATSONX_API_KEY=your-api-key \
  --from-literal WATSONX_SPACE_ID=your-space-id \
  --from-literal WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### Step 3: Deploy using the script

```bash
./deploy.sh
```

The script will:
1. Build the Docker image
2. Push to IBM Cloud Container Registry
3. Deploy/Update the Code Engine application
4. Display the application URL

### Step 4: Verify Deployment

```bash
# Get application URL
ibmcloud ce app get --name mlregistry12 --output url

# Test health endpoint
curl https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/health

# Test MCP tools list
curl -X POST https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

## Manual Deployment

If you prefer manual deployment:

### 1. Build and Push Image

```bash
# Build
docker build -t ml-registry-mcp-server:latest .

# Tag for IBM Cloud Registry
docker tag ml-registry-mcp-server:latest us.icr.io/your-namespace/ml-registry-mcp-server:latest

# Login to registry
ibmcloud cr login

# Push
docker push us.icr.io/your-namespace/ml-registry-mcp-server:latest
```

### 2. Deploy to Code Engine

```bash
# Create/Update application
ibmcloud ce app update --name mlregistry12 \
  --image us.icr.io/your-namespace/ml-registry-mcp-server:latest \
  --env-from-secret watsonx-credentials \
  --port 8080 \
  --min-scale 1 \
  --max-scale 3 \
  --cpu 0.5 \
  --memory 1G
```

## Environment Variables

The following environment variables are required:

- `WATSONX_API_KEY`: Your IBM Cloud API key
- `WATSONX_SPACE_ID`: Your watsonx.ai deployment space ID
- `WATSONX_URL`: watsonx.ai API URL (default: https://us-south.ml.cloud.ibm.com)

## Monitoring

### View Logs
```bash
ibmcloud ce app logs --name mlregistry12 --follow
```

### Check Application Status
```bash
ibmcloud ce app get --name mlregistry12
```

### View Application Events
```bash
ibmcloud ce app events --name mlregistry12
```

## Rollback

If you need to rollback to a previous version:

```bash
# List revisions
ibmcloud ce revision list --application mlregistry12

# Update to specific revision
ibmcloud ce app update --name mlregistry12 --revision <revision-name>
```

## Troubleshooting

### Application not starting
1. Check logs: `ibmcloud ce app logs --name mlregistry12`
2. Verify secrets are set correctly
3. Check resource limits (CPU/Memory)

### Connection issues
1. Verify the application is running: `ibmcloud ce app get --name mlregistry12`
2. Check if the port is correct (8080)
3. Test health endpoint

### Model discovery issues
1. Verify watsonx credentials are correct
2. Check space ID is valid
3. Ensure models are deployed in the specified space

## Current Deployment

**Production URL**: https://mlregistry12.27jid12fsm9n.us-south.codeengine.appdomain.cloud

**Endpoints**:
- Health: `/health`
- MCP: `/mcp`
- SSE: `/sse`
- API Docs: `/api/docs`
- UI: `/ui`

## Updates

After making code changes:

1. Commit and push to GitHub
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. Redeploy
   ```bash
   ./deploy.sh
   ```

The deployment script will automatically build and deploy the latest code.
# Integrating ML Registry with watsonx Orchestrate

## Overview

This guide shows you how to expose your custom ML models from watsonx.ai to watsonx Orchestrate (WxO) using the ML Registry MCP Server.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           watsonx Orchestrate (WxO)                     │
│  - Conversational AI                                    │
│  - Skill orchestration                                  │
└─────────────────────────────────────────────────────────┘
                         │
                         │ REST API / OpenAPI
                         ▼
┌─────────────────────────────────────────────────────────┐
│         ML Registry MCP Server (This Project)           │
│  - Auto-discovers watsonx.ai models                     │
│  - Exposes as REST endpoints                            │
│  - Provides OpenAPI spec                                │
└─────────────────────────────────────────────────────────┘
                         │
                         │ watsonx.ai API
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Your Deployed ML Models                    │
│  - Fraud detection                                      │
│  - Churn prediction                                     │
│  - Demand forecasting                                   │
└─────────────────────────────────────────────────────────┘
```

## Step 1: View Your Models

### Option A: Via Web UI

1. Open http://localhost:8081
2. Go to Settings and add your watsonx.ai credentials
3. Restart the server
4. View all discovered models on the home page

### Option B: Via API

```bash
# List all models
curl http://localhost:8081/api/models

# Example response:
{
  "models": [
    {
      "id": "deployment-123",
      "name": "fraud_detection_model",
      "provider": "watsonx",
      "model_type": "classification",
      "framework": "scikit-learn",
      "status": "deployed"
    }
  ]
}
```

## Step 2: Get Model Endpoints for WxO

Each discovered model gets its own REST endpoint that WxO can call:

### Model Endpoint Format

```
POST http://localhost:8081/api/models/{model_id}/predict
```

### Example: Fraud Detection Model

```bash
# Make prediction
curl -X POST http://localhost:8081/api/models/deployment-123/predict \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "fields": ["amount", "merchant_category", "time_of_day"],
      "values": [[500.00, "electronics", "14:30"]]
    }
  }'

# Response:
{
  "predictions": [{
    "fraud_probability": 0.85,
    "is_fraud": true
  }],
  "model_id": "deployment-123",
  "provider": "watsonx"
}
```

## Step 3: Generate OpenAPI Spec for WxO

The ML Registry automatically generates an OpenAPI specification that WxO can import:

### Get OpenAPI Spec

```bash
# Get full OpenAPI specification
curl http://localhost:8081/openapi.json > ml-models-openapi.json
```

### OpenAPI Spec Structure

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "ML Model Registry API",
    "version": "0.1.0"
  },
  "paths": {
    "/api/models": {
      "get": {
        "summary": "List all models",
        "responses": {
          "200": {
            "description": "List of models"
          }
        }
      }
    },
    "/api/models/{model_id}/predict": {
      "post": {
        "summary": "Make prediction",
        "parameters": [
          {
            "name": "model_id",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ],
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "input_data": {"type": "object"}
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Step 4: Add to watsonx Orchestrate

### Method 1: Import OpenAPI Spec

1. **Export OpenAPI spec**:
   ```bash
   curl http://localhost:8081/openapi.json > ml-models.json
   ```

2. **In watsonx Orchestrate**:
   - Go to **Skills** → **Add Skill**
   - Select **Import OpenAPI**
   - Upload `ml-models.json`
   - Configure authentication (if needed)

3. **Test the skill**:
   - WxO will create skills for each endpoint
   - Test with sample data
   - Add to your assistant

### Method 2: Manual Skill Creation

For each model, create a custom skill in WxO:

1. **Skill Name**: `Fraud Detection Model`
2. **Endpoint**: `http://localhost:8081/api/models/deployment-123/predict`
3. **Method**: `POST`
4. **Input Schema**:
   ```json
   {
     "input_data": {
       "fields": ["amount", "merchant_category", "time_of_day"],
       "values": [[500.00, "electronics", "14:30"]]
     }
   }
   ```
5. **Output Schema**:
   ```json
   {
     "predictions": [{"fraud_probability": 0.85, "is_fraud": true}]
   }
   ```

## Step 5: Deploy for Production

### Option A: Deploy to IBM Cloud Code Engine

```bash
# Build and deploy
ibmcloud ce application create \
  --name ml-registry \
  --image your-registry/ml-registry:latest \
  --port 8081 \
  --env WATSONX_API_KEY=your-key \
  --env WATSONX_PROJECT_ID=your-project

# Get public URL
ibmcloud ce application get --name ml-registry
```

### Option B: Deploy to Kubernetes

```bash
# Create deployment
kubectl create deployment ml-registry \
  --image=your-registry/ml-registry:latest

# Expose service
kubectl expose deployment ml-registry \
  --type=LoadBalancer \
  --port=8081

# Get external IP
kubectl get service ml-registry
```

### Option C: Use ContextForge (Recommended)

Deploy through ContextForge for enterprise features:

```bash
# Register ML Registry as a gateway in ContextForge
curl -X POST http://contextforge:8000/gateways \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "ML Model Registry",
    "url": "http://ml-registry:8081",
    "type": "rest"
  }'
```

## Step 6: Configure WxO to Use Production URL

Update your WxO skills to use the production URL:

```
# Development
http://localhost:8081/api/models/{model_id}/predict

# Production (Code Engine)
https://ml-registry.1234.us-south.codeengine.appdomain.cloud/api/models/{model_id}/predict

# Production (ContextForge)
https://contextforge.your-domain.com/ml-models/{model_id}/predict
```

## Example: Complete WxO Integration

### 1. Discover Models

```bash
curl http://localhost:8081/api/models
```

**Response**:
```json
{
  "models": [
    {
      "id": "fraud-det-001",
      "name": "fraud_detection_model",
      "model_type": "classification"
    },
    {
      "id": "churn-pred-002",
      "name": "churn_predictor",
      "model_type": "classification"
    }
  ]
}
```

### 2. Create WxO Skills

**Skill 1: Check Fraud**
- **Endpoint**: `POST /api/models/fraud-det-001/predict`
- **Input**: Transaction details
- **Output**: Fraud probability

**Skill 2: Predict Churn**
- **Endpoint**: `POST /api/models/churn-pred-002/predict`
- **Input**: Customer data
- **Output**: Churn probability

### 3. Use in WxO Conversation

```
User: "Check if this transaction is fraudulent: $500 at electronics store at 2am"

WxO: [Calls fraud_detection_model skill]
     "This transaction has an 85% probability of being fraudulent. 
      I recommend blocking it and contacting the customer."

User: "What's the churn risk for customer ID 12345?"

WxO: [Calls churn_predictor skill]
     "Customer 12345 has a 72% churn probability. 
      Consider offering a retention incentive."
```

## Authentication Options

### Option 1: No Auth (Development Only)

```bash
# No authentication required
curl http://localhost:8081/api/models
```

### Option 2: API Key (Recommended)

```bash
# Add API key to .env
API_KEY=your-secret-key

# Use in requests
curl -H "X-API-Key: your-secret-key" \
  http://localhost:8081/api/models
```

### Option 3: OAuth (Enterprise)

Use ContextForge for OAuth integration:

```bash
# Get OAuth token
TOKEN=$(curl -X POST https://contextforge/oauth/token \
  -d "grant_type=client_credentials" \
  -d "client_id=wxo" \
  -d "client_secret=secret")

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://contextforge/ml-models
```

## Monitoring and Observability

### View Model Usage

```bash
# Get model metrics
curl http://localhost:8081/api/models/fraud-det-001/metrics

# Response:
{
  "total_predictions": 1523,
  "avg_latency_ms": 45,
  "success_rate": 0.998,
  "last_24h": {
    "predictions": 234,
    "errors": 2
  }
}
```

### Health Check

```bash
# Check if models are accessible
curl http://localhost:8081/api/health

# Response:
{
  "status": "ok",
  "providers": {
    "watsonx": true
  }
}
```

## Troubleshooting

### Models Not Appearing

1. Check watsonx.ai credentials in Settings
2. Verify models are deployed in watsonx.ai
3. Check server logs for errors
4. Test connection in Settings page

### WxO Can't Reach Endpoint

1. Ensure ML Registry is publicly accessible
2. Check firewall rules
3. Verify URL in WxO skill configuration
4. Test endpoint with curl first

### Prediction Errors

1. Check input data format matches model schema
2. Verify model is still deployed in watsonx.ai
3. Check model logs in watsonx.ai
4. Test prediction directly via UI

## Next Steps

1. ✅ Configure watsonx.ai credentials in Settings
2. ✅ View discovered models in UI
3. ✅ Test predictions via API
4. ✅ Export OpenAPI spec
5. ✅ Import into watsonx Orchestrate
6. ✅ Create conversational flows
7. ✅ Deploy to production

## Support

For issues or questions:
- Check logs: Server console output
- Test API: Use curl or Postman
- View UI: http://localhost:8081
- Settings: http://localhost:8081/settings
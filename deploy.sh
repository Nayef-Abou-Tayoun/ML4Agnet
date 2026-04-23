#!/bin/bash
# Deployment script for IBM Cloud Code Engine

set -e

echo "=========================================="
echo "ML Registry MCP Server - Deployment"
echo "=========================================="

# Configuration
PROJECT_NAME="ml-registry"
APP_NAME="mlregistry12"
REGION="us-south"
IMAGE_NAME="ml-registry-mcp-server"

# Check if ibmcloud CLI is installed
if ! command -v ibmcloud &> /dev/null; then
    echo "❌ IBM Cloud CLI not found. Please install it first:"
    echo "   https://cloud.ibm.com/docs/cli?topic=cli-getting-started"
    exit 1
fi

# Check if logged in
if ! ibmcloud target &> /dev/null; then
    echo "❌ Not logged in to IBM Cloud. Please run: ibmcloud login"
    exit 1
fi

echo ""
echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME:latest .

echo ""
echo "🏷️  Tagging image for IBM Cloud Container Registry..."
REGISTRY="us.icr.io"
NAMESPACE=$(ibmcloud cr namespace-list | grep -v "Listing" | grep -v "Name" | head -1 | awk '{print $1}')

if [ -z "$NAMESPACE" ]; then
    echo "Creating new namespace..."
    NAMESPACE="ml-registry-ns"
    ibmcloud cr namespace-add $NAMESPACE
fi

docker tag $IMAGE_NAME:latest $REGISTRY/$NAMESPACE/$IMAGE_NAME:latest

echo ""
echo "🚀 Pushing image to IBM Cloud Container Registry..."
ibmcloud cr login
docker push $REGISTRY/$NAMESPACE/$IMAGE_NAME:latest

echo ""
echo "☁️  Deploying to Code Engine..."

# Check if project exists
if ! ibmcloud ce project get --name $PROJECT_NAME &> /dev/null; then
    echo "Creating Code Engine project..."
    ibmcloud ce project create --name $PROJECT_NAME
fi

# Select project
ibmcloud ce project select --name $PROJECT_NAME

# Check if app exists
if ibmcloud ce app get --name $APP_NAME &> /dev/null; then
    echo "Updating existing application..."
    ibmcloud ce app update --name $APP_NAME \
        --image $REGISTRY/$NAMESPACE/$IMAGE_NAME:latest \
        --env-from-secret watsonx-credentials \
        --port 8080 \
        --min-scale 1 \
        --max-scale 3 \
        --cpu 0.5 \
        --memory 1G
else
    echo "Creating new application..."
    ibmcloud ce app create --name $APP_NAME \
        --image $REGISTRY/$NAMESPACE/$IMAGE_NAME:latest \
        --env-from-secret watsonx-credentials \
        --port 8080 \
        --min-scale 1 \
        --max-scale 3 \
        --cpu 0.5 \
        --memory 1G
fi

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Application URL:"
ibmcloud ce app get --name $APP_NAME --output url

echo ""
echo "📊 To view logs:"
echo "   ibmcloud ce app logs --name $APP_NAME"
echo ""
echo "🔍 To check status:"
echo "   ibmcloud ce app get --name $APP_NAME"

# Made with Bob

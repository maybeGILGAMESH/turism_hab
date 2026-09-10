#!/bin/bash

# Docker Deploy Script for Moscow Metro App
# Usage: ./docker-deploy.sh [registry] [tag]

set -e

# Default values
REGISTRY=${1:-"your-registry"}
TAG=${2:-"latest"}
IMAGE_NAME="moscow-metro-app"
CONTAINER_NAME="moscow-metro-app"

echo "🚀 Deploying Moscow Metro Cultural Heritage Recognition System"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Image: $REGISTRY/$IMAGE_NAME:$TAG"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Stop and remove existing container if it exists
if docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
    echo "🔄 Stopping existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# Pull the latest image
echo "📥 Pulling image from registry..."
docker pull $REGISTRY/$IMAGE_NAME:$TAG

# Create necessary directories
echo "📁 Creating local directories..."
mkdir -p ./artifacts ./uploads ./data

# Run the container
echo "🚀 Starting container..."
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 8000:8000 \
    -p 8501:8501 \
    -p 8080:8080 \
    -v $(pwd)/artifacts:/app/artifacts:ro \
    -v $(pwd)/uploads:/app/uploads \
    -v $(pwd)/data:/app/data \
    $REGISTRY/$IMAGE_NAME:$TAG

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Check container status
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$CONTAINER_NAME.*Up"; then
    echo ""
    echo "✅ Deployment completed successfully!"
    echo ""
    echo "🌐 Access your application:"
    echo "   Backend API: http://localhost:8000"
    echo "   Streamlit UI: http://localhost:8501"
    echo "   HTML UI: http://localhost:8080/static/index.html"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "📊 Container status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep $CONTAINER_NAME
    echo ""
    echo "📝 Container logs: docker logs $CONTAINER_NAME"
    echo "🛑 Stop container: docker stop $CONTAINER_NAME"
else
    echo "❌ Container failed to start properly"
    echo "📝 Check logs: docker logs $CONTAINER_NAME"
    exit 1
fi

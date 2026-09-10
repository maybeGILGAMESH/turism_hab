#!/bin/bash

# Docker Build Script for Moscow Metro App
# Usage: ./docker-build.sh [registry] [tag]

set -e

# Default values
REGISTRY=${1:-"your-registry"}
TAG=${2:-"latest"}
IMAGE_NAME="moscow-metro-app"

echo "🐳 Building Docker image for Moscow Metro Cultural Heritage Recognition System"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"
echo "Image: $REGISTRY/$IMAGE_NAME:$TAG"
echo ""

# Build the image
echo "📦 Building Docker image..."
docker build -t $REGISTRY/$IMAGE_NAME:$TAG .

# Tag as latest if not already
if [ "$TAG" != "latest" ]; then
    echo "🏷️  Tagging as latest..."
    docker tag $REGISTRY/$IMAGE_NAME:$TAG $REGISTRY/$IMAGE_NAME:latest
fi

echo ""
echo "✅ Build completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Push to registry: docker push $REGISTRY/$IMAGE_NAME:$TAG"
echo "2. Run locally: docker-compose up"
echo "3. Run standalone: docker run -p 8000:8000 -p 8501:8501 -p 8080:8080 $REGISTRY/$IMAGE_NAME:$TAG"
echo ""
echo "🌐 Access URLs:"
echo "   Backend API: http://localhost:8000"
echo "   Streamlit UI: http://localhost:8501"
echo "   HTML UI: http://localhost:8080/static/index.html"

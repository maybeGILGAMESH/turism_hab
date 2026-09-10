# 🐳 Docker Deployment Guide

This guide explains how to containerize and deploy your Moscow Metro Cultural Heritage Recognition System using Docker.

## 📋 Prerequisites

- Docker installed on your system
- Docker Compose (usually comes with Docker)
- Access to a Docker registry (Docker Hub, GitHub Container Registry, etc.)

## 🏗️ Building the Docker Image

### Option 1: Using the Build Script
```bash
# Build with default settings
./docker-build.sh

# Build with custom registry and tag
./docker-build.sh your-username v1.0.0
```

### Option 2: Manual Build
```bash
# Build the image
docker build -t moscow-metro-app .

# Tag for registry
docker tag moscow-metro-app your-username/moscow-metro-app:latest
docker tag moscow-metro-app your-username/moscow-metro-app:v1.0.0
```

## 📤 Pushing to Docker Registry

### Docker Hub
```bash
# Login to Docker Hub
docker login

# Push images
docker push your-username/moscow-metro-app:latest
docker push your-username/moscow-metro-app:v1.0.0
```

### GitHub Container Registry
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag for GitHub
docker tag moscow-metro-app ghcr.io/your-username/moscow-metro-app:latest

# Push
docker push ghcr.io/your-username/moscow-metro-app:latest
```

## 🚀 Running Locally

### Using Docker Compose (Recommended)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Using Docker Run
```bash
# Run the container
docker run -d \
    --name moscow-metro-app \
    -p 8000:8000 \
    -p 8501:8501 \
    -p 8080:8080 \
    -v $(pwd)/artifacts:/app/artifacts:ro \
    -v $(pwd)/uploads:/app/uploads \
    -v $(pwd)/data:/app/data \
    your-username/moscow-metro-app:latest
```

## 🌐 Deploying to Another Device

### Step 1: On the Target Device
1. Install Docker
2. Create a directory for the app
3. Copy the `docker-deploy.sh` script

### Step 2: Deploy
```bash
# Make script executable
chmod +x docker-deploy.sh

# Deploy with your registry
./docker-deploy.sh your-username latest
```

### Step 3: Access the App
From any device on the same network:
- **Backend API**: `http://TARGET_DEVICE_IP:8000`
- **Streamlit UI**: `http://TARGET_DEVICE_IP:8501`
- **HTML UI**: `http://TARGET_DEVICE_IP:8080/static/index.html`

## 🔧 Configuration

### Environment Variables
You can customize the app behavior using environment variables:

```bash
# In docker-compose.yml or docker run command
environment:
  - API_BASE_URL=http://your-api-url:8000
  - DEVICE=cpu  # or cuda for GPU support
```

### Port Mapping
The default ports are:
- **8000**: Backend API
- **8501**: Streamlit frontend
- **8080**: HTML frontend

You can change these in `docker-compose.yml` or the `docker run` command.

## 📊 Monitoring and Management

### Container Status
```bash
# Check running containers
docker ps

# View container logs
docker logs moscow-metro-app

# Access container shell
docker exec -it moscow-metro-app bash
```

### Health Checks
The container includes health checks that monitor the API endpoint:
```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' moscow-metro-app
```

## 🧹 Cleanup

### Remove Container
```bash
docker stop moscow-metro-app
docker rm moscow-metro-app
```

### Remove Image
```bash
docker rmi your-username/moscow-metro-app:latest
```

### Clean Up Everything
```bash
docker system prune -a
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   sudo netstat -tulpn | grep :8000
   
   # Kill the process or change ports in docker-compose.yml
   ```

2. **Permission Issues**
   ```bash
   # Fix directory permissions
   sudo chown -R $USER:$USER ./artifacts ./uploads ./data
   ```

3. **Container Won't Start**
   ```bash
   # Check logs
   docker logs moscow-metro-app
   
   # Check if artifacts directory exists
   ls -la artifacts/
   ```

4. **Memory Issues**
   ```bash
   # Increase Docker memory limit in Docker Desktop settings
   # Or use --memory flag
   docker run --memory=4g your-image
   ```

## 📱 Network Access

### From Same Network
- Use the target device's local IP address
- Ensure firewall allows connections on ports 8000, 8501, 8080

### From Internet
- Configure port forwarding on your router
- Use your public IP address
- Consider using a reverse proxy (nginx, traefik) for production

## 🔒 Security Considerations

- The app currently allows CORS from any origin (`allow_origins=["*"]`)
- For production, restrict CORS origins
- Consider adding authentication
- Use HTTPS in production
- Regularly update the base image and dependencies

## 📈 Scaling

### Multiple Instances
```bash
# Scale with docker-compose
docker-compose up -d --scale metro-app=3

# Or use Docker Swarm/Kubernetes for production
```

### Load Balancing
- Use nginx or traefik as a reverse proxy
- Configure health checks and failover
- Monitor resource usage

---

For more information, check the main README.md and the application code.

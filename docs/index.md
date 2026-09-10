# 🚇 Moscow Metro Cultural Heritage Recognition System

Welcome to the documentation for the **Moscow Metro Cultural Heritage Recognition System** - an AI-powered platform for identifying cultural heritage objects in Moscow Metro stations.

## 🌟 Overview

This system combines cutting-edge AI technologies with cultural heritage preservation to provide:

- **Image Recognition**: Identify cultural objects using CLIP embeddings and FAISS vector search
- **RAG System**: Retrieval-Augmented Generation for intelligent object descriptions
- **Web Interface**: User-friendly web application with visitor and admin interfaces
- **REST API**: Comprehensive API for integration and automation
- **Docker Support**: Easy deployment and scaling with containerization

## 🚀 Quick Start

Get up and running in minutes:

```bash
# Clone the repository
git clone https://github.com/frznfrgg/sbermetro.git
cd sbermetro

# Install dependencies
pip install -r requirements.txt

# Run the system
python run_system.py
```

## 🏗️ Architecture

The system is built with a modular architecture:

- **Backend API**: FastAPI-based REST API
- **RAG Searcher**: CLIP-based image embeddings with FAISS vector search
- **Frontend Interfaces**: Streamlit admin panel and HTML visitor interface
- **AI Models**: CLIP for image understanding and similarity search

## 🔧 Key Components

### Backend API (`app.py`)
- FastAPI-based REST API
- Image upload and processing
- Object management endpoints
- Health monitoring

### RAG Searcher (`rag_searcher.py`)
- CLIP-based image embeddings
- FAISS vector similarity search
- Intelligent object classification
- Description retrieval

### Frontend Interfaces
- **Streamlit Admin Panel**: Full-featured management interface
- **HTML Visitor Interface**: Simple, responsive web interface
- **REST API**: Programmatic access for developers

## 📱 Features

- 🖼️ **Image Recognition**: Upload photos to identify cultural objects
- 🔍 **Smart Search**: AI-powered similarity search across the database
- 📊 **Admin Management**: Add, edit, and manage cultural heritage objects
- 🌐 **Multi-Interface**: Choose between Streamlit and HTML interfaces
- 🐳 **Docker Ready**: Containerized deployment for any environment
- 📈 **Monitoring**: Health checks and system statistics

## 🎯 Use Cases

- **Cultural Heritage Preservation**: Document and catalog metro station artifacts
- **Tourism & Education**: Provide information about cultural objects to visitors
- **Research & Analysis**: Study patterns and relationships in cultural heritage
- **Digital Archives**: Create searchable digital collections of cultural objects

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **AI/ML**: CLIP, FAISS, PyTorch
- **Frontend**: Streamlit, HTML/CSS/JavaScript
- **Database**: FAISS vector database, JSON metadata
- **Deployment**: Docker, Docker Compose
- **Documentation**: MkDocs, Material theme

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t moscow-metro-app .
docker run -p 8000:8000 -p 8501:8501 -p 8080:8080 moscow-metro-app
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the system
python run_system.py
```

## 📚 Documentation

This documentation is built with MkDocs and Material theme, providing:

- **Modern Design**: Clean, responsive interface
- **Search Functionality**: Find information quickly
- **Navigation**: Easy browsing through sections
- **Code Examples**: Practical implementation examples

## 🤝 Contributing

We welcome contributions! Please see our repository for details on how to contribute to this project.

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/frznfrgg/sbermetro/issues)
- **Repository**: [GitHub Repository](https://github.com/frznfrgg/sbermetro)
- **Documentation**: This site and [README.md](https://github.com/frznfrgg/sbermetro/blob/main/README.md)

---

<div align="center">

**Built with ❤️ for Cultural Heritage Preservation**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/frznfrgg/sbermetro/blob/main/LICENSE)

</div>

# Getting Started

Welcome to the Moscow Metro Cultural Heritage Recognition System! This guide will help you get up and running quickly.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the System

```bash
python run_system.py
```

The system will start and be available at `http://localhost:8000`

### 3. Upload an Image

1. Go to the main page
2. Click "Upload Image"
3. Select a photo of a metro station
4. Choose the station name (optional)
5. Click "Recognize"

## What You Can Do

### Image Recognition
- Upload photos of metro stations
- Get AI-powered recognition of cultural objects
- View detailed information about each object

### Explore Objects
- Browse the complete database
- Search by station or object type
- View high-quality images

### Learn About History
- Discover the cultural significance
- Learn about artists and architects
- Understand historical context

## System Requirements

- Python 3.8+
- 4GB RAM minimum
- Internet connection for first run
- Modern web browser

## Troubleshooting

### Common Issues

**"Model not found" error:**
- Run `python -c "import clip; clip.load('ViT-B/32')"` to download models

**"Port already in use" error:**
- Change port in `run_system.py` or stop other services

**"CUDA not available" warning:**
- System will use CPU (slower but functional)

### Getting Help

- Check the [API Reference](../api/) for technical details
- Review [User Guide](../user-guide/index.md) for detailed instructions
- Open an issue on GitHub for bugs

## Next Steps

- Try different metro stations
- Explore the object database
- Learn about the AI technology behind the system
- Check out the development documentation

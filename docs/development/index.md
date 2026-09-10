# Development Guide

Welcome to the Development Guide for the Moscow Metro Cultural Heritage Recognition System.

## Project Structure

```
sber/
├── app.py              # FastAPI main application
├── rag_searcher.py     # RAG search functionality
├── frontend.py         # Web interface
├── run_system.py       # System startup script
├── docs/               # Documentation
├── artifacts/          # AI models and indexes
├── data/               # Image data
└── static/             # Static web files
```

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **PyTorch**: Deep learning framework
- **CLIP**: OpenAI's image-text model
- **FAISS**: Vector similarity search
- **LangChain**: AI application framework

### Frontend
- **HTML/CSS/JavaScript**: Web interface
- **Material Design**: UI components
- **Responsive Design**: Mobile-friendly layout

### AI/ML
- **Computer Vision**: Image recognition
- **Natural Language Processing**: Text understanding
- **Vector Search**: Similarity matching
- **Embeddings**: High-dimensional representations

## Development Setup

### Prerequisites
- Python 3.8+
- Git
- Virtual environment (recommended)

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/sbermetro.git
cd sbermetro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally
```bash
# Start the system
python run_system.py

# Or run components separately
python app.py          # FastAPI server
python frontend.py     # Frontend interface
```

## Code Style

### Python
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for functions
- Keep functions focused and small

### Documentation
- Use clear, concise language
- Include code examples
- Update docs when changing code
- Follow markdown best practices

## Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest test_system.py

# Run with coverage
python -m pytest --cov=.
```

### Writing Tests
- Test both success and failure cases
- Mock external dependencies
- Use descriptive test names
- Keep tests independent

## Contributing

### Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

### Code Review
- All changes require review
- Address feedback promptly
- Ensure CI/CD passes
- Update documentation as needed

## Deployment

### Local Testing
```bash
# Build documentation
mkdocs build

# Serve locally
mkdocs serve
```

### Production
- Documentation auto-deploys to GitHub Pages
- Backend can be deployed to various cloud platforms
- Use Docker for containerized deployment

## Troubleshooting

### Common Issues
- **Import errors**: Check virtual environment
- **Model loading**: Verify artifacts directory
- **Port conflicts**: Change port numbers
- **Memory issues**: Reduce batch sizes

### Getting Help
- Check existing issues
- Review documentation
- Ask questions in discussions
- Open new issues for bugs

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PyTorch Tutorials](https://pytorch.org/tutorials/)
- [CLIP Paper](https://arxiv.org/abs/2103.00020)
- [FAISS Documentation](https://faiss.ai/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

# API Reference

Welcome to the API Reference for the Moscow Metro Cultural Heritage Recognition System.

## Overview

This system provides a comprehensive API for recognizing and searching cultural heritage objects in Moscow Metro stations using AI-powered image analysis and RAG (Retrieval-Augmented Generation).

## API Components

### [FastAPI Application](app.md)
The main REST API server that handles:
- Image uploads and processing
- Cultural heritage recognition
- Station and object information
- User interactions

### [RAG Searcher](rag_searcher.md)
AI-powered search functionality using:
- CLIP embeddings for image and text understanding
- FAISS vector search for similarity matching
- LangChain framework for RAG operations

### [Frontend Interface](frontend.md)
Web-based user interface providing:
- Image upload and preview
- Recognition results display
- Interactive object browsing
- Responsive design for all devices

## Quick Start

### Base URL
```
http://localhost:8000  # Local development
https://yourdomain.com # Production
```

### Authentication
Currently, no authentication is required for basic operations.

### Rate Limiting
- Upload: 10 requests per minute
- Recognition: 20 requests per minute
- Search: 50 requests per minute

## Response Format

All API responses follow a consistent JSON format:

```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {
        // Response data here
    }
}
```

## Error Handling

Errors return appropriate HTTP status codes:

- `400 Bad Request`: Invalid input parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server-side errors

## Code Examples

### Python
```python
import requests

# Upload image
with open('metro_photo.jpg', 'rb') as f:
    files = {'file': f}
    data = {'station_name': 'Mayakovskaya'}
    response = requests.post('http://localhost:8000/upload', 
                           files=files, data=data)
    result = response.json()
```

### JavaScript
```javascript
// Upload image
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('station_name', 'Mayakovskaya');

fetch('/upload', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL
```bash
# Upload image
curl -X POST "http://localhost:8000/upload" \
     -F "file=@metro_photo.jpg" \
     -F "station_name=Mayakovskaya"
```

## Testing

### Interactive Documentation
- Visit `/docs` for Swagger UI
- Visit `/redoc` for ReDoc documentation

### Health Check
```bash
curl http://localhost:8000/health
```

## Support

- Check the [Getting Started](../getting-started/index.md) guide
- Review the [User Guide](../user-guide/index.md) for usage examples
- Open an issue on GitHub for bugs or feature requests

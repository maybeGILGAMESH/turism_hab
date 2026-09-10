# FastAPI Application

The main FastAPI application for the Moscow Metro Cultural Heritage Recognition System.

## Overview

This module provides a REST API for recognizing cultural heritage objects in Moscow Metro stations using AI-powered image analysis and RAG (Retrieval-Augmented Generation).

## Main Components

### FastAPI App Instance

```python
app = FastAPI(
    title="Moscow Metro Cultural Heritage Recognition System",
    description="AI-powered system for identifying cultural heritage objects in Moscow Metro stations",
    version="1.0.0"
)
```

## API Endpoints

### POST /upload
Upload an image for cultural heritage recognition.

**Parameters:**
- `file`: Image file (JPEG, PNG)
- `station_name`: Optional station name for context

**Response:**
```json
{
    "success": true,
    "message": "Image uploaded successfully",
    "filename": "uploaded_image.jpg",
    "station_name": "Mayakovskaya"
}
```

### POST /recognize
Recognize cultural heritage objects in an uploaded image.

**Parameters:**
- `filename`: Name of the uploaded image file
- `query`: Optional text query for RAG search

**Response:**
```json
{
    "success": true,
    "recognitions": [
        {
            "object_name": "Mosaic Panel",
            "description": "Artistic mosaic depicting...",
            "confidence": 0.95,
            "location": "Platform level"
        }
    ]
}
```

### GET /stations
Get list of available metro stations.

**Response:**
```json
{
    "stations": [
        "Mayakovskaya",
        "Ploshchad Revolyutsii",
        "Komsomolskaya"
    ]
}
```

### GET /objects
Get list of cultural heritage objects.

**Response:**
```json
{
    "objects": [
        {
            "id": "O0028",
            "name": "Mosaic Panel",
            "station": "Mayakovskaya",
            "description": "Artistic mosaic..."
        }
    ]
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request`: Invalid input parameters
- `404 Not Found`: File or resource not found
- `500 Internal Server Error`: Server-side processing error

## CORS Configuration

CORS middleware is enabled for cross-origin requests:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## File Upload Handling

- Supports JPEG and PNG image formats
- Images are stored in the `uploads/` directory
- Automatic file naming with timestamps
- Image validation and processing

## Dependencies

- FastAPI
- PIL (Pillow) for image processing
- Uvicorn for ASGI server
- CORS middleware for cross-origin requests

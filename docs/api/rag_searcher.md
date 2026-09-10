# RAG Searcher

RAG (Retrieval-Augmented Generation) searcher for Moscow Metro cultural heritage objects.

## Overview

This module provides functionality to search and retrieve information about cultural heritage objects in Moscow Metro stations using CLIP embeddings and FAISS vector search.

## Main Classes

### RAGSearcher

The main class for performing RAG-based searches on cultural heritage objects.

```python
class RAGSearcher:
    def __init__(self, artifacts_dir: str = "artifacts"):
        # Initialize with artifacts directory
```

## Key Methods

### `__init__(artifacts_dir: str)`
Initialize the RAG searcher with the specified artifacts directory.

**Parameters:**
- `artifacts_dir`: Path to directory containing FAISS index and metadata

### `load_artifacts()`
Load the pre-built FAISS index and metadata files.

**Returns:**
- `bool`: True if artifacts loaded successfully, False otherwise

### `search_by_image(image_path: str, top_k: int = 5)`
Search for cultural heritage objects using an image query.

**Parameters:**
- `image_path`: Path to the query image
- `top_k`: Number of top results to return

**Returns:**
- `List[Dict]`: List of matching objects with similarity scores

### `search_by_text(query: str, top_k: int = 5)`
Search for cultural heritage objects using a text query.

**Parameters:**
- `query`: Text query string
- `top_k`: Number of top results to return

**Returns:**
- `List[Dict]`: List of matching objects with similarity scores

### `get_object_info(object_id: str)`
Retrieve detailed information about a specific cultural heritage object.

**Parameters:**
- `object_id`: Unique identifier of the object

**Returns:**
- `Dict`: Object information including name, description, station, etc.

## Search Results Format

Each search result contains:

```python
{
    "id": "O0028",
    "name": "Mosaic Panel",
    "station": "Mayakovskaya",
    "description": "Artistic mosaic depicting...",
    "image_path": "data/images/O0028/O0028_000001.jpg",
    "similarity_score": 0.95,
    "metadata": {
        "artist": "Unknown",
        "year": "1938",
        "style": "Socialist Realism"
    }
}
```

## Supported Search Types

### Image-to-Image Search
- Uses CLIP image embeddings
- Compares query image with database images
- Returns most similar objects

### Text-to-Image Search
- Uses CLIP text embeddings
- Searches for objects matching text descriptions
- Supports natural language queries

### Hybrid Search
- Combines image and text queries
- Provides more accurate results
- Weighted scoring system

## Performance Features

- **FAISS Vector Index**: Fast similarity search
- **CLIP Embeddings**: State-of-the-art image-text understanding
- **Caching**: Pre-computed embeddings for quick retrieval
- **Batch Processing**: Efficient handling of multiple queries

## Dependencies

- `torch`: PyTorch for deep learning
- `clip`: OpenAI CLIP model
- `faiss`: Facebook AI Similarity Search
- `langchain`: LangChain framework
- `PIL`: Python Imaging Library
- `numpy`: Numerical computing

## Usage Example

```python
# Initialize searcher
searcher = RAGSearcher("artifacts")

# Load artifacts
if searcher.load_artifacts():
    # Search by image
    results = searcher.search_by_image("query_image.jpg", top_k=3)
    
    # Search by text
    text_results = searcher.search_by_text("mosaic panel", top_k=3)
    
    # Get object details
    object_info = searcher.get_object_info("O0028")
```

## Error Handling

The searcher handles various error conditions:

- Missing artifacts directory
- Corrupted index files
- Invalid image formats
- CLIP model loading failures
- FAISS index errors

## Configuration

Default settings can be modified:

- `artifacts_dir`: Path to artifacts (default: "artifacts")
- `top_k`: Default number of results (default: 5)
- `similarity_threshold`: Minimum similarity score (default: 0.1)

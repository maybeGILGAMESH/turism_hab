# Frontend Module

Web-based frontend interface for the Moscow Metro Cultural Heritage Recognition System.

## Overview

This module provides a user-friendly web interface for uploading images, viewing recognition results, and exploring cultural heritage objects in Moscow Metro stations.

## Main Components

### Web Interface

The frontend consists of HTML pages with JavaScript functionality for:

- Image upload and preview
- Recognition results display
- Station and object browsing
- Interactive search functionality

## Key Features

### Image Upload Interface

- Drag-and-drop file upload
- Image preview before submission
- Support for JPEG and PNG formats
- File size validation
- Station selection dropdown

### Recognition Results Display

- Visual presentation of recognized objects
- Confidence scores and descriptions
- Links to detailed object information
- Image comparison views

### Station Navigation

- List of all metro stations
- Station-specific object galleries
- Interactive station selection
- Location-based filtering

### Object Database Browser

- Complete catalog of cultural heritage objects
- Search and filter capabilities
- Detailed object information pages
- Image galleries for each object

## HTML Pages

### Main Page (`index.html`)
- Landing page with system overview
- Quick access to main features
- Navigation menu

### Admin Interface (`admin.html`)
- System administration panel
- Upload management
- Database statistics
- System configuration

## JavaScript Functionality

### File Upload Handling

```javascript
function handleFileUpload(file) {
    // Validate file type and size
    // Show preview
    // Submit to backend API
}
```

### API Communication

```javascript
async function uploadImage(file, stationName) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('station_name', stationName);
    
    const response = await fetch('/upload', {
        method: 'POST',
        body: formData
    });
    
    return response.json();
}
```

### Results Display

```javascript
function displayResults(results) {
    // Clear previous results
    // Create result cards
    // Show confidence scores
    // Display object images
}
```

## CSS Styling

### Responsive Design
- Mobile-first approach
- Adaptive layouts
- Touch-friendly interfaces

### Material Design
- Modern UI components
- Consistent color scheme
- Smooth animations
- Professional appearance

## User Experience Features

### Intuitive Navigation
- Clear menu structure
- Breadcrumb navigation
- Search functionality
- Quick access buttons

### Visual Feedback
- Loading indicators
- Success/error messages
- Progress bars
- Interactive elements

### Accessibility
- Keyboard navigation
- Screen reader support
- High contrast options
- Alt text for images

## Integration Points

### Backend API
- RESTful API endpoints
- JSON data exchange
- File upload handling
- Error response handling

### Database
- Object metadata
- Image storage
- Search indexing
- User preferences

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers
- Progressive Web App features
- Offline capability support

## Performance Optimizations

- Image compression
- Lazy loading
- Caching strategies
- Minimal dependencies

## Security Features

- File type validation
- Size limits
- CSRF protection
- Input sanitization

## Deployment

The frontend can be deployed as:

- Static files served by FastAPI
- Standalone web application
- Docker container
- GitHub Pages site

## Configuration

Frontend behavior can be customized through:

- Environment variables
- Configuration files
- API endpoint URLs
- Feature flags

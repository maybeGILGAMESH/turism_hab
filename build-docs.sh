#!/bin/bash

# Documentation Build and Serve Script
# Usage: ./build-docs.sh [serve|build]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if mkdocs is installed
check_mkdocs() {
    if ! command -v mkdocs &> /dev/null; then
        print_error "MkDocs is not installed. Installing now..."
        pip install mkdocs-material mkdocs-git-revision-date-localized-plugin mkdocs-git-authors-plugin mkdocs-minify-plugin
    fi
}

# Build documentation
build_docs() {
    print_status "Building documentation..."
    
    # Clean previous build
    if [ -d "site" ]; then
        rm -rf site
        print_status "Cleaned previous build"
    fi
    
    # Build documentation
    mkdocs build --strict
    
    if [ $? -eq 0 ]; then
        print_success "Documentation built successfully!"
        print_status "Output directory: ./site"
    else
        print_error "Documentation build failed!"
        exit 1
    fi
}

# Serve documentation locally
serve_docs() {
    print_status "Starting local documentation server..."
    print_status "Documentation will be available at: http://localhost:8000"
    print_status "Press Ctrl+C to stop the server"
    
    mkdocs serve --dev-addr=127.0.0.1:8000
}

# Main script logic
main() {
    print_status "🚇 Moscow Metro Cultural Heritage Recognition System - Documentation Builder"
    print_status "=================================================================="
    
    # Check dependencies
    check_mkdocs
    
    # Parse command line arguments
    case "${1:-serve}" in
        "build")
            build_docs
            ;;
        "serve")
            build_docs
            serve_docs
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  build   Build documentation only"
            echo "  serve   Build and serve documentation locally (default)"
            echo "  help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0          # Build and serve (default)"
            echo "  $0 build    # Build only"
            echo "  $0 serve    # Build and serve"
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

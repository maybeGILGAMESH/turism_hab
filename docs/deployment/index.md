# Deployment Guide

This guide explains how to deploy the Moscow Metro Cultural Heritage Recognition System documentation to GitHub Pages.

## GitHub Pages Setup

### 1. Enable GitHub Pages

1. Go to your repository settings
2. Navigate to "Pages" section
3. Select "GitHub Actions" as source
4. The workflow will automatically deploy on pushes to main branch

### 2. Automatic Deployment

The system uses GitHub Actions to automatically:
- Build documentation when you push to main
- Deploy to GitHub Pages
- Update the live site

### 3. Manual Deployment

To manually trigger deployment:

```bash
# Build locally
./build-docs.sh build

# Or use mkdocs directly
mkdocs build --strict

# Deploy manually (if needed)
mkdocs gh-deploy
```

## Local Development

### Build Documentation

```bash
# Install dependencies
pip install -r requirements-docs.txt

# Build docs
mkdocs build

# Serve locally
mkdocs serve
```

### Preview Changes

```bash
# Start local server
mkdocs serve --dev-addr=127.0.0.1:8000

# Open browser to http://localhost:8000
```

## Configuration

### Site Settings

The main configuration is in `mkdocs.yml`:

```yaml
site_name: Moscow Metro Cultural Heritage Recognition System
site_url: https://yourusername.github.io/yourrepo
repo_name: yourusername/yourrepo
```

### Theme Customization

The site uses Material for MkDocs theme with:

- Navigation tabs and sections
- Search functionality
- Code highlighting
- Responsive design

## Troubleshooting

### Common Issues

**Build fails:**
- Check Python version (3.8+ required)
- Verify all dependencies installed
- Check for syntax errors in markdown

**Deployment fails:**
- Ensure GitHub Pages is enabled
- Check repository permissions
- Verify workflow file is correct

**Site not updating:**
- Wait a few minutes for deployment
- Check Actions tab for build status
- Clear browser cache

### Getting Help

- Check GitHub Actions logs
- Review mkdocs documentation
- Open an issue for persistent problems

## Customization

### Adding Pages

1. Create markdown file in `docs/` directory
2. Add to navigation in `mkdocs.yml`
3. Commit and push to trigger deployment

### Styling

- Modify CSS in `docs/stylesheets/`
- Update theme settings in `mkdocs.yml`
- Customize Material theme options

### Content

- Use standard markdown syntax
- Include code examples with syntax highlighting
- Add images to `docs/images/` directory

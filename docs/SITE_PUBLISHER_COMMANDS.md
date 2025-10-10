# Site Publisher - Quick Command Reference

**Purpose**: Quick copy-paste commands for implementation  
**Date**: October 10, 2025

## Phase 1: Initial Setup

### Create Directory Structure
```bash
cd /workspaces/ai-content-farm

# Create main container directory
mkdir -p containers/site-publisher/{hugo-config,tests}

# Create test subdirectories
mkdir -p containers/site-publisher/tests/{unit,integration}

# Create Python files
touch containers/site-publisher/{__init__.py,app.py,config.py,models.py}
touch containers/site-publisher/{security.py,site_builder.py,deployment.py}
touch containers/site-publisher/{error_handling.py,logging_config.py}
touch containers/site-publisher/requirements.txt
touch containers/site-publisher/Dockerfile

# Create test files
touch containers/site-publisher/tests/{__init__.py,conftest.py}
touch containers/site-publisher/tests/unit/{test_security.py,test_site_builder.py}
touch containers/site-publisher/tests/integration/test_e2e.py

# Create Hugo config
touch containers/site-publisher/hugo-config/config.toml
```

### Install Hugo Locally (for testing)
```bash
# macOS
brew install hugo

# Linux (download binary)
HUGO_VERSION=0.138.0
wget https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_Linux-64bit.tar.gz
tar -xzf hugo_extended_${HUGO_VERSION}_Linux-64bit.tar.gz
sudo mv hugo /usr/local/bin/
hugo version
```

### Test Hugo Locally
```bash
cd /tmp

# Create test site
hugo new site test-site
cd test-site

# Clone PaperMod theme
git clone https://github.com/adityatelange/hugo-PaperMod themes/PaperMod

# Configure theme
echo 'theme = "PaperMod"' >> config.toml

# Create test content
mkdir -p content/posts
cat > content/posts/test-article.md << 'CONTENT'
---
title: "Test Article"
date: 2025-10-10T14:00:00Z
tags: ["test", "hugo"]
---

# Test Article

This is a test article to verify Hugo works correctly.
CONTENT

# Build site
hugo

# Verify output
ls -la public/

# Serve locally (optional)
# hugo server --bind 0.0.0.0
```

## Phase 2: Create requirements.txt

```bash
cat > containers/site-publisher/requirements.txt << 'EOF'
# FastAPI and web server
fastapi==0.115.0
uvicorn[standard]==0.31.0

# Pydantic for validation
pydantic==2.9.2
pydantic-settings==2.5.2

# Azure SDK
azure-storage-blob==12.23.1
azure-identity==1.18.0

# Logging and utilities
python-json-logger==2.0.7

# Shared libraries (from monorepo)
# Installed via Docker COPY

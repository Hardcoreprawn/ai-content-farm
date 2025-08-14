# Development Workflow Guide

## Container Implementation Checklist

Use this checklist when implementing the remaining containers (Content Ranker, Scheduler, SSG) to maintain consistency with the established architecture.

### 📋 Phase 1: Setup and Structure

#### Directory Structure
```bash
containers/<service-name>/
├── main.py              # FastAPI application entry point
├── <service>.py         # Core business logic module  
├── config.py           # Environment configuration management
├── requirements.txt    # Python dependencies
├── pyproject.toml     # pytest and tool configuration
├── __init__.py        # Python package initialization
└── tests/
    ├── __init__.py     # Test package initialization
    ├── test_main.py    # API endpoint tests
    └── test_<service>.py # Business logic unit tests
```

#### Essential Files Template

**`requirements.txt`**:
```
fastapi>=0.104.1
pydantic>=2.5.0
uvicorn>=0.24.0
requests>=2.31.0
pytest>=7.4.3
pytest-asyncio>=0.21.1
pytest-mock>=3.12.0
```

**`pyproject.toml`**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
```

### 📋 Phase 2: Configuration Management

#### `config.py` Template
```python
"""
<Service Name> Configuration

Environment-based configuration management.
"""

import os
from typing import Dict, Any, List


class Config:
    """Configuration settings for <service-name>."""
    
    # Service settings
    SERVICE_NAME: str = "<service-name>"
    PORT: int = int(os.getenv("PORT", "800X"))  # Use next available port
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # External API settings (if needed)
    API_KEY: str = os.getenv("API_KEY", "")
    API_URL: str = os.getenv("API_URL", "")
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "10"))
    
    # Service-specific settings
    MAX_ITEMS_PER_REQUEST: int = int(os.getenv("MAX_ITEMS_PER_REQUEST", "100"))
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return any issues."""
        issues = []
        
        if not cls.API_KEY:
            issues.append("API_KEY not set")
            
        return issues
    
    @classmethod
    def get_service_config(cls) -> Dict[str, Any]:
        """Get service configuration."""
        return {
            "service_name": cls.SERVICE_NAME,
            "port": cls.PORT,
            "debug": cls.DEBUG,
            "timeout": cls.REQUEST_TIMEOUT,
        }
```

### 📋 Phase 3: Core Business Logic

#### `<service>.py` Template Structure
```python
"""
<Service Name> Core Logic

Main business logic for <service-name> functionality.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def main_processing_function(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main processing function for <service-name>.
    
    Args:
        input_data: Input data for processing
        
    Returns:
        Processed results with metadata
    """
    start_time = time.time()
    
    try:
        # Main processing logic here
        results = process_data(input_data)
        
        # Create metadata
        metadata = {
            "total_processed": len(results),
            "processing_time_seconds": round(time.time() - start_time, 3),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "service_version": "1.0.0",
        }
        
        return {
            "results": results,
            "metadata": metadata
        }
        
    except Exception as e:
        raise RuntimeError(f"Processing failed: {str(e)}")


def process_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process individual data items.
    
    Args:
        data: Data to process
        
    Returns:
        List of processed items
    """
    # Implement core processing logic
    processed_items = []
    
    # Example processing
    for item in data.get("items", []):
        processed_item = {
            "id": item.get("id"),
            "processed_data": transform_item(item),
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        processed_items.append(processed_item)
    
    return processed_items


def transform_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Transform individual item."""
    # Implement item transformation logic
    return {
        "original": item,
        "enhanced": True,
        "transform_timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### 📋 Phase 4: FastAPI Application

#### `main.py` Template
```python
"""
<Service Name> API

FastAPI application for <service-name> functionality.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
import time
from datetime import datetime, timezone

from <service> import main_processing_function
from config import Config


app = FastAPI(
    title="<Service Name> API",
    description="API for <service-name> functionality",
    version="1.0.0"
)


# Request/Response Models
class ProcessingRequest(BaseModel):
    """Request model for processing."""
    items: List[Dict[str, Any]] = Field(..., description="Items to process")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing options")
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 items allowed per request')
        return v


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    config_issues: List[str] = Field(default_factory=list, description="Configuration issues")


class ProcessingResponse(BaseModel):
    """Processing response."""
    results: List[Dict[str, Any]] = Field(..., description="Processing results")
    metadata: Dict[str, Any] = Field(..., description="Processing metadata")
    processing_id: str = Field(..., description="Unique processing identifier")
    timestamp: str = Field(..., description="Processing timestamp")


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config_issues = Config.validate_config()
    
    return HealthResponse(
        status="healthy" if not config_issues else "warning",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        config_issues=config_issues
    )


@app.post("/process", response_model=ProcessingResponse)
async def process_items(request: ProcessingRequest):
    """Main processing endpoint."""
    try:
        # Process the request
        result = main_processing_function(request.dict())
        
        # Generate processing ID
        processing_id = f"proc_{int(time.time())}_{len(result['results'])}"
        
        return ProcessingResponse(
            results=result["results"],
            metadata=result["metadata"],
            processing_id=processing_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/status")
async def get_status():
    """Get service status and configuration."""
    return {
        "service": Config.SERVICE_NAME,
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": Config.get_service_config()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
```

### 📋 Phase 5: Test Implementation

#### Test Requirements
- **Minimum 30 tests per container** (follow established pattern)
- **Unit tests**: Core business logic functions
- **API tests**: All HTTP endpoints
- **Integration tests**: Cross-component functionality
- **Error handling tests**: Validation and exception scenarios

#### `test_<service>.py` Template
```python
"""
Unit tests for <service-name> core functionality.
"""

import pytest
from unittest.mock import Mock, patch
from <service> import main_processing_function, process_data, transform_item


class TestCoreProcessing:
    """Test core processing functionality."""

    @pytest.mark.unit
    def test_main_processing_function_success(self) -> None:
        """Test successful processing."""
        test_data = {
            "items": [
                {"id": "test1", "data": "sample"},
                {"id": "test2", "data": "sample2"}
            ]
        }

        result = main_processing_function(test_data)

        assert "results" in result
        assert "metadata" in result
        assert len(result["results"]) == 2
        assert result["metadata"]["total_processed"] == 2

    @pytest.mark.unit
    def test_process_data_empty_input(self) -> None:
        """Test processing with empty input."""
        result = process_data({"items": []})
        
        assert result == []

    @pytest.mark.unit
    def test_transform_item_basic(self) -> None:
        """Test basic item transformation."""
        test_item = {"id": "test", "value": 123}
        
        result = transform_item(test_item)
        
        assert "original" in result
        assert result["original"] == test_item
        assert result["enhanced"] is True

    @pytest.mark.unit
    def test_main_processing_function_error_handling(self) -> None:
        """Test error handling in main processing."""
        with patch('<service>.process_data', side_effect=Exception("Test error")):
            with pytest.raises(RuntimeError, match="Processing failed"):
                main_processing_function({"items": [{"id": "test"}]})


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.unit
    def test_large_dataset_processing(self) -> None:
        """Test processing large datasets."""
        large_dataset = {
            "items": [{"id": f"item_{i}", "data": f"data_{i}"} for i in range(50)]
        }
        
        result = main_processing_function(large_dataset)
        
        assert len(result["results"]) == 50
        assert result["metadata"]["total_processed"] == 50
```

#### `test_main.py` Template
```python
"""
API endpoint tests for <service-name>.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Test health check functionality."""

    @pytest.mark.unit
    def test_health_check_success(self) -> None:
        """Test successful health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestProcessingEndpoint:
    """Test main processing functionality."""

    @pytest.mark.unit
    def test_process_items_success(self) -> None:
        """Test successful item processing."""
        test_data = {
            "items": [
                {"id": "test1", "data": "sample"}
            ],
            "options": {}
        }

        response = client.post("/process", json=test_data)

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "metadata" in data
        assert "processing_id" in data

    @pytest.mark.unit
    def test_process_items_validation_error(self) -> None:
        """Test validation error handling."""
        test_data = {
            "items": [{"id": f"item_{i}"} for i in range(101)]  # Too many items
        }

        response = client.post("/process", json=test_data)

        assert response.status_code == 422

    @pytest.mark.unit
    @patch('<service>.main_processing_function')
    def test_process_items_internal_error(self, mock_process: Mock) -> None:
        """Test internal error handling."""
        mock_process.side_effect = Exception("Processing error")

        test_data = {"items": [{"id": "test"}]}

        response = client.post("/process", json=test_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestStatusEndpoint:
    """Test status endpoint functionality."""

    @pytest.mark.unit
    def test_status_endpoint(self) -> None:
        """Test status endpoint."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "status" in data
        assert data["status"] == "running"
```

### 📋 Phase 6: Testing and Validation

#### Test Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html

# Run specific test categories
python -m pytest tests/ -m unit -v
python -m pytest tests/ -k "test_health" -v
```

#### Quality Gates
- [ ] All tests passing (100%)
- [ ] Minimum 30 tests implemented
- [ ] All API endpoints tested
- [ ] Error handling validated
- [ ] Service starts without errors
- [ ] Health endpoint responds correctly

### 📋 Phase 7: Integration and Documentation

#### Service Integration
1. **Port Assignment**: Use next available port (8005, 8006, 8007)
2. **API Documentation**: FastAPI auto-generates at `/docs`
3. **Cross-service Communication**: Test with existing containers
4. **Configuration Validation**: Environment variables properly configured

#### Documentation Updates
1. Update `PROJECT_STATUS.md` with completion status
2. Create service-specific API documentation
3. Update architecture diagrams
4. Document any new dependencies or requirements

---

## Quick Start Commands

```bash
# Create new container structure
mkdir -p containers/<service-name>/tests
touch containers/<service-name>/{main.py,<service>.py,config.py,requirements.txt,pyproject.toml,__init__.py}
touch containers/<service-name>/tests/{__init__.py,test_main.py,test_<service>.py}

# Install dependencies
cd containers/<service-name>
pip install -r requirements.txt

# Run development server
python main.py

# Run tests
python -m pytest tests/ -v
```

Follow this workflow to maintain consistency with the established architecture and ensure high-quality implementation across all remaining containers.

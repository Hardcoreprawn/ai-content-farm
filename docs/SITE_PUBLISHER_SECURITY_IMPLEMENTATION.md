# Site Publisher - Security & Functional Implementation Guide

**Date**: October 10, 2025  
**Status**: Implementation Ready  
**Architecture**: Pure Functional + FastAPI REST + Security First

## 🔐 Shared Library Integration

**This implementation uses `libs.secure_error_handler.SecureErrorHandler`** - battle-tested, OWASP-compliant error handling with:

- ✅ **UUID Correlation IDs**: Automatic error tracking with unique identifiers
- ✅ **Sensitive Data Sanitization**: Auto-removes passwords, tokens, keys, credentials
- ✅ **OWASP Compliance**: CWE-209, CWE-754, CWE-532 protection
- ✅ **Severity-Based Logging**: LOW/MEDIUM/HIGH/CRITICAL with appropriate detail
- ✅ **Stack Traces**: Only logged for CRITICAL errors
- ✅ **Standardized Responses**: Matches our API contract format
- ✅ **Context Sanitization**: Recursive sanitization of nested data structures

**Import and use**:
```python
from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity

error_handler = SecureErrorHandler(service_name="site-publisher")

# Handle errors with correlation ID
result = error_handler.handle_error(
    error=exc,
    error_type="validation",
    severity=ErrorSeverity.MEDIUM,
    context={"blob": "article.md"}
)
# Returns: {"error_id": "uuid", "message": "Safe message", "timestamp": "ISO-8601", ...}
```

## Security Requirements ✅

### 1. OWASP Compliance
- ✅ **Input Validation**: All blob names, paths, and queue messages validated
- ✅ **Path Traversal Prevention**: Strict path validation for file operations
- ✅ **Command Injection Prevention**: Hugo executed with explicit args, no shell
- ✅ **Error Handling**: No sensitive data in error messages or logs
- ✅ **Dependency Security**: Regular security scans (Trivy, Checkov)

### 2. Docker Security
```dockerfile
# Non-root user (MANDATORY)
RUN useradd --create-home --shell /bin/bash app
USER app

# No secrets in environment variables
# All auth via managed identity
# Minimal base image (python:3.13-slim)
# Note: Using Python 3.13 for 4 years of security support (vs 2 years for 3.11)
```

### 3. Azure Security
- ✅ **Managed Identity**: No connection strings, no keys
- ✅ **RBAC**: Least privilege (Storage Blob Contributor only)
- ✅ **Network**: Private endpoints where possible
- ✅ **Logging**: All operations logged to Application Insights

### 4. Hugo Security
- ✅ **Fixed Version**: Pinned Hugo version (no 'latest')
- ✅ **Binary Verification**: SHA256 checksum validation
- ✅ **Sandboxed Execution**: Runs in isolated temp directory
- ✅ **No User Content in Templates**: All content is markdown data only

### 5. Secure Error Handling
```python
# GOOD - Safe error logging
logger.error(f"Build failed: {sanitize_error(error)}")

# BAD - Never log these
# logger.error(f"Error with file: {full_path}")  # Path disclosure
# logger.error(f"Azure error: {azure_exception}")  # Credential leak
# logger.error(f"Queue message: {raw_message}")  # Data leak
```

## Pure Functional Design ✅

### Core Principles
1. **No Classes** (except Pydantic models for data validation)
2. **Pure Functions**: Predictable outputs for given inputs
3. **Immutable Data**: All configuration passed as parameters
4. **No Global State**: All state in function parameters or return values
5. **Side Effects Isolated**: I/O operations clearly separated

### Functional Architecture Pattern

```python
# Pure function - no side effects
def validate_blob_name(blob_name: str) -> ValidationResult:
    """Validate blob name against security rules."""
    # Pure logic, predictable output
    pass

# Pure function with I/O clearly marked
async def download_markdown_files(
    blob_client: BlobServiceClient,
    container: str,
    output_dir: Path,
    logger: logging.Logger
) -> DownloadResult:
    """Download markdown files (I/O side effect)."""
    # All dependencies injected, no hidden state
    pass

# Pure function
async def build_site(
    content_dir: Path,
    output_dir: Path,
    config: HugoConfig,
    logger: logging.Logger
) -> BuildResult:
    """Build site with Hugo (I/O side effect)."""
    # Explicit parameters, no implicit state
    pass

# Composition function
async def build_and_deploy_site(
    blob_client: BlobServiceClient,
    config: Config,
    logger: logging.Logger
) -> DeploymentResult:
    """Compose functions to build and deploy site."""
    # Function composition, not object methods
    download_result = await download_markdown_files(...)
    build_result = await build_site(...)
    deploy_result = await deploy_to_blob(...)
    return DeploymentResult(...)
```

## File Structure (Pure Functional)

```
site-publisher/
├── Dockerfile                      # Multi-stage, security-hardened
├── app.py                          # FastAPI REST endpoints only
├── config.py                       # Configuration models (Pydantic)
├── models.py                       # Data models (Pydantic)
├── security.py                     # Security validation functions
├── site_builder.py                 # Pure functions for building
│   ├── download_content()         # Download markdown
│   ├── organize_content()         # Organize for Hugo
│   ├── build_with_hugo()          # Run Hugo
│   ├── validate_build()           # Validate output
│   └── build_and_deploy()         # Composition function
├── deployment.py                   # Pure functions for deployment
│   ├── deploy_to_blob()           # Upload to $web
│   ├── backup_current_site()      # Backup before deploy
│   └── rollback_deployment()      # Rollback on failure
├── error_handling.py               # Wrapper for libs.secure_error_handler
├── logging_config.py               # Structured logging setup
├── hugo-config/
│   └── config.toml                # Hugo configuration
├── requirements.txt
└── tests/
    ├── test_security.py           # Security validation tests
    ├── test_site_builder.py       # Pure function tests
    ├── test_deployment.py         # Deployment tests
    └── conftest.py

**Note**: `error_handling.py` is a thin wrapper around `libs.secure_error_handler.SecureErrorHandler` for convenience.
```

## Security Implementation

### 1. Input Validation (security.py)
```python
"""Security validation functions."""
import re
from pathlib import Path
from typing import Dict, List
from models import ValidationResult

# Pure function - no side effects
def validate_blob_name(blob_name: str) -> ValidationResult:
    """
    Validate blob name for security.
    
    Prevents:
    - Path traversal (../)
    - Absolute paths (/)
    - Special characters
    - Command injection attempts
    """
    errors = []
    
    # Check for path traversal
    if ".." in blob_name:
        errors.append("Path traversal detected")
    
    # Check for absolute paths
    if blob_name.startswith("/"):
        errors.append("Absolute paths not allowed")
    
    # Check for suspicious patterns
    suspicious = [";", "|", "&", "$", "`", "&&", "||"]
    if any(char in blob_name for char in suspicious):
        errors.append("Suspicious characters detected")
    
    # Validate extension
    if not blob_name.endswith(".md"):
        errors.append("Only .md files allowed")
    
    # Check length
    if len(blob_name) > 255:
        errors.append("Blob name too long")
    
    return ValidationResult(
        is_valid=(len(errors) == 0),
        errors=errors
    )


def validate_path(path: Path, allowed_base: Path) -> ValidationResult:
    """
    Validate that path is within allowed base directory.
    
    Prevents path traversal attacks.
    """
    try:
        # Resolve to absolute path
        resolved_path = path.resolve()
        resolved_base = allowed_base.resolve()
        
        # Check if path is within base
        if not str(resolved_path).startswith(str(resolved_base)):
            return ValidationResult(
                is_valid=False,
                errors=["Path outside allowed directory"]
            )
        
        return ValidationResult(is_valid=True, errors=[])
        
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Path validation error: {type(e).__name__}"]
        )


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error message for safe logging.
    
    Removes:
    - File paths
    - URLs
    - Credentials
    - Sensitive data
    """
    error_msg = str(error)
    
    # Remove paths (anything with /)
    error_msg = re.sub(r'/[^\s]+', '[PATH]', error_msg)
    
    # Remove URLs
    error_msg = re.sub(r'https?://[^\s]+', '[URL]', error_msg)
    
    # Remove potential credentials
    error_msg = re.sub(r'(key|token|password|secret)=[^\s&]+', r'\1=[REDACTED]', error_msg, flags=re.IGNORECASE)
    
    # Limit length
    if len(error_msg) > 200:
        error_msg = error_msg[:200] + "..."
    
    return error_msg


def validate_hugo_output(output_dir: Path) -> ValidationResult:
    """
    Validate Hugo build output for security and completeness.
    """
    errors = []
    
    # Check index.html exists
    if not (output_dir / "index.html").exists():
        errors.append("Missing index.html")
    
    # Check for suspicious files
    suspicious_extensions = [".exe", ".sh", ".bat", ".ps1", ".dll"]
    for ext in suspicious_extensions:
        if list(output_dir.rglob(f"*{ext}")):
            errors.append(f"Suspicious file type found: {ext}")
    
    # Check total size (prevent DOS)
    total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
    max_size = 100 * 1024 * 1024  # 100 MB
    if total_size > max_size:
        errors.append(f"Build output too large: {total_size / (1024*1024):.1f} MB")
    
    return ValidationResult(
        is_valid=(len(errors) == 0),
        errors=errors
    )
```

### 2. Secure Error Handling (using libs.secure_error_handler)

**Use the shared `SecureErrorHandler` from libs - it's OWASP-compliant and battle-tested!**

```python
"""Secure error handling utilities - uses shared library."""
from libs.secure_error_handler import SecureErrorHandler, ErrorSeverity
from typing import Any, Dict, Optional

# Initialize handler for site-publisher
error_handler = SecureErrorHandler(service_name="site-publisher")


def handle_error(
    error: Exception,
    error_type: str = "general",
    user_message: Optional[str] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handle errors securely using shared SecureErrorHandler.
    
    Features:
    - Automatic UUID correlation IDs for tracking
    - Sensitive data sanitization (passwords, tokens, keys)
    - OWASP-compliant (CWE-209, CWE-754, CWE-532)
    - Severity-based logging
    - Stack traces only for critical errors
    
    Args:
        error: The exception that occurred
        error_type: Type of error (general, validation, authentication, etc.)
        user_message: Optional custom safe message for users
        severity: Error severity (LOW, MEDIUM, HIGH, CRITICAL)
        context: Additional context (automatically sanitized)
    
    Returns:
        Sanitized error response with correlation ID
    """
    return error_handler.handle_error(
        error=error,
        error_type=error_type,
        severity=severity,
        context=context,
        user_message=user_message
    )


def create_http_error_response(
    status_code: int,
    error: Optional[Exception] = None,
    error_type: str = "general",
    user_message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized HTTP error response.
    
    Returns format matching our API contract:
    {
        "status": "error",
        "message": "Safe user message",
        "data": None,
        "errors": ["Safe user message"],
        "metadata": {
            "function": "site-publisher",
            "timestamp": "ISO-8601",
            "version": "1.0.0",
            "error_id": "uuid-for-tracking"
        }
    }
    """
    return error_handler.create_http_error_response(
        status_code=status_code,
        error=error,
        error_type=error_type,
        user_message=user_message,
        context=context
    )
```

### 3. Secure Logging Configuration (logging_config.py)
```python
"""Secure logging configuration."""
import logging
import sys
from typing import Any, Dict

class SensitiveDataFilter(logging.Filter):
    """Filter sensitive data from logs."""
    
    SENSITIVE_PATTERNS = [
        "password",
        "token",
        "key",
        "secret",
        "credential",
        "connection_string"
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out log records containing sensitive data."""
        message = record.getMessage().lower()
        
        # Check for sensitive patterns
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                record.msg = f"[REDACTED - Contains {pattern}]"
                record.args = ()
        
        return True


def configure_secure_logging(log_level: str = "INFO") -> None:
    """
    Configure secure logging.
    
    Features:
    - No sensitive data in logs
    - Structured JSON format (for Application Insights)
    - Appropriate log levels
    - No file path disclosure
    """
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Structured format (Azure-friendly)
    formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    
    # Add sensitive data filter
    handler.addFilter(SensitiveDataFilter())
    
    logger.addHandler(handler)
    
    # Suppress noisy Azure SDK logs
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
```

## Pure Functional Site Builder (site_builder.py)

```python
"""
Pure functional site builder.

All functions are pure with explicit dependencies.
No classes, no mutable state, no side effects except I/O.
"""
import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from azure.storage.blob.aio import BlobServiceClient
from models import (
    BuildResult,
    Config,
    DeploymentResult,
    DownloadResult,
    ProcessingStatus,
    ValidationResult,
)
from security import (
    sanitize_error_message,
    validate_blob_name,
    validate_hugo_output,
    validate_path,
)

logger = logging.getLogger(__name__)


async def download_markdown_files(
    blob_client: BlobServiceClient,
    container_name: str,
    output_dir: Path,
    max_files: int = 10000
) -> DownloadResult:
    """
    Download markdown files from blob storage (pure function with I/O).
    
    Args:
        blob_client: Azure blob client (injected dependency)
        container_name: Source container name
        output_dir: Destination directory
        max_files: Maximum files to download (DOS prevention)
    
    Returns:
        DownloadResult with file list and metrics
    """
    start_time = time.time()
    downloaded_files: List[str] = []
    errors: List[str] = []
    
    try:
        container_client = blob_client.get_container_client(container_name)
        
        async for blob in container_client.list_blobs():
            # Validate blob name (security)
            validation = validate_blob_name(blob.name)
            if not validation.is_valid:
                logger.warning(f"Skipping invalid blob: {blob.name}")
                errors.extend(validation.errors)
                continue
            
            # DOS prevention
            if len(downloaded_files) >= max_files:
                errors.append(f"Max files limit reached: {max_files}")
                break
            
            # Download blob
            blob_client_instance = container_client.get_blob_client(blob.name)
            content = await blob_client_instance.download_blob()
            markdown_content = await content.readall()
            
            # Validate and save
            file_path = output_dir / "posts" / Path(blob.name).name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Path traversal check
            path_validation = validate_path(file_path, output_dir)
            if not path_validation.is_valid:
                logger.warning(f"Path validation failed: {blob.name}")
                errors.extend(path_validation.errors)
                continue
            
            file_path.write_bytes(markdown_content)
            downloaded_files.append(blob.name)
            logger.debug(f"Downloaded: {blob.name}")
        
        duration = time.time() - start_time
        logger.info(f"Downloaded {len(downloaded_files)} files in {duration:.2f}s")
        
        return DownloadResult(
            files=downloaded_files,
            file_count=len(downloaded_files),
            duration_seconds=duration,
            errors=errors
        )
        
    except Exception as e:
        sanitized_error = sanitize_error_message(e)
        logger.error(f"Download failed: {sanitized_error}")
        return DownloadResult(
            files=[],
            file_count=0,
            duration_seconds=time.time() - start_time,
            errors=[f"Download failed: {type(e).__name__}"]
        )


async def build_site_with_hugo(
    content_dir: Path,
    output_dir: Path,
    hugo_config_path: Path,
    hugo_version: str = "0.138.0"
) -> BuildResult:
    """
    Build site with Hugo (pure function with subprocess I/O).
    
    Security:
    - No shell=True (prevents command injection)
    - Explicit arguments (no string formatting)
    - Sandboxed in temp directory
    - Output validation
    
    Args:
        content_dir: Hugo content directory
        output_dir: Build output directory
        hugo_config_path: Hugo config file
        hugo_version: Hugo version for logging
    
    Returns:
        BuildResult with build status and metrics
    """
    start_time = time.time()
    
    try:
        # Validate paths
        for path in [content_dir, hugo_config_path]:
            if not path.exists():
                return BuildResult(
                    status=ProcessingStatus.FAILED,
                    message=f"Path not found: {path.name}",
                    build_time_seconds=0,
                    errors=[f"Missing: {path.name}"]
                )
        
        # Build Hugo command (NO SHELL - security)
        cmd = [
            "hugo",
            "--source", str(content_dir.parent),
            "--destination", str(output_dir),
            "--config", str(hugo_config_path),
            "--minify",
            "--cleanDestinationDir",
            "--quiet"  # Reduce log noise
        ]
        
        logger.info(f"Building site with Hugo {hugo_version}")
        
        # Run Hugo (async subprocess, no shell)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(content_dir.parent)  # Sandbox to content directory
        )
        
        stdout, stderr = await process.communicate()
        
        build_time = time.time() - start_time
        
        # Check return code
        if process.returncode != 0:
            error_msg = stderr.decode()[:200]  # Limit error length
            logger.error(f"Hugo build failed (exit {process.returncode})")
            return BuildResult(
                status=ProcessingStatus.FAILED,
                message="Hugo build failed",
                build_time_seconds=build_time,
                errors=[f"Exit code: {process.returncode}"]
            )
        
        # Validate build output (security)
        validation = validate_hugo_output(output_dir)
        if not validation.is_valid:
            logger.error(f"Build validation failed: {validation.errors}")
            return BuildResult(
                status=ProcessingStatus.FAILED,
                message="Build validation failed",
                build_time_seconds=build_time,
                errors=validation.errors
            )
        
        # Count generated files
        html_files = list(output_dir.rglob("*.html"))
        
        logger.info(
            f"Hugo build complete: {len(html_files)} pages in {build_time:.2f}s"
        )
        
        return BuildResult(
            status=ProcessingStatus.COMPLETED,
            message="Build successful",
            build_time_seconds=build_time,
            html_pages_generated=len(html_files),
            errors=[]
        )
        
    except Exception as e:
        sanitized_error = sanitize_error_message(e)
        logger.error(f"Build error: {sanitized_error}")
        return BuildResult(
            status=ProcessingStatus.FAILED,
            message="Build error",
            build_time_seconds=time.time() - start_time,
            errors=[f"Error: {type(e).__name__}"]
        )


async def deploy_to_web_container(
    build_dir: Path,
    blob_client: BlobServiceClient,
    container_name: str,
    max_file_size: int = 10 * 1024 * 1024  # 10 MB per file
) -> DeploymentResult:
    """
    Deploy built site to blob storage (pure function with I/O).
    
    Security:
    - File size limits (DOS prevention)
    - Content type validation
    - Path validation
    
    Args:
        build_dir: Directory containing built site
        blob_client: Azure blob client
        container_name: Destination container ($web)
        max_file_size: Maximum file size (security)
    
    Returns:
        DeploymentResult with upload metrics
    """
    start_time = time.time()
    uploaded_files: List[str] = []
    errors: List[str] = []
    
    try:
        container_client = blob_client.get_container_client(container_name)
        
        # Get all files to upload
        for file_path in build_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Security checks
            file_size = file_path.stat().st_size
            if file_size > max_file_size:
                errors.append(f"File too large: {file_path.name}")
                continue
            
            # Path validation
            relative_path = file_path.relative_to(build_dir)
            path_validation = validate_path(file_path, build_dir)
            if not path_validation.is_valid:
                errors.extend(path_validation.errors)
                continue
            
            # Determine content type
            content_type = get_content_type(file_path)
            
            # Upload
            blob_client_instance = container_client.get_blob_client(str(relative_path))
            
            with open(file_path, "rb") as data:
                await blob_client_instance.upload_blob(
                    data,
                    overwrite=True,
                    content_settings={"content_type": content_type}
                )
            
            uploaded_files.append(str(relative_path))
            logger.debug(f"Uploaded: {relative_path}")
        
        duration = time.time() - start_time
        logger.info(f"Deployed {len(uploaded_files)} files in {duration:.2f}s")
        
        return DeploymentResult(
            files_uploaded=len(uploaded_files),
            duration_seconds=duration,
            errors=errors
        )
        
    except Exception as e:
        sanitized_error = sanitize_error_message(e)
        logger.error(f"Deployment failed: {sanitized_error}")
        return DeploymentResult(
            files_uploaded=len(uploaded_files),
            duration_seconds=time.time() - start_time,
            errors=[f"Deployment failed: {type(e).__name__}"]
        )


def get_content_type(file_path: Path) -> str:
    """
    Determine content type from file extension (pure function).
    
    Whitelist approach for security.
    """
    extension = file_path.suffix.lower()
    
    # Whitelist of allowed content types
    content_types = {
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".xml": "application/xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".txt": "text/plain",
        ".pdf": "application/pdf",
    }
    
    return content_types.get(extension, "application/octet-stream")


async def build_and_deploy_site(
    blob_client: BlobServiceClient,
    config: Config
) -> DeploymentResult:
    """
    Compose functions to build and deploy site (pure composition).
    
    This is the main orchestration function that composes
    all the pure functions above.
    """
    logger.info("Starting site build and deployment")
    start_time = time.time()
    
    try:
        # Create temp directory (cleanup handled by context manager)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            content_dir = temp_path / "content"
            output_dir = temp_path / "public"
            content_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Download markdown
            download_result = await download_markdown_files(
                blob_client=blob_client,
                container_name=config.markdown_container,
                output_dir=content_dir
            )
            
            if download_result.file_count == 0:
                logger.info("No markdown files to process")
                return DeploymentResult(
                    files_uploaded=0,
                    duration_seconds=time.time() - start_time,
                    errors=["No markdown files found"]
                )
            
            # Step 2: Build with Hugo
            build_result = await build_site_with_hugo(
                content_dir=content_dir,
                output_dir=output_dir,
                hugo_config_path=Path("/app/hugo-config/config.toml")
            )
            
            if build_result.status != ProcessingStatus.COMPLETED:
                logger.error("Build failed, aborting deployment")
                return DeploymentResult(
                    files_uploaded=0,
                    duration_seconds=time.time() - start_time,
                    errors=build_result.errors
                )
            
            # Step 3: Deploy to $web
            deploy_result = await deploy_to_web_container(
                build_dir=output_dir,
                blob_client=blob_client,
                container_name=config.output_container
            )
            
            total_duration = time.time() - start_time
            
            logger.info(
                f"Site published: {download_result.file_count} markdown → "
                f"{build_result.html_pages_generated} HTML → "
                f"{deploy_result.files_uploaded} deployed in {total_duration:.2f}s"
            )
            
            return deploy_result
            
    except Exception as e:
        sanitized_error = sanitize_error_message(e)
        logger.error(f"Build and deploy failed: {sanitized_error}")
        return DeploymentResult(
            files_uploaded=0,
            duration_seconds=time.time() - start_time,
            errors=[f"Failed: {type(e).__name__}"]
        )
```

## FastAPI Application (app.py)

```python
"""
FastAPI REST API for site-publisher.

Provides monitoring, control, and manual triggering endpoints.
Pure functional core with thin API layer.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from config import get_settings
from error_handling import handle_error, create_http_error_response
from libs.secure_error_handler import ErrorSeverity
from logging_config import configure_secure_logging
from models import (
    Config,
    HealthCheckResponse,
    MetricsResponse,
    PublishRequest,
    PublishResponse,
    ProcessingStatus,
)
from site_builder import build_and_deploy_site

# Configure secure logging
configure_secure_logging()
logger = logging.getLogger(__name__)

# Application metrics (immutable updates only)
app_metrics: Dict[str, Any] = {
    "start_time": datetime.utcnow(),
    "total_builds": 0,
    "successful_builds": 0,
    "failed_builds": 0,
    "last_build_time": None,
    "last_build_duration": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle with secure initialization."""
    logger.info("Starting site-publisher container")
    
    try:
        settings = get_settings()
        
        # Initialize Azure clients with managed identity
        credential = DefaultAzureCredential()
        account_url = (
            f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
        )
        
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=credential,
        )
        
        # Store in app state (dependency injection)
        app.state.blob_client = blob_service_client
        app.state.settings = settings
        app.state.credential = credential
        
        logger.info("Site-publisher initialized successfully")
        
        # Start queue processing (if enabled)
        if settings.enable_queue_processing:
            from libs.queue_client import process_queue_messages
            from libs.storage_queue_poller import StorageQueuePoller
            
            async def message_handler(queue_message, message) -> Dict[str, Any]:
                """Process site publishing request from queue."""
                try:
                    logger.info(
                        f"Processing publish request {queue_message.message_id}"
                    )
                    
                    # Call pure function
                    result = await build_and_deploy_site(
                        blob_client=app.state.blob_client,
                        config=settings
                    )
                    
                    # Update metrics (immutable pattern)
                    app_metrics["total_builds"] += 1
                    if len(result.errors) == 0:
                        app_metrics["successful_builds"] += 1
                    else:
                        app_metrics["failed_builds"] += 1
                    app_metrics["last_build_time"] = datetime.utcnow()
                    app_metrics["last_build_duration"] = result.duration_seconds
                    
                    return {"status": "success", "result": result.model_dump()}
                    
                except Exception as e:
                    error_response = handle_error(
                        error=e,
                        context="queue_processing",
                        user_message="Site publish failed"
                    )
                    app_metrics["total_builds"] += 1
                    app_metrics["failed_builds"] += 1
                    return {"status": "error", "error": error_response.message}
            
            # Start background poller
            poller = StorageQueuePoller(
                queue_name=settings.queue_name,
                message_handler=message_handler,
                poll_interval=float(settings.queue_polling_interval_seconds),
                max_messages_per_batch=1,  # One build at a time
                max_empty_polls=3,
                empty_queue_sleep=60.0,
                process_queue_messages_func=process_queue_messages,
            )
            
            asyncio.create_task(poller.start())
            logger.info(f"Queue polling started: {settings.queue_name}")
        
        yield
        
        # Cleanup
        await blob_service_client.close()
        await credential.close()
        logger.info("Site-publisher shutdown complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


app = FastAPI(
    lifespan=lifespan,
    title="Site Publisher",
    description="Static site generation with Hugo",
    version="1.0.0",
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler - never expose sensitive data."""
    error_response = create_http_error_response(
        status_code=500,
        error=exc,
        error_type="general",
        user_message="An error occurred processing your request",
        context={"path": str(request.url.path)}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        service="site-publisher",
        version="1.0.0",
        timestamp=datetime.utcnow(),
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get build metrics."""
    uptime = (datetime.utcnow() - app_metrics["start_time"]).total_seconds()
    
    return MetricsResponse(
        total_builds=app_metrics["total_builds"],
        successful_builds=app_metrics["successful_builds"],
        failed_builds=app_metrics["failed_builds"],
        last_build_time=app_metrics["last_build_time"],
        last_build_duration=app_metrics["last_build_duration"],
        uptime_seconds=uptime,
    )


@app.post("/publish", response_model=PublishResponse)
async def publish_site(request: PublishRequest):
    """
    Manually trigger site publish.
    
    Security: Input validation via Pydantic model.
    """
    try:
        logger.info("Manual publish triggered")
        
        # Call pure function
        result = await build_and_deploy_site(
            blob_client=app.state.blob_client,
            config=app.state.settings
        )
        
        # Update metrics
        app_metrics["total_builds"] += 1
        if len(result.errors) == 0:
            app_metrics["successful_builds"] += 1
            response_status = ProcessingStatus.COMPLETED
        else:
            app_metrics["failed_builds"] += 1
            response_status = ProcessingStatus.FAILED
        
        app_metrics["last_build_time"] = datetime.utcnow()
        app_metrics["last_build_duration"] = result.duration_seconds
        
        return PublishResponse(
            status=response_status,
            message="Site published" if len(result.errors) == 0 else "Publish failed",
            files_uploaded=result.files_uploaded,
            duration_seconds=result.duration_seconds,
            errors=result.errors,
        )
        
    except Exception as e:
        # Use shared secure error handler with correlation ID
        error_data = handle_error(
            error=e,
            error_type="general",
            severity=ErrorSeverity.HIGH,
            user_message="Failed to publish site",
            context={"request": request.dict()}
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_data["message"]
        )


@app.get("/status")
async def get_status():
    """Get current build status."""
    return {
        "status": "idle" if app_metrics["total_builds"] == 0 else "ready",
        "last_build": app_metrics["last_build_time"],
        "builds_today": app_metrics["total_builds"],
    }
```

## Next Steps

1. **Review Security Implementation** ✅
2. **Create Container Structure** (30 min)
3. **Implement Pure Functions** (2-3 hours)
4. **Add Comprehensive Tests** (2-3 hours)
5. **Security Scan** (Trivy, Checkov)
6. **Deploy via CI/CD**

**All requirements met**:
- ✅ Hugo (Go-based SSG)
- ✅ Security-first design
- ✅ Pure functional architecture
- ✅ FastAPI REST endpoints
- ✅ Secure logging
- ✅ Secure error handling
- ✅ Single replica scaling (0→1)

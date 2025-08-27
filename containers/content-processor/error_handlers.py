#!/usr/bin/env python3
"""
Content Processor - Exception Handlers

Global exception handlers for the content processor service.
"""

import json
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from libs.shared_models import ErrorCodes

logger = logging.getLogger(__name__)


async def value_error_handler(request: Request, exc: ValueError):
    """Handle JSON parsing errors"""
    logger.error(f"Value error (likely JSON parsing): {exc}")
    response = ErrorCodes.secure_validation_error(
        field="request body", safe_message="Invalid format"
    )
    return JSONResponse(status_code=400, content=response.model_dump())


async def json_error_handler(request: Request, exc: json.JSONDecodeError):
    """Handle JSON decode errors"""
    logger.error(f"JSON decode error: {exc}")
    response = ErrorCodes.secure_validation_error(
        field="request body", safe_message="Malformed JSON"
    )
    return JSONResponse(status_code=400, content=response.model_dump())


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.error(f"Validation error: {exc}")
    response = ErrorCodes.secure_validation_error(
        field="request", safe_message="Validation failed"
    )
    return JSONResponse(status_code=422, content=response.model_dump())


async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Global exception: {exc}")
    response = ErrorCodes.secure_internal_error(
        actual_error=exc, log_context="content-processor API"
    )
    return JSONResponse(status_code=500, content=response.model_dump())

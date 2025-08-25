#!/usr/bin/env python3
"""
Test configuration setup - Run before any test imports.

Sets up environment variables required for main.py import.
"""

import os

# Set required environment variables for tests
if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=dGVzdA==;EndpointSuffix=core.windows.net"

if not os.getenv("ENVIRONMENT"):
    os.environ["ENVIRONMENT"] = "testing"

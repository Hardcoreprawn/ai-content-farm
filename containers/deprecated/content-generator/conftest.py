"""
Container-level conftest.py for content-generator.

Sets up path configuration for tests.
"""

import os
import sys
from pathlib import Path

# Ensure this container directory is first on sys.path so tests importing
# top-level modules resolve to the local files.
root = Path(__file__).parent
sys.path.insert(0, str(root))

# Also add repo root so shared `libs` package is importable during tests
repo_root = root.parent.parent
sys.path.insert(0, str(repo_root))

# Set up environment for testing
os.environ["ENVIRONMENT"] = "local"
os.environ["BLOB_STORAGE_MOCK"] = "true"

# Set up Azurite connection for testing
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"  # pragma: allowlist secret
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)

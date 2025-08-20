import os
import sys

import pytest

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables for testing
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["CLAUDE_API_KEY"] = "test-claude-key"
os.environ["BLOB_CONNECTION_STRING"] = "UseDevelopmentStorage=true"

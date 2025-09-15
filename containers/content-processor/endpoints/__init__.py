"""
Content Processor Endpoints Package

Contains all FastAPI router endpoints for the content processor service.
"""

# Import the main router from the parent endpoints.py module
import sys
from pathlib import Path

# Add the parent directory to path to import from endpoints.py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import main router from endpoints.py
try:
    import endpoints as endpoints_module

    router = endpoints_module.router
except ImportError:
    router = None

# Import Service Bus router
try:
    from .servicebus_router import router as servicebus_router
except ImportError:
    servicebus_router = None

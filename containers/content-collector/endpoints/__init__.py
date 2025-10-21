"""
Content Womble Endpoints Package

Modular endpoint organization following REST best practices.
Storage Queue integration replaces Service Bus for Container Apps compatibility.
"""

# OLD ENDPOINTS - TEMPORARILY DISABLED during streaming architecture refactoring
# These depend on old batch collection code (service_logic.py, content_processing_simple.py)
# which has been replaced by Phase 1-3 streaming architecture
# from .collections import router as collections_router
# from .discoveries import router as discoveries_router
# from .reprocess import router as reprocess_router
# from .storage_queue_router import router as storage_queue_router
# from .templates import router as templates_router

# TEMPORARILY DISABLED during collector architecture refactoring
# from .diagnostics import router as diagnostics_router
# from .sources import router as sources_router

__all__ = [
    # "collections_router",
    # "discoveries_router",
    # "storage_queue_router",
    # "templates_router",
    # "reprocess_router",
    # "sources_router",  # Disabled during refactoring
    # "diagnostics_router",  # Disabled during refactoring
]

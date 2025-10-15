#!/usr/bin/env python3
"""
Test script to verify imports work correctly in monorepo context.

Tests:
1. Imports from container directory (added to sys.path by conftest.py)
2. Imports from shared libs/ directory
3. Cross-module imports within container
"""

import sys
from pathlib import Path

# Simulate pytest environment setup
project_root = Path(__file__).parent.parent.parent
container_dir = Path(__file__).parent

# Add to sys.path like conftest.py does
sys.path.insert(0, str(container_dir))
sys.path.insert(0, str(project_root))

print("=" * 70)
print("MONOREPO IMPORT TEST")
print("=" * 70)
print(f"Project root: {project_root}")
print(f"Container dir: {container_dir}")
print(f"sys.path[0:3]: {sys.path[0:3]}")
print()

# Test 1: Import shared libs
print("✓ Test 1: Importing shared libs...")
try:
    from libs.blob_storage import BlobStorageClient

    print("  libs.blob_storage.BlobStorageClient")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

try:
    from libs.queue_client import StorageQueueClient

    print("  libs.queue_client.StorageQueueClient")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

# Test 2: Import container modules (absolute imports)
print("\n✓ Test 2: Importing container modules...")
try:
    from models import ProcessorStatus, TopicMetadata

    print("  models.TopicMetadata, ProcessorStatus")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

try:
    from processor_context import ProcessorContext

    print("  processor_context.ProcessorContext")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

# Test 3: Import split queue modules
print("\n✓ Test 3: Importing split queue modules...")
try:
    from queue_message_builder import create_queue_message, generate_correlation_id

    print("  queue_message_builder.create_queue_message")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

try:
    from queue_client_operations import send_queue_message, trigger_markdown_for_article

    print("  queue_client_operations.send_queue_message")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

# Test 4: Import backward-compatible queue_operations
print("\n✓ Test 4: Importing backward-compatible queue_operations...")
try:
    from queue_operations import create_queue_message as cqm
    from queue_operations import send_queue_message as sqm
    from queue_operations import trigger_markdown_for_article as tmfa

    print("  queue_operations re-exports work correctly")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

# Test 5: Import processor operations
print("\n✓ Test 5: Importing processor operations...")
try:
    from processor_operations import check_processor_health, process_collection_file

    print("  processor_operations.process_collection_file")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

try:
    from processing_operations import process_topic_to_article

    print("  processing_operations.process_topic_to_article")
except ImportError as e:
    print(f"  Failed: {e}")
    sys.exit(1)

# Test 6: Verify functions are callable
print("\n✓ Test 6: Verifying functions are callable...")
try:
    corr_id = generate_correlation_id("test-service")
    assert "test-service_" in corr_id
    print(f"  generate_correlation_id() works: {corr_id[:30]}...")
except Exception as e:
    print(f"  Failed: {e}")
    sys.exit(1)

try:
    msg = create_queue_message("test", "wake_up", {"data": "test"})
    assert msg["service_name"] == "test"
    assert msg["operation"] == "wake_up"
    print("  create_queue_message() works")
except Exception as e:
    print(f"  Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("ALL IMPORT TESTS PASSED!")
print("=" * 70)
print("\nConclusion:")
print("  • Absolute imports work correctly in monorepo")
print("  • Container modules import successfully")
print("  • Shared libs/ modules accessible")
print("  • Split queue_operations modules work")
print("  • Backward compatibility maintained")
print("  • Functions are callable and work as expected")

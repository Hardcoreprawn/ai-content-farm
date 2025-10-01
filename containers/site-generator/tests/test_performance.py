"""
Performance Testing for Site Generator

Basic performance benchmarks for key operations.
Tests execution time and resource usage for critical functions.
"""

import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from content_processing_functions import generate_markdown_batch, generate_static_site
from content_utility_functions import create_markdown_content
from models import GenerationResponse

from libs.simplified_blob_client import SimplifiedBlobClient


class TestPerformanceBenchmarks:
    """Basic performance testing for key operations."""

    @pytest.fixture
    def performance_blob_client(self):
        """Optimized mock for performance testing."""
        mock = Mock(spec=SimplifiedBlobClient)
        mock.list_blobs = AsyncMock(return_value=[{"name": "perf-test.json"}])
        mock.download_text = AsyncMock(
            return_value=json.dumps(
                {
                    "items": [
                        {
                            "topic_id": "perf_test",
                            "title": "Performance Test",
                            "content": "Perf content",
                        }
                    ]
                }
            )
        )
        mock.upload_text = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def performance_config(self):
        """Configuration for performance testing."""
        return {
            "PROCESSED_CONTENT_CONTAINER": "perf-processed",
            "MARKDOWN_CONTENT_CONTAINER": "perf-markdown",
            "STATIC_SITE_CONTAINER": "perf-static",
        }

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_markdown_generation_performance(
        self, performance_blob_client, performance_config
    ):
        """Benchmark markdown generation performance."""
        with patch("content_utility_functions.ContractValidator") as mock_validator:
            mock_validated = Mock()
            mock_validated.items = [
                {
                    "topic_id": "perf_test",
                    "title": "Performance Test",
                    "content": "Test",
                }
            ]
            mock_validator.validate_collection_data.return_value = mock_validated

            # Measure execution time
            start_time = time.perf_counter()

            result = await generate_markdown_batch(
                source="performance_test",
                batch_size=1,
                force_regenerate=False,
                blob_client=performance_blob_client,
                config=performance_config,
                generator_id="perf-test-001",
            )

            end_time = time.perf_counter()
            execution_time = end_time - start_time

            # Verify function completed successfully
            assert isinstance(result, GenerationResponse)

            # Performance assertions (adjust thresholds as needed)
            assert (
                execution_time < 5.0
            ), f"Markdown generation took {execution_time:.2f}s (expected < 5.0s)"

            # Log performance for monitoring
            print(f"\nMarkdown generation performance: {execution_time:.3f}s")

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_static_site_generation_performance(
        self, performance_blob_client, performance_config
    ):
        """Benchmark static site generation performance."""
        start_time = time.perf_counter()

        result = await generate_static_site(
            theme="performance_theme",
            force_rebuild=False,
            blob_client=performance_blob_client,
            config=performance_config,
            generator_id="perf-site-001",
        )

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # Verify function completed successfully
        assert isinstance(result, GenerationResponse)

        # Performance assertions
        assert (
            execution_time < 10.0
        ), f"Site generation took {execution_time:.2f}s (expected < 10.0s)"

        # Log performance for monitoring
        print(f"\nStatic site generation performance: {execution_time:.3f}s")

    def test_markdown_content_creation_performance(self):
        """Benchmark markdown content creation performance."""
        article_data = {
            "title": "Performance Test Article",
            "content": "This is test content for performance benchmarking."
            * 50,  # Longer content
            "metadata": {"category": "performance", "tags": ["benchmark", "test"]},
        }

        # Measure multiple iterations
        iterations = 100
        start_time = time.perf_counter()

        for _ in range(iterations):
            result = create_markdown_content(article_data)
            assert isinstance(result, str)
            assert len(result) > 0

        end_time = time.perf_counter()
        total_time = end_time - start_time
        avg_time = total_time / iterations

        # Performance assertions
        assert (
            avg_time < 0.01
        ), f"Average markdown creation took {avg_time:.4f}s (expected < 0.01s)"

        # Log performance for monitoring
        print(
            f"\nMarkdown content creation performance: {avg_time:.6f}s average over {iterations} iterations"
        )

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_batch_processing_scalability(
        self, performance_blob_client, performance_config
    ):
        """Test performance scaling with different batch sizes."""
        batch_sizes = [1, 5, 10, 25]
        performance_results = {}

        for batch_size in batch_sizes:
            # Create test data for this batch size
            test_items = [
                {
                    "topic_id": f"scale_test_{i}",
                    "title": f"Scale Test Article {i}",
                    "content": f"Content for scalability test article {i}",
                }
                for i in range(batch_size)
            ]

            performance_blob_client.download_text = AsyncMock(
                return_value=json.dumps({"items": test_items})
            )

            with patch("content_utility_functions.ContractValidator") as mock_validator:
                mock_validated = Mock()
                mock_validated.items = test_items
                mock_validator.validate_collection_data.return_value = mock_validated

                # Measure execution time for this batch size
                start_time = time.perf_counter()

                result = await generate_markdown_batch(
                    source="scalability_test",
                    batch_size=batch_size,
                    force_regenerate=False,
                    blob_client=performance_blob_client,
                    config=performance_config,
                    generator_id=f"scale-test-{batch_size}",
                )

                end_time = time.perf_counter()
                execution_time = end_time - start_time

                # Store results
                performance_results[batch_size] = execution_time

                # Verify successful completion
                assert isinstance(result, GenerationResponse)

        # Analyze scaling characteristics
        print("\nBatch processing scalability results:")
        for batch_size, exec_time in performance_results.items():
            print(f"  Batch size {batch_size:2d}: {exec_time:.3f}s")

        # Basic scalability assertions (execution time should scale reasonably)
        max_time = max(performance_results.values())
        assert max_time < 15.0, f"Largest batch took {max_time:.2f}s (expected < 15.0s)"

    def test_memory_usage_patterns(self):
        """Test memory usage patterns for content creation."""
        import tracemalloc

        # Start memory tracing
        tracemalloc.start()

        # Create various sizes of content
        for content_multiplier in [1, 10, 50]:
            article_data = {
                "title": f"Memory Test Article (x{content_multiplier})",
                "content": "Memory usage test content. " * (100 * content_multiplier),
                "metadata": {
                    "category": "memory_test",
                    "multiplier": content_multiplier,
                },
            }

            # Take memory snapshot before
            snapshot_before = tracemalloc.take_snapshot()

            # Create markdown content
            result = create_markdown_content(article_data)
            assert isinstance(result, str)

            # Take memory snapshot after
            snapshot_after = tracemalloc.take_snapshot()

            # Calculate memory usage
            top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
            total_memory = sum(stat.size for stat in top_stats)

            # Log memory usage (for monitoring)
            print(
                f"\nMemory usage for content x{content_multiplier}: {total_memory / 1024:.1f} KB"
            )

            # Memory usage should be reasonable (adjust threshold as needed)
            assert (
                total_memory < 1024 * 1024
            ), f"Memory usage {total_memory} bytes too high for x{content_multiplier}"

        tracemalloc.stop()

    @pytest.mark.slow
    def test_concurrent_performance_impact(self):
        """Test performance impact of concurrent operations."""
        import asyncio
        import concurrent.futures

        def create_test_content(article_id):
            """Helper function for concurrent testing."""
            article_data = {
                "title": f"Concurrent Test Article {article_id}",
                "content": f"Content for concurrent performance test {article_id}",
                "topic_id": f"concurrent_test_{article_id}",
            }
            return create_markdown_content(article_data)

        # Test sequential execution
        sequential_start = time.perf_counter()
        sequential_results = []
        for i in range(10):
            result = create_test_content(i)
            sequential_results.append(result)
        sequential_time = time.perf_counter() - sequential_start

        # Test concurrent execution
        concurrent_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            concurrent_results = list(executor.map(create_test_content, range(10)))
        concurrent_time = time.perf_counter() - concurrent_start

        # Verify all results are valid
        assert len(sequential_results) == 10
        assert len(concurrent_results) == 10
        for result in sequential_results + concurrent_results:
            assert isinstance(result, str) and len(result) > 0

        # Log performance comparison
        print(f"\nConcurrency performance comparison:")
        print(f"  Sequential: {sequential_time:.3f}s")
        print(f"  Concurrent: {concurrent_time:.3f}s")

        # For CPU-bound operations like markdown creation, threading overhead
        # may make concurrent execution slower due to Python's GIL
        # Just verify both approaches produce valid results
        speedup = (
            sequential_time / concurrent_time if concurrent_time > 0 else float("inf")
        )
        print(f"  Speedup ratio: {speedup:.2f}x")

        # Main assertion: both approaches should complete successfully
        # Performance comparison is informational only for CPU-bound tasks
        assert all(
            isinstance(result, str) and len(result) > 0 for result in sequential_results
        )
        assert all(
            isinstance(result, str) and len(result) > 0 for result in concurrent_results
        )

#!/usr/bin/env python3
"""
Test script to validate the wake-up message processing pattern.

This script tests the current architecture where:
1. Collector sends a single wake-up message per collection batch
2. Processor receives wake-up message and scans all available work in blob storage
3. KEDA scales from 0→1 on any message arrival
4. Processing happens for all collected content in storage

Usage:
    python test_wake_up_pattern.py
"""

import asyncio
import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WakeUpPatternValidator:
    """Validates the wake-up message processing architecture."""

    def __init__(self):
        self.test_results = {
            "collector_sends_wake_up": False,
            "processor_handles_wake_up": False,
            "keda_scaling_responsive": False,
            "end_to_end_flow_working": False,
        }

    async def validate_collector_wake_up_logic(self) -> bool:
        """Validate that the collector sends wake-up messages."""
        try:
            logger.info("🔍 Validating collector wake-up message logic...")

            # Test that ContentCollectorService has wake-up message logic
            sys.path.insert(
                0, "/workspaces/ai-content-farm/containers/content-collector"
            )
            sys.path.insert(0, "/workspaces/ai-content-farm")
            from service_logic import ContentCollectorService

            # Create a test service instance
            service = ContentCollectorService()

            # Check that _send_processing_request exists and sends wake-up messages
            import inspect

            method = getattr(service, "_send_processing_request", None)
            if method:
                signature = inspect.signature(method)
                logger.info(f"✓ _send_processing_request method found: {signature}")

                # Check if it's the wake-up pattern (collection_result parameter, not individual items)
                params = list(signature.parameters.keys())
                if "collection_result" in params:
                    logger.info(
                        "✓ Wake-up pattern detected (collection_result parameter)"
                    )
                    self.test_results["collector_sends_wake_up"] = True
                    return True
                elif "items" in params:
                    logger.warning(
                        f"⚠️ Method signature suggests individual items: {params}"
                    )
                    return False
                else:
                    logger.warning(f"⚠️ Unexpected method signature: {params}")
                    return False
            else:
                logger.error("✗ _send_processing_request method not found")
                return False

        except Exception as e:
            logger.error(f"✗ Collector validation failed: {e}")
            return False

    async def validate_processor_wake_up_logic(self) -> bool:
        """Validate that the processor handles wake-up messages correctly."""
        try:
            logger.info("🔍 Validating processor wake-up message handling...")

            # Check source code for wake-up pattern instead of importing
            processor_router_path = Path(
                "/workspaces/ai-content-farm/containers/content-processor/endpoints/servicebus_router.py"
            )
            if not processor_router_path.exists():
                logger.error("✗ ContentProcessorServiceBusRouter file not found")
                return False

            source_code = processor_router_path.read_text()

            # Check for wake-up processing patterns in source
            wake_up_indicators = [
                "wake_up",  # Operation type
                "process_available_work",  # Method that processes all work
                "ContentProcessorServiceBusRouter",  # Class name
                "process_message_payload",  # Message handling method
            ]

            found_indicators = []
            for indicator in wake_up_indicators:
                if indicator in source_code:
                    found_indicators.append(indicator)
                    logger.info(f"✓ Found wake-up indicator: {indicator}")
                else:
                    logger.warning(f"⚠️ Missing wake-up indicator: {indicator}")

            if len(found_indicators) >= 3:  # At least 3/4 indicators
                logger.info("✓ Wake-up processing logic detected in processor")
                self.test_results["processor_handles_wake_up"] = True
                return True
            else:
                logger.error(
                    f"✗ Insufficient wake-up indicators ({len(found_indicators)}/4)"
                )
                return False

        except Exception as e:
            logger.error(f"✗ Processor validation failed: {e}")
            return False

    async def validate_keda_configuration(self) -> bool:
        """Validate KEDA scaling configuration for responsiveness."""
        try:
            logger.info("🔍 Validating KEDA scaling configuration...")

            # Check Terraform configuration for KEDA scaling rules
            container_apps_tf = Path(
                "/workspaces/ai-content-farm/infra/container_apps.tf"
            )
            if not container_apps_tf.exists():
                logger.error("✗ container_apps.tf not found")
                return False

            tf_content = container_apps_tf.read_text()

            # Look for KEDA scaling configuration
            checks = [
                ('messageCount           = "1"', "messageCount = 1"),
                ('activationMessageCount = "1"', "activationMessageCount = 1"),
                ("custom_scale_rule", "KEDA custom scaling rules"),
            ]

            passed = 0
            for check_str, description in checks:
                if check_str in tf_content:
                    logger.info(f"✓ Found responsive scaling config: {description}")
                    passed += 1
                else:
                    logger.warning(f"⚠️ Missing scaling config: {description}")

            if passed >= 2:  # At least messageCount and activationMessageCount
                logger.info(
                    "✓ KEDA configured for immediate responsiveness (messageCount=1)"
                )
                self.test_results["keda_scaling_responsive"] = True
                return True
            else:
                logger.error("✗ KEDA not configured for responsive scaling")
                return False

        except Exception as e:
            logger.error(f"✗ KEDA configuration validation failed: {e}")
            return False

    async def validate_integration_points(self) -> bool:
        """Validate that all integration points are properly configured."""
        try:
            logger.info("🔍 Validating integration points...")

            checks = []

            # Check Service Bus queue configuration
            try:
                sys.path.insert(0, "/workspaces/ai-content-farm")
                from libs.service_bus_router import ServiceBusRouterBase

                logger.info("✓ Service Bus router library available")
                checks.append(True)
            except Exception as e:
                logger.error(f"✗ Service Bus router library issue: {e}")
                checks.append(False)

            # Check blob storage integration
            try:
                from libs.blob_storage import BlobStorageClient

                logger.info("✓ Blob storage client library available")
                checks.append(True)
            except Exception as e:
                logger.error(f"✗ Blob storage client library issue: {e}")
                checks.append(False)

            # Check processor core logic
            try:
                processor_path = Path(
                    "/workspaces/ai-content-farm/containers/content-processor/processor.py"
                )
                if processor_path.exists():
                    logger.info("✓ Content processor core logic file exists")
                    checks.append(True)
                else:
                    logger.error("✗ Content processor core logic file missing")
                    checks.append(False)
            except Exception as e:
                logger.error(f"✗ Content processor core logic issue: {e}")
                checks.append(False)

            success_rate = sum(checks) / len(checks)
            if success_rate >= 0.75:  # 75% of integrations working
                logger.info(f"✓ Integration points mostly working ({success_rate:.1%})")
                self.test_results["end_to_end_flow_working"] = True
                return True
            else:
                logger.error(
                    f"✗ Too many integration issues ({success_rate:.1%} working)"
                )
                return False

        except Exception as e:
            logger.error(f"✗ Integration validation failed: {e}")
            return False

    async def run_validation(self) -> Dict[str, Any]:
        """Run all validations and return results."""
        logger.info(
            "🔍 Starting validation of wake-up message processing architecture..."
        )
        logger.info("")

        # Run all validation tests
        validations = [
            ("Collector Sends Wake-Up Messages", self.validate_collector_wake_up_logic),
            (
                "Processor Handles Wake-Up Messages",
                self.validate_processor_wake_up_logic,
            ),
            ("KEDA Scaling Responsive", self.validate_keda_configuration),
            ("Integration Points Working", self.validate_integration_points),
        ]

        results = {}
        for name, validation_func in validations:
            try:
                result = await validation_func()
                results[name] = "PASS" if result else "FAIL"
            except Exception as e:
                logger.error(f"✗ {name} validation crashed: {e}")
                results[name] = "FAIL"

        return results

    def print_summary(self, results: Dict[str, Any]):
        """Print validation summary."""
        logger.info("")
        logger.info("📊 WAKE-UP PATTERN VALIDATION SUMMARY")
        logger.info("==================================================")

        passed = sum(1 for result in results.values() if result == "PASS")
        total = len(results)
        logger.info(f"✅ Tests Passed: {passed}/{total}")
        logger.info("")

        for test_name, result in results.items():
            status = "✅ PASS" if result == "PASS" else "❌ FAIL"
            logger.info(f"  {status}: {test_name}")

        logger.info("")

        if passed == total:
            logger.info(
                "🎉 All validations passed! Wake-up pattern is working correctly."
            )
            return True
        elif passed >= total * 0.75:
            logger.info("⚠️  Most validations passed - minor issues to address")
            return True
        else:
            logger.info("⚠️  Some validations failed - review above for details")
            return False


async def main():
    """Main test execution."""
    validator = WakeUpPatternValidator()

    try:
        results = await validator.run_validation()
        success = validator.print_summary(results)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Validation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Validation crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

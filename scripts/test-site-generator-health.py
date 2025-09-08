#!/usr/bin/env python3
"""
Test script for site-generator health endpoint

This script tests the Azure Container Apps site-generator health endpoint
to help diagnose and resolve the 504 timeout issue.
"""

import asyncio
import json
import sys
import time
from typing import Any, Dict

import aiohttp


async def test_health_endpoint(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Test the health endpoint with proper timeout handling."""
    print(f"🧪 Testing health endpoint: {url}")
    print(f"⏱️  Timeout: {timeout} seconds")

    start_time = time.time()

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            async with session.get(url) as response:
                end_time = time.time()
                response_time = end_time - start_time

                print(f"📊 Status Code: {response.status}")
                print(f"⏱️  Response Time: {response_time:.2f}s")
                print(f"📋 Headers: {dict(response.headers)}")

                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"✅ Health Check Successful!")
                        print(f"📄 Response Data: {json.dumps(data, indent=2)}")
                        return {
                            "success": True,
                            "status_code": response.status,
                            "response_time": response_time,
                            "data": data,
                        }
                    except Exception as json_error:
                        text_data = await response.text()
                        print(f"⚠️  JSON parsing failed: {json_error}")
                        print(f"📄 Raw Response: {text_data}")
                        return {
                            "success": True,
                            "status_code": response.status,
                            "response_time": response_time,
                            "raw_data": text_data,
                            "json_error": str(json_error),
                        }
                else:
                    text_data = await response.text()
                    print(f"❌ Health Check Failed!")
                    print(f"📄 Error Response: {text_data}")
                    return {
                        "success": False,
                        "status_code": response.status,
                        "response_time": response_time,
                        "error_data": text_data,
                    }

    except asyncio.TimeoutError:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"⏰ Request timed out after {response_time:.2f}s")
        return {"success": False, "error": "timeout", "response_time": response_time}
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"💥 Request failed: {e}")
        return {"success": False, "error": str(e), "response_time": response_time}


async def test_all_endpoints():
    """Test all container app health endpoints."""

    base_url = "https://ai-content-prod-{service}.happysea-caceb272.uksouth.azurecontainerapps.io"

    services = ["collector", "processor", "site-generator"]

    results = {}

    for service in services:
        print(f"\n{'='*60}")
        print(f"🔍 Testing {service.upper()} Container App")
        print(f"{'='*60}")

        service_url = base_url.format(service=service)
        health_url = f"{service_url}/health"

        result = await test_health_endpoint(health_url)
        results[service] = result

        # Also test the base URL
        print(f"\n📍 Testing base endpoint...")
        base_result = await test_health_endpoint(service_url, timeout=10)
        results[f"{service}_base"] = base_result

        print(f"\n⏸️  Waiting 2 seconds before next test...")
        await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"📊 SUMMARY REPORT")
    print(f"{'='*60}")

    for service, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        response_time = result.get("response_time", 0)
        print(f"{service:20} {status:8} {response_time:.2f}s")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific URL
        url = sys.argv[1]
        result = asyncio.run(test_health_endpoint(url))
        print(f"\nFinal Result: {json.dumps(result, indent=2)}")
    else:
        # Test all endpoints
        results = asyncio.run(test_all_endpoints())
        print(f"\nFull Results: {json.dumps(results, indent=2)}")

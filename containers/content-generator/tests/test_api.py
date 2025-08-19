#!/usr/bin/env python3
"""
Test the Content Generator HTTP API
"""

import requests
import json


def test_api():
    base_url = "http://localhost:8000"

    print("🌐 Testing Content Generator HTTP API")
    print("=" * 40)

    try:
        # Test root endpoint
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print("✅ Root endpoint working")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False

        # Test health endpoint
        response = requests.get(f"{base_url}/health")
        # 503 is expected without AI keys
        if response.status_code in [200, 503]:
            data = response.json()
            print(
                f"✅ Health endpoint working (status: {response.status_code})")
            print(f"   Health Status: {data.get('status')}")
            print(f"   Service: {data.get('service')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False

        # Test status endpoint
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            data = response.json()
            print("✅ Status endpoint working")
            print(f"   Uptime: {data.get('uptime_seconds', 0):.1f}s")
            print(
                f"   Active generations: {data.get('active_generations', 0)}")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")

        print("\n🎉 HTTP API Integration Test Complete!")
        return True

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to service. Is it running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)

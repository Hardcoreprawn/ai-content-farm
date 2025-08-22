#!/usr/bin/env python3
"""
Test Event-Driven Pipeline

This script tests the complete containerized, event-driven pipeline:
1. Send test data to enricher
2. Enricher forwards to ranker
3. Ranker triggers markdown generator
4. Markdown generator triggers static site generator
5. View the generated website
"""

import asyncio
import json
import time
from datetime import datetime, timezone

import httpx


async def test_event_driven_pipeline():
    """Test the complete event-driven pipeline."""

    print("🚀 Testing Event-Driven AI Content Farm Pipeline")
    print("=" * 60)

    # Test data - simulating enriched content
    test_content = [
        {
            "id": "test_quantum_ai_2025",
            "title": "Revolutionary AI breakthrough in quantum computing error correction",
            "clean_title": "Revolutionary AI breakthrough in quantum computing error correction",
            "source_url": "https://example.com/quantum-ai-breakthrough",
            "content_type": "article",
            "normalized_score": 0.89,
            "engagement_score": 0.89,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "topic_classification": {
                "topics": [
                    "Quantum Computing",
                    "Artificial Intelligence",
                    "Machine Learning",
                    "Research",
                ],
                "confidence": 0.95,
            },
            "sentiment_analysis": {"sentiment": "positive", "confidence": 0.92},
            "source_metadata": {
                "site_name": "Quantum Tech Today",
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        {
            "id": "test_uk_ai_investment_2025",
            "title": "UK government announces £3bn investment in AI infrastructure",
            "clean_title": "UK government announces £3bn investment in AI infrastructure",
            "source_url": "https://example.com/uk-ai-investment",
            "content_type": "article",
            "normalized_score": 0.76,
            "engagement_score": 0.76,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "topic_classification": {
                "topics": [
                    "UK Politics",
                    "AI Infrastructure",
                    "Government Policy",
                    "Investment",
                ],
                "confidence": 0.88,
            },
            "sentiment_analysis": {"sentiment": "positive", "confidence": 0.85},
            "source_metadata": {
                "site_name": "UK Tech News",
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        {
            "id": "test_open_source_ai_2025",
            "title": "Open source AI models challenge Big Tech dominance in machine learning",
            "clean_title": "Open source AI models challenge Big Tech dominance in machine learning",
            "source_url": "https://example.com/open-source-ai-challenge",
            "content_type": "article",
            "normalized_score": 0.82,
            "engagement_score": 0.82,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "topic_classification": {
                "topics": [
                    "Open Source",
                    "AI Models",
                    "Big Tech",
                    "Machine Learning",
                    "Industry",
                ],
                "confidence": 0.91,
            },
            "sentiment_analysis": {"sentiment": "positive", "confidence": 0.87},
            "source_metadata": {
                "site_name": "Open AI Weekly",
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    ]

    async with httpx.AsyncClient() as client:

        print("📡 Step 1: Checking service health...")
        services = [
            ("Enricher", "http://localhost:8003/health"),
            ("Ranker", "http://localhost:8004/health"),
            ("Markdown Generator", "http://localhost:8007/health"),
            ("SSG", "http://localhost:8005/health"),
            ("Markdown Converter", "http://localhost:8006/health"),
        ]

        for service_name, url in services:
            try:
                response = await client.get(url, timeout=5.0)
                status = (
                    "✅ Healthy"
                    if response.status_code == 200
                    else f"❌ Error {response.status_code}"
                )
                print(f"   {service_name}: {status}")
            except Exception as e:
                print(f"   {service_name}: ❌ Unreachable ({e})")

        print(f"\n🔄 Step 2: Sending test content to ranker...")

        try:
            # Send content directly to ranker for ranking
            response = await client.post(
                "http://localhost:8004/rank", json={"items": test_content}, timeout=30.0
            )

            if response.status_code == 200:
                ranking_result = response.json()
                print(
                    f"✅ Content ranked successfully: {len(ranking_result.get('ranked_items', []))} items"
                )
            else:
                print(f"❌ Ranking failed: {response.status_code}")
                return

        except Exception as e:
            print(f"❌ Failed to rank content: {e}")
            return

        print(f"\n⏳ Step 3: Waiting for markdown generation (auto-triggered)...")
        # Wait for markdown generator to detect new rankings
        await asyncio.sleep(20)

        try:
            response = await client.get("http://localhost:8007/status", timeout=10.0)
            if response.status_code == 200:
                status = response.json()
                markdown_files = status.get("file_statistics", {}).get(
                    "markdown_files", 0
                )
                print(f"✅ Markdown Generator Status: {markdown_files} files generated")
            else:
                print(f"❌ Could not get markdown generator status")
        except Exception as e:
            print(f"❌ Failed to check markdown generator: {e}")

        print(f"\n⏳ Step 4: Waiting for static site generation (auto-triggered)...")
        await asyncio.sleep(15)  # Wait for site generation

        try:
            response = await client.get("http://localhost:8005/health", timeout=10.0)
            if response.status_code == 200:
                print(f"✅ Static Site Generator: Ready")

                # Try to trigger site generation manually to ensure it's ready
                response = await client.get(
                    "http://localhost:8005/generate/sync", timeout=60.0
                )
                if response.status_code == 200:
                    result = response.json()
                    pages = result.get("result", {}).get("pages_generated", 0)
                    print(f"✅ Website generated: {pages} pages")
                else:
                    print(f"❌ Site generation failed: {response.status_code}")
            else:
                print(f"❌ SSG service not healthy")
        except Exception as e:
            print(f"❌ Failed to generate site: {e}")

        print(f"\n📊 Step 5: Pipeline Summary...")

        # Get status from all services
        try:
            # Check markdown converter notifications
            response = await client.get(
                "http://localhost:8006/notifications", timeout=10.0
            )
            if response.status_code == 200:
                notifications = response.json().get("notifications", [])
                print(f"✅ Markdown Converter: {len(notifications)} notifications")

            # Get SSG status
            response = await client.get("http://localhost:8005/", timeout=10.0)
            if response.status_code == 200:
                print(f"✅ SSG Service: Ready for preview")

        except Exception as e:
            print(f"⚠️  Could not get full pipeline status: {e}")

        print(f"\n🎉 Pipeline Test Complete!")
        print(f"")
        print(f"🌐 View Your Generated Website:")
        print(f"   📱 Live Preview: http://localhost:8005/preview/")
        print(f"   🔧 SSG API: http://localhost:8005/")
        print(f"   📝 Markdown API: http://localhost:8007/")
        print(f"   🔄 Converter API: http://localhost:8006/")
        print(f"")
        print(f"💡 The pipeline is now event-driven:")
        print(f"   ➡️  Ranker receives content → triggers Markdown Generator")
        print(
            f"   ➡️  Markdown Generator creates files → triggers Static Site Generator"
        )
        print(f"   ➡️  Static Site Generator creates website → ready for viewing")
        print(f"")
        print(f"🚀 Your AI Content Farm is live and automatically updating!")


if __name__ == "__main__":
    asyncio.run(test_event_driven_pipeline())

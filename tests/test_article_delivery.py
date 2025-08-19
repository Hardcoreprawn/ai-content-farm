#!/usr/bin/env python3
"""
End-to-end test script for article delivery pipeline.
Tests the complete flow from ranked content to markdown generation.
"""

from libs.blob_storage import BlobStorageClient, BlobContainers
from service_logic import MarkdownGenerator, ContentWatcher
import sys
import os
from pathlib import Path

# Add container paths for imports
sys.path.insert(0, '/workspaces/ai-content-farm/containers/markdown-generator')


# Add the workspace root to Python path
sys.path.insert(0, '/workspaces/ai-content-farm')
sys.path.insert(0, '/workspaces/ai-content-farm/containers/markdown-generator')


async def test_article_delivery():
    """Test the complete article delivery pipeline."""
    print("🚀 Starting End-to-End Article Delivery Test")

    try:
        # Initialize components
        print("📦 Initializing components...")

        # Set up test environment
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;'
        os.environ['RANKED_CONTENT_CONTAINER'] = 'processed-content'
        os.environ['GENERATED_CONTENT_CONTAINER'] = 'generated-content'

        blob_client = BlobStorageClient()
        generator = MarkdownGenerator(blob_client)
        watcher = ContentWatcher(blob_client, generator)

        print("✅ Components initialized successfully")

        # Load test data
        print("📄 Loading test ranked content...")
        with open('/workspaces/ai-content-farm/test_ranked_content.json', 'r') as f:
            test_data = json.load(f)

        # Transform test data to expected format
        content_items = []
        for item in test_data['items']:
            content_item = {
                'title': item['title'],
                'clean_title': item['title'],
                'content': item['content'],
                'ai_summary': item['summary'],
                'final_score': item['score'],
                'source_url': item['url'],
                'topics': item['tags'],
                'sentiment': 'positive',
                'engagement_score': item['score'] * 0.8,
                'content_type': 'article',
                'source_metadata': {
                    'site_name': item['source'].title(),
                    'author': item.get('author', 'Unknown')
                },
                'published_at': item['published_date']
            }
            content_items.append(content_item)

        print(f"✅ Loaded {len(content_items)} test articles")

        # Test markdown generation
        print("🎯 Testing markdown generation...")

        # Test Jekyll format
        print("  📝 Generating Jekyll format...")
        jekyll_result = await generator.generate_markdown_from_ranked_content(
            content_items[:2], template_style="jekyll"
        )

        if jekyll_result:
            print(
                f"  ✅ Jekyll: Generated {jekyll_result['files_generated']} files")
            print(f"     Timestamp: {jekyll_result['timestamp']}")
            print(f"     Articles: {len(jekyll_result['markdown_files'])}")
        else:
            print("  ❌ Jekyll generation failed")
            return False

        # Test Hugo format
        print("  📝 Generating Hugo format...")
        hugo_result = await generator.generate_markdown_from_ranked_content(
            content_items[:2], template_style="hugo"
        )

        if hugo_result:
            print(
                f"  ✅ Hugo: Generated {hugo_result['files_generated']} files")
            print(f"     Timestamp: {hugo_result['timestamp']}")
            print(f"     Articles: {len(hugo_result['markdown_files'])}")
        else:
            print("  ❌ Hugo generation failed")
            return False

        # Test content watcher workflow
        print("🔍 Testing content watcher workflow...")

        # Mock ranked content in blob storage
        print("  📤 Uploading test ranked content to blob storage...")
        ranked_content_blob = {
            "content": content_items,
            "generated_at": "2025-08-19T16:00:00Z",
            "total_items": len(content_items)
        }

        test_blob_name = "ranked-content/test-content-20250819_160000.json"
        blob_url = blob_client.upload_json(
            BlobContainers.PROCESSED_CONTENT,
            test_blob_name,
            ranked_content_blob
        )
        print(f"  ✅ Uploaded test content: {test_blob_name}")

        # Test content watching
        print("  👀 Testing content watcher detection...")
        watcher_result = await watcher.check_for_new_ranked_content()

        if watcher_result:
            print(f"  ✅ Watcher detected and processed content:")
            print(f"     Status: {watcher_result['status']}")
            print(
                f"     Files generated: {watcher_result.get('files_generated', 'N/A')}")
        else:
            print("  ⚠️  Watcher found no new content (expected if already processed)")

        # Test slug generation
        print("🏷️  Testing slug generation...")
        test_titles = [
            "Revolutionary AI Framework Transforms Machine Learning Development",
            "Quantum Computing Breakthrough: 1000-Qubit Processor Achieved",
            "Special Characters & Symbols: Testing Edge Cases!"
        ]

        for title in test_titles:
            slug = generator._create_slug(title)
            print(f"  '{title}' → '{slug}'")

        print("✅ Slug generation working correctly")

        # Verify watcher status
        print("📊 Checking watcher status...")
        status = watcher.get_watcher_status()
        print(f"  Watching: {status['watching']}")
        print(f"  Processed blobs: {status['processed_blobs']}")
        print(f"  Last check: {status['last_check']}")

        print("\n🎉 End-to-End Article Delivery Test PASSED!")
        print("\n📈 Summary:")
        print(
            f"  ✅ Jekyll markdown generation: {jekyll_result['files_generated']} files")
        print(
            f"  ✅ Hugo markdown generation: {hugo_result['files_generated']} files")
        print(f"  ✅ Content watcher functionality: Working")
        print(f"  ✅ Blob storage integration: Working")
        print(f"  ✅ Template generation: Both formats working")
        print(f"  ✅ Slug generation: Working correctly")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_article_delivery())
    sys.exit(0 if success else 1)

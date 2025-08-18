#!/usr/bin/env python3
"""
Test Web Content Pipeline

Creates sample web content and runs it through the processing pipeline.
"""

import requests
import json
from datetime import datetime, timezone


def create_sample_web_content():
    """Create sample web content for testing pipeline."""
    return [
        {
            'id': 'arstechnica_12345',
            'source': 'web',
            'site': 'arstechnica',
            'site_name': 'Ars Technica',
            'title': 'AI researchers develop new method for quantum computing optimization',
            'content': 'Scientists at leading research institutions have unveiled a groundbreaking approach to quantum computing that could dramatically improve processing speeds for AI workloads. The new method combines quantum error correction with machine learning algorithms to achieve unprecedented computational efficiency.',
            'url': 'https://arstechnica.com/science/2025/08/ai-quantum-computing-breakthrough/',
            'author': 'Ars Technica',
            'score': 0,
            'num_comments': 0,
            'content_type': 'article',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'raw_data': {
                'source': 'web',
                'source_type': 'rss_feed',
                'site': 'arstechnica'
            }
        },
        {
            'id': 'theregister_67890',
            'source': 'web',
            'site': 'theregister',
            'site_name': 'The Register',
            'title': 'UK tech startups see record funding amid AI boom',
            'content': 'British technology startups secured unprecedented levels of venture capital funding this quarter, with artificial intelligence companies leading the charge. The surge reflects growing investor confidence in the UK\'s position as a global AI hub, particularly in areas like healthcare AI and autonomous systems.',
            'url': 'https://www.theregister.com/2025/08/15/uk_tech_funding_ai/',
            'author': 'The Register',
            'score': 0,
            'num_comments': 0,
            'content_type': 'article',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'raw_data': {
                'source': 'web',
                'source_type': 'rss_feed',
                'site': 'theregister'
            }
        },
        {
            'id': 'thenewstack_11111',
            'source': 'web',
            'site': 'thenewstack',
            'site_name': 'The New Stack',
            'title': 'Container orchestration evolves with WebAssembly integration',
            'content': 'The latest developments in container orchestration platforms are embracing WebAssembly (WASM) as a lightweight alternative to traditional containerization. This shift promises faster startup times, improved security, and better resource utilization for cloud-native applications.',
            'url': 'https://thenewstack.io/container-orchestration-webassembly/',
            'author': 'The New Stack',
            'score': 0,
            'num_comments': 0,
            'content_type': 'article',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'raw_data': {
                'source': 'web',
                'source_type': 'rss_feed',
                'site': 'thenewstack'
            }
        }
    ]


def test_pipeline():
    """Test the full pipeline with sample web content."""
    print('🌐 AI Content Farm - Web Content Pipeline Test')
    print('='*60)

    # Create sample content
    print('📝 Creating sample web content...')
    sample_items = create_sample_web_content()
    print(f'✅ Created {len(sample_items)} sample articles')

    try:
        # Step 1: Process content
        print('⚙️  Step 1: Processing content...')
        process_response = requests.post('http://localhost:8002/process',
                                         json={'items': sample_items}, timeout=15)

        if process_response.status_code == 200:
            process_data = process_response.json()
            processed_items = process_data['processed_items']
            print(f'✅ Processed {len(processed_items)} items')

            # Step 2: Enrich content
            print('🎨 Step 2: Enriching content...')
            enrich_response = requests.post('http://localhost:8003/enrich',
                                            json={'items': processed_items}, timeout=20)

            if enrich_response.status_code == 200:
                enrich_data = enrich_response.json()
                enriched_items = enrich_data['enriched_items']
                print(f'✅ Enriched {len(enriched_items)} items')

                # Step 3: Rank content
                print('📊 Step 3: Ranking content...')
                rank_response = requests.post('http://localhost:8004/rank',
                                              json={'items': enriched_items}, timeout=15)

                if rank_response.status_code == 200:
                    rank_data = rank_response.json()
                    ranked_items = rank_data['ranked_items']
                    print(f'✅ Ranked {len(ranked_items)} items')
                    print()
                    print('🎉 PIPELINE COMPLETE! Here are the results:')
                    print('='*60)

                    # Show all ranked items with detailed info
                    for i, item in enumerate(ranked_items, 1):
                        print(f'{i}. {item["title"]}')
                        print(
                            f'   📊 Final Score: {item.get("final_score", 0):.3f}')
                        print(
                            f'   🌐 Source: {item.get("source_metadata", {}).get("site_name", "Unknown")}')
                        print(
                            f'   📈 Engagement: {item.get("engagement_score", 0):.3f}')
                        print(
                            f'   📝 Summary: {item.get("ai_summary", "No summary available")[:120]}...')
                        print(
                            f'   🏷️  Topics: {", ".join(item.get("topics", ["None"])[:3])}')
                        print(
                            f'   😊 Sentiment: {item.get("sentiment", "neutral").title()}')
                        print(f'   🔗 URL: {item.get("source_url", "No URL")}')
                        print()

                    # Save results
                    output_file = f'/workspaces/ai-content-farm/output/web_pipeline_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                    with open(output_file, 'w') as f:
                        json.dump({
                            'processed_items': processed_items,
                            'enriched_items': enriched_items,
                            'ranked_items': ranked_items,
                            'metadata': {
                                'test_type': 'web_content_pipeline',
                                'timestamp': datetime.now(timezone.utc).isoformat(),
                                'items_count': len(ranked_items)
                            }
                        }, f, indent=2)
                    print(f'💾 Results saved to: {output_file}')

                else:
                    print(f'❌ Ranking failed: {rank_response.status_code}')
                    print(rank_response.text[:300])
            else:
                print(f'❌ Enrichment failed: {enrich_response.status_code}')
                print(enrich_response.text[:300])
        else:
            print(f'❌ Processing failed: {process_response.status_code}')
            print(process_response.text[:300])

    except Exception as e:
        print(f'❌ Pipeline test failed: {e}')


if __name__ == '__main__':
    test_pipeline()

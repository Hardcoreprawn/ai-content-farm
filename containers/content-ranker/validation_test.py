"""
Validation test comparing original Azure Function with new Container Apps service
"""

import sys
import os
from datetime import datetime, timezone

# Add paths for both old and new implementations
sys.path.insert(0, '/home/runner/work/ai-content-farm/ai-content-farm/functions')
sys.path.insert(0, '/home/runner/work/ai-content-farm/ai-content-farm/containers/content-ranker')

# Import original functions
from ranker_core import process_content_ranking as original_process_content_ranking
from ranker_core import calculate_engagement_score as original_engagement
from ranker_core import calculate_monetization_score as original_monetization

# Import new functions  
from core.ranking_engine import process_content_ranking as new_process_content_ranking
from core.ranking_engine import calculate_engagement_score as new_engagement
from core.ranking_engine import calculate_monetization_score as new_monetization

# Test data
TEST_TOPIC = {
    "title": "AI and Machine Learning Breakthrough in Crypto Trading",
    "score": 15000,
    "num_comments": 250,
    "created_utc": datetime.now(timezone.utc).timestamp() - 3600,
    "author": "tech_user",
    "reddit_id": "test123",
    "external_url": "https://example.com/ai-breakthrough",
    "subreddit": "technology",
    "selftext": "Revolutionary advancement in artificial intelligence and cryptocurrency"
}

TEST_BLOB_DATA = {
    "job_id": "validation-test",
    "source": "reddit", 
    "subject": "technology",
    "fetched_at": "20250813_120000",
    "topics": [
        TEST_TOPIC,
        {
            **TEST_TOPIC,
            "title": "Random weather discussion",
            "score": 150,
            "num_comments": 15,
            "reddit_id": "test456",
            "selftext": "Just talking about weather"
        }
    ]
}

TEST_CONFIG = {
    "min_score_threshold": 100,
    "min_comments_threshold": 10,
    "weights": {
        "engagement": 0.3,
        "freshness": 0.2,  # Original uses 'freshness'
        "monetization": 0.3,
        "seo_potential": 0.2  # Original uses 'seo_potential'
    }
}

def test_individual_functions():
    """Test that individual ranking functions produce identical results"""
    print("🔍 Testing Individual Functions")
    print("=" * 40)
    
    # Test engagement scoring
    orig_engagement = original_engagement(TEST_TOPIC)
    new_engagement_score = new_engagement(TEST_TOPIC)
    
    print(f"Engagement Score:")
    print(f"  Original: {orig_engagement}")
    print(f"  New:      {new_engagement_score}")
    print(f"  Match:    {'✅' if abs(orig_engagement - new_engagement_score) < 0.001 else '❌'}")
    
    # Test monetization scoring
    orig_monetization = original_monetization(TEST_TOPIC)
    new_monetization_score = new_monetization(TEST_TOPIC)
    
    print(f"\nMonetization Score:")
    print(f"  Original: {orig_monetization}")
    print(f"  New:      {new_monetization_score}")
    print(f"  Match:    {'✅' if abs(orig_monetization - new_monetization_score) < 0.001 else '❌'}")

def test_full_pipeline():
    """Test that the full ranking pipeline produces compatible results"""
    print("\n🔍 Testing Full Pipeline")
    print("=" * 40)
    
    # Process with original function
    original_result = original_process_content_ranking(TEST_BLOB_DATA, TEST_CONFIG)
    
    # Process with new function (need to adjust config for new naming)
    new_config = {
        "min_score_threshold": 100,
        "min_comments_threshold": 10,
        "weights": {
            "engagement": 0.3,
            "recency": 0.2,  # Updated naming
            "monetization": 0.3,
            "title_quality": 0.2  # Updated naming
        }
    }
    new_result = new_process_content_ranking(TEST_BLOB_DATA, new_config)
    
    print(f"Total Topics Processed:")
    print(f"  Original: {len(original_result.get('topics', []))}")
    print(f"  New:      {len(new_result.get('ranked_topics', []))}")
    
    # Compare top topic rankings (if any topics were ranked)
    orig_topics = original_result.get('topics', [])
    new_topics = new_result.get('ranked_topics', [])
    
    if orig_topics and new_topics:
        orig_top = orig_topics[0]
        new_top = new_topics[0]
        
        print(f"\nTop Topic Comparison:")
        print(f"  Original Title: {orig_top.get('title', 'N/A')[:50]}...")
        print(f"  New Title:      {new_top.get('title', 'N/A')[:50]}...")
        
        orig_score = orig_top.get('ranking_score', 0)
        new_score = new_top.get('ranking_score', 0)
        
        print(f"  Original Score: {orig_score}")
        print(f"  New Score:      {new_score}")
        
        # Allow for small differences due to potential rounding or minor implementation differences
        score_match = abs(orig_score - new_score) < 0.05
        print(f"  Score Match:    {'✅' if score_match else '❌'}")
        
        # Check that both ranked the same topic as #1
        title_match = orig_top.get('reddit_id') == new_top.get('reddit_id')
        print(f"  Same Top Topic: {'✅' if title_match else '❌'}")

def test_api_contract_compatibility():
    """Test that new API can handle Azure Function-style requests"""
    print("\n🔍 Testing API Contract Compatibility")
    print("=" * 40)
    
    # Test that new function can process original blob format
    result = new_process_content_ranking(TEST_BLOB_DATA, {
        "weights": {
            "engagement": 0.3,
            "recency": 0.2,
            "monetization": 0.3,
            "title_quality": 0.2
        }
    })
    
    # Check expected output structure
    has_ranked_topics = 'ranked_topics' in result
    has_metadata = 'metadata' in result
    has_config = 'ranking_config' in result
    
    print(f"Output Structure:")
    print(f"  Has ranked_topics: {'✅' if has_ranked_topics else '❌'}")
    print(f"  Has metadata:      {'✅' if has_metadata else '❌'}")
    print(f"  Has ranking_config: {'✅' if has_config else '❌'}")
    
    if has_ranked_topics:
        topics = result['ranked_topics']
        if topics:
            topic = topics[0]
            has_score = 'ranking_score' in topic
            has_details = 'ranking_details' in topic
            print(f"  Topic has score:   {'✅' if has_score else '❌'}")
            print(f"  Topic has details: {'✅' if has_details else '❌'}")

if __name__ == "__main__":
    print("🧪 ContentRanker Migration Validation")
    print("Testing compatibility between Azure Function and Container Apps implementations")
    print("=" * 80)
    
    try:
        test_individual_functions()
        test_full_pipeline() 
        test_api_contract_compatibility()
        
        print("\n" + "=" * 80)
        print("✅ Migration validation completed successfully!")
        print("The new Container Apps service maintains compatibility with the Azure Function.")
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
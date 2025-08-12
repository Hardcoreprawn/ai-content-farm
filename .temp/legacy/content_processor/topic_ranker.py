#!/usr/bin/env python3
"""
Topic Ranker - Evaluates collected topics for publishing worthiness.

This module analyzes topics from various sources and ranks them based on:
- Engagement metrics (scores, comments)
- Content quality indicators
- Monetization potential
- Recency and trending status
- SEO potential
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
import requests
from urllib.parse import urlparse
import re

class TopicRanker:
    def __init__(self, output_dir: str = "../output"):
        self.output_dir = output_dir
        self.min_score_threshold = 100  # Minimum Reddit score
        self.min_comments_threshold = 10  # Minimum comments
        self.hours_fresh_threshold = 48  # Consider "fresh" if within 48 hours
        
        # Keywords that indicate high monetization potential
        self.high_value_keywords = [
            "AI", "artificial intelligence", "machine learning", "crypto", "bitcoin",
            "technology", "startup", "innovation", "breakthrough", "investment",
            "market", "stock", "IPO", "acquisition", "merger", "funding",
            "productivity", "tool", "software", "app", "platform", "service"
        ]
        
        # Keywords that might indicate controversial/risky content
        self.risk_keywords = [
            "lawsuit", "scandal", "controversy", "hack", "breach", "leak",
            "illegal", "banned", "suspended", "fired", "resigned"
        ]

    def load_recent_topics(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Load topics from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        topics = []
        
        if not os.path.exists(self.output_dir):
            print(f"Output directory {self.output_dir} not found")
            return topics
            
        for filename in os.listdir(self.output_dir):
            if filename.endswith('.json') and 'reddit' in filename:
                # Extract timestamp from filename: YYYYMMDD_HHMMSS_reddit_subreddit.json
                try:
                    timestamp_str = filename.split('_')[0] + '_' + filename.split('_')[1]
                    file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if file_time >= cutoff_time:
                        filepath = os.path.join(self.output_dir, filename)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            for topic in data.get('topics', []):
                                topic['source_file'] = filename
                                topics.append(topic)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue
                    
        return topics

    def calculate_engagement_score(self, topic: Dict[str, Any]) -> float:
        """Calculate engagement score based on Reddit metrics."""
        score = topic.get('score', 0)
        comments = topic.get('num_comments', 0)
        
        # Weight formula: score + (comments * 2) 
        # Comments are weighted more as they indicate higher engagement
        engagement = score + (comments * 2)
        
        # Bonus for high-engagement posts
        if comments > 100:
            engagement *= 1.2
        if score > 1000:
            engagement *= 1.1
            
        return engagement

    def calculate_freshness_score(self, topic: Dict[str, Any]) -> float:
        """Calculate freshness score - higher for more recent content."""
        created_utc = topic.get('created_utc', 0)
        if not created_utc:
            return 0.0
            
        post_time = datetime.fromtimestamp(created_utc)
        now = datetime.now()
        age_hours = (now - post_time).total_seconds() / 3600
        
        # Score decreases with age
        if age_hours <= 6:
            return 1.0
        elif age_hours <= 24:
            return 0.8
        elif age_hours <= 48:
            return 0.6
        elif age_hours <= 72:
            return 0.4
        else:
            return 0.2

    def calculate_monetization_potential(self, topic: Dict[str, Any]) -> float:
        """Calculate monetization potential based on content and keywords."""
        title = topic.get('title', '').lower()
        selftext = topic.get('selftext', '').lower()
        content = title + ' ' + selftext
        
        score = 0.0
        
        # Check for high-value keywords
        for keyword in self.high_value_keywords:
            if keyword.lower() in content:
                score += 0.1
                
        # Reduce score for risky content
        for keyword in self.risk_keywords:
            if keyword.lower() in content:
                score -= 0.2
                
        # Bonus for external URL (indicates substantial content)
        if topic.get('external_url') and not topic.get('external_url').startswith('https://www.reddit.com'):
            score += 0.3
            
        # Bonus for substantial self-text
        if len(topic.get('selftext', '')) > 200:
            score += 0.2
            
        return max(0.0, min(1.0, score))

    def calculate_seo_potential(self, topic: Dict[str, Any]) -> float:
        """Calculate SEO potential based on title quality and topic."""
        title = topic.get('title', '')
        
        score = 0.0
        
        # Good title length (50-60 chars is optimal for SEO)
        title_len = len(title)
        if 30 <= title_len <= 70:
            score += 0.3
        elif 20 <= title_len <= 90:
            score += 0.2
            
        # Check for question format (good for SEO)
        if '?' in title or title.lower().startswith(('how', 'what', 'why', 'when', 'where')):
            score += 0.2
            
        # Check for numbers (listicles perform well)
        if re.search(r'\d+', title):
            score += 0.1
            
        # Avoid clickbait indicators
        clickbait_indicators = ['you won\'t believe', 'shocking', 'amazing', 'incredible']
        if any(indicator in title.lower() for indicator in clickbait_indicators):
            score -= 0.2
            
        return max(0.0, min(1.0, score))

    def rank_topic(self, topic: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Rank a single topic and return overall score with breakdown."""
        # Calculate individual scores
        engagement = self.calculate_engagement_score(topic)
        freshness = self.calculate_freshness_score(topic)
        monetization = self.calculate_monetization_potential(topic)
        seo = self.calculate_seo_potential(topic)
        
        # Normalize engagement score (log scale to handle very high values)
        import math
        engagement_normalized = min(1.0, math.log(engagement + 1) / math.log(10000))
        
        # Weighted final score
        weights = {
            'engagement': 0.4,
            'freshness': 0.2,
            'monetization': 0.3,
            'seo': 0.1
        }
        
        final_score = (
            engagement_normalized * weights['engagement'] +
            freshness * weights['freshness'] +
            monetization * weights['monetization'] +
            seo * weights['seo']
        )
        
        score_breakdown = {
            'engagement': engagement_normalized,
            'freshness': freshness,
            'monetization': monetization,
            'seo': seo,
            'final': final_score
        }
        
        return final_score, score_breakdown

    def _deduplicate_topics(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate topics based on title similarity and external URL."""
        seen_titles = set()
        seen_urls = set()
        unique_topics = []
        
        for topic in topics:
            title = topic.get('title', '').strip().lower()
            external_url = topic.get('external_url', '').strip()
            
            # Create a normalized title for comparison (remove punctuation, extra spaces)
            import re
            normalized_title = re.sub(r'[^\w\s]', '', title)
            normalized_title = re.sub(r'\s+', ' ', normalized_title).strip()
            
            # Check for duplicate by normalized title
            title_duplicate = False
            for seen_title in seen_titles:
                # Check if titles are very similar (>80% similarity)
                if self._calculate_title_similarity(normalized_title, seen_title) > 0.8:
                    title_duplicate = True
                    break
            
            # Check for duplicate by external URL
            url_duplicate = external_url in seen_urls if external_url else False
            
            if not title_duplicate and not url_duplicate:
                seen_titles.add(normalized_title)
                if external_url:
                    seen_urls.add(external_url)
                unique_topics.append(topic)
            else:
                # Keep the topic with higher engagement if it's a duplicate
                existing_topic = None
                for i, existing in enumerate(unique_topics):
                    existing_title = re.sub(r'[^\w\s]', '', existing.get('title', '').strip().lower())
                    existing_title = re.sub(r'\s+', ' ', existing_title).strip()
                    
                    if (self._calculate_title_similarity(normalized_title, existing_title) > 0.8 or 
                        existing.get('external_url') == external_url):
                        existing_topic = existing
                        existing_index = i
                        break
                
                if existing_topic:
                    # Compare engagement scores
                    current_engagement = self.calculate_engagement_score(topic)
                    existing_engagement = self.calculate_engagement_score(existing_topic)
                    
                    if current_engagement > existing_engagement:
                        # Find and replace with higher engagement version
                        for i, existing in enumerate(unique_topics):
                            existing_title = re.sub(r'[^\w\s]', '', existing.get('title', '').strip().lower())
                            existing_title = re.sub(r'\s+', ' ', existing_title).strip()
                            
                            if (self._calculate_title_similarity(normalized_title, existing_title) > 0.8 or 
                                existing.get('external_url') == external_url):
                                unique_topics[i] = topic
                                break
        
        return unique_topics

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using simple word overlap."""
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def filter_and_rank_topics(self, hours_back: int = 24, min_final_score: float = 0.3) -> List[Dict[str, Any]]:
        """Filter and rank all topics, returning top candidates for publishing."""
        topics = self.load_recent_topics(hours_back)
        
        if not topics:
            print("No topics found to rank")
            return []
            
        print(f"Loaded {len(topics)} topics from last {hours_back} hours")
        
        # Deduplicate topics by title and external URL
        deduplicated_topics = self._deduplicate_topics(topics)
        print(f"After deduplication: {len(deduplicated_topics)} unique topics")
        
        # Filter by basic thresholds
        filtered_topics = []
        for topic in deduplicated_topics:
            if (topic.get('score', 0) >= self.min_score_threshold and 
                topic.get('num_comments', 0) >= self.min_comments_threshold):
                filtered_topics.append(topic)
                
        print(f"Filtered to {len(filtered_topics)} topics meeting basic thresholds")
        
        # Rank remaining topics
        ranked_topics = []
        for topic in filtered_topics:
            final_score, score_breakdown = self.rank_topic(topic)
            
            if final_score >= min_final_score:
                topic['ranking_score'] = final_score
                topic['score_breakdown'] = score_breakdown
                ranked_topics.append(topic)
        
        # Sort by ranking score (highest first)
        ranked_topics.sort(key=lambda x: x['ranking_score'], reverse=True)
        
        print(f"Final ranked list: {len(ranked_topics)} topics above score threshold {min_final_score}")
        
        return ranked_topics

    def save_ranked_topics(self, ranked_topics: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """Save ranked topics to a JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ranked_topics_{timestamp}.json"
            
        output_path = os.path.join(self.output_dir, output_file)
        
        # Prepare output data
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "total_topics": len(ranked_topics),
            "ranking_criteria": {
                "min_score_threshold": self.min_score_threshold,
                "min_comments_threshold": self.min_comments_threshold,
                "weights": {
                    "engagement": 0.4,
                    "freshness": 0.2,
                    "monetization": 0.3,
                    "seo": 0.1
                }
            },
            "topics": ranked_topics
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        print(f"Ranked topics saved to: {output_path}")
        return output_path

def main():
    """Command line interface for topic ranking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Rank topics for publishing worthiness")
    parser.add_argument("--hours", type=int, default=24, help="Hours back to look for topics")
    parser.add_argument("--min-score", type=float, default=0.3, help="Minimum ranking score")
    parser.add_argument("--output-dir", default="../output", help="Output directory")
    parser.add_argument("--top-n", type=int, default=10, help="Show top N topics")
    
    args = parser.parse_args()
    
    ranker = TopicRanker(args.output_dir)
    ranked_topics = ranker.filter_and_rank_topics(args.hours, args.min_score)
    
    if not ranked_topics:
        print("No topics found matching criteria")
        return
        
    # Save full results
    output_file = ranker.save_ranked_topics(ranked_topics)
    
    # Display top results
    print(f"\n=== TOP {min(args.top_n, len(ranked_topics))} TOPICS ===")
    for i, topic in enumerate(ranked_topics[:args.top_n], 1):
        print(f"\n{i}. {topic['title']}")
        print(f"   Score: {topic['ranking_score']:.3f}")
        print(f"   Subreddit: r/{topic['subreddit']}")
        print(f"   Engagement: {topic['score']} upvotes, {topic['num_comments']} comments")
        print(f"   Breakdown: Eng:{topic['score_breakdown']['engagement']:.2f} "
              f"Fresh:{topic['score_breakdown']['freshness']:.2f} "
              f"Money:{topic['score_breakdown']['monetization']:.2f} "
              f"SEO:{topic['score_breakdown']['seo']:.2f}")

if __name__ == "__main__":
    main()

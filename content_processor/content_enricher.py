#!/usr/bin/env python3
"""
Content Enricher - Researches and fact-checks topics for publishing.

This module takes ranked topics and enriches them with:
- Source content fetching and analysis
- Fact-checking against multiple sources
- Related content discovery
- Citation generation
- Content quality assessment
"""

import json
import os
import sys
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin
import re
from html import unescape
import hashlib

class ContentEnricher:
    def __init__(self, output_dir: str = "../output"):
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'AI-Content-Farm-Research/1.0 (Educational Content Creation)'
        }
        self.request_delay = 1.0  # Delay between requests to be respectful
        
        # Common fact-checking and news sources for verification
        self.verification_sources = [
            "reuters.com",
            "apnews.com", 
            "bbc.com",
            "npr.org",
            "cnn.com",
            "techcrunch.com",
            "arstechnica.com",
            "theverge.com"
        ]

    def fetch_url_content(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """Fetch content from a URL with error handling."""
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            result = {
                'url': url,
                'status_code': response.status_code,
                'content_type': content_type,
                'success': True,
                'error': None,
                'title': None,
                'description': None,
                'content_preview': None,
                'word_count': 0,
                'domain': urlparse(url).netloc
            }
            
            if 'text/html' in content_type:
                # Basic HTML content extraction
                html_content = response.text
                result.update(self._extract_html_metadata(html_content))
                
            elif 'application/json' in content_type:
                # JSON content
                try:
                    json_data = response.json()
                    result['json_data'] = json_data
                    result['content_preview'] = str(json_data)[:500]
                except:
                    result['content_preview'] = response.text[:500]
            else:
                # Plain text or other
                result['content_preview'] = response.text[:500]
                result['word_count'] = len(response.text.split())
                
            return result
            
        except requests.RequestException as e:
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'status_code': None,
                'content_type': None,
                'domain': urlparse(url).netloc
            }

    def _extract_html_metadata(self, html_content: str) -> Dict[str, Any]:
        """Extract metadata from HTML content."""
        result = {
            'title': None,
            'description': None,
            'content_preview': None,
            'word_count': 0
        }
        
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            result['title'] = unescape(title_match.group(1).strip())
            
        # Extract meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        if desc_match:
            result['description'] = unescape(desc_match.group(1).strip())
            
        # Extract Open Graph description as fallback
        if not result['description']:
            og_desc_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
            if og_desc_match:
                result['description'] = unescape(og_desc_match.group(1).strip())
        
        # Extract main content (very basic - remove scripts, styles, etc.)
        content_clean = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        content_clean = re.sub(r'<style[^>]*>.*?</style>', '', content_clean, flags=re.DOTALL | re.IGNORECASE)
        content_clean = re.sub(r'<[^>]+>', ' ', content_clean)
        content_clean = re.sub(r'\s+', ' ', content_clean).strip()
        
        result['content_preview'] = content_clean[:1000]
        result['word_count'] = len(content_clean.split())
        
        return result

    def search_verification_sources(self, query: str, max_sources: int = 3) -> List[Dict[str, Any]]:
        """Search verification sources for related content."""
        verification_results = []
        
        # Simple approach: construct search URLs for major sources
        # In production, you'd use proper APIs
        search_engines = [
            f"https://www.google.com/search?q=site:reuters.com {query}",
            f"https://www.google.com/search?q=site:apnews.com {query}",
            f"https://www.google.com/search?q=site:bbc.com {query}"
        ]
        
        # For now, return placeholder verification data
        # In production, implement proper fact-checking API integration
        verification_results.append({
            'source': 'manual_verification_required',
            'query': query,
            'recommendation': 'Cross-reference with reputable news sources',
            'confidence': 'medium'
        })
        
        return verification_results

    def enrich_topic(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single topic with research and fact-checking."""
        print(f"Enriching: {topic['title']}")
        
        enriched_topic = topic.copy()
        enriched_topic['enrichment'] = {
            'processed_at': datetime.now().isoformat(),
            'external_content': None,
            'verification_checks': [],
            'related_sources': [],
            'content_quality': {},
            'citations': [],
            'research_notes': []
        }
        
        # Fetch external URL content if available
        external_url = topic.get('external_url')
        if external_url and not external_url.startswith('https://www.reddit.com'):
            print(f"  Fetching external content from: {external_url}")
            content_result = self.fetch_url_content(external_url)
            enriched_topic['enrichment']['external_content'] = content_result
            
            if content_result['success']:
                # Add citation
                citation = {
                    'type': 'primary_source',
                    'url': external_url,
                    'title': content_result.get('title', 'Source Article'),
                    'domain': content_result['domain'],
                    'accessed_date': datetime.now().strftime('%Y-%m-%d')
                }
                enriched_topic['enrichment']['citations'].append(citation)
                
                # Assess content quality
                quality_assessment = self._assess_content_quality(content_result)
                enriched_topic['enrichment']['content_quality'] = quality_assessment
                
            time.sleep(self.request_delay)  # Be respectful
            
        # Perform verification checks
        title_words = topic['title'].split()[:5]  # First 5 words for search
        search_query = ' '.join(title_words)
        verification_results = self.search_verification_sources(search_query)
        enriched_topic['enrichment']['verification_checks'] = verification_results
        
        # Add Reddit citation
        reddit_citation = {
            'type': 'discussion_source',
            'url': topic['reddit_url'],
            'title': f"Reddit Discussion: {topic['title']}",
            'domain': 'reddit.com',
            'subreddit': topic['subreddit'],
            'engagement': f"{topic['score']} upvotes, {topic['num_comments']} comments",
            'accessed_date': datetime.now().strftime('%Y-%m-%d')
        }
        enriched_topic['enrichment']['citations'].append(reddit_citation)
        
        # Add research notes
        enriched_topic['enrichment']['research_notes'] = [
            f"Topic trending on r/{topic['subreddit']} with {topic['score']} upvotes",
            f"Generated {topic['num_comments']} comments indicating community interest",
            "Requires manual fact-checking before publication",
            "Consider reaching out to original source for quotes or clarification"
        ]
        
        return enriched_topic

    def _assess_content_quality(self, content_result: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of fetched content."""
        quality = {
            'has_title': bool(content_result.get('title')),
            'has_description': bool(content_result.get('description')),
            'substantial_content': content_result.get('word_count', 0) > 200,
            'domain_credibility': self._assess_domain_credibility(content_result['domain']),
            'content_length': content_result.get('word_count', 0),
            'overall_score': 0.0
        }
        
        # Calculate overall quality score
        score = 0.0
        if quality['has_title']:
            score += 0.2
        if quality['has_description']:
            score += 0.2
        if quality['substantial_content']:
            score += 0.3
        score += quality['domain_credibility'] * 0.3
        
        quality['overall_score'] = score
        return quality

    def _assess_domain_credibility(self, domain: str) -> float:
        """Assess domain credibility (0.0 to 1.0)."""
        # High credibility domains
        high_credibility = [
            'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
            'techcrunch.com', 'arstechnica.com', 'theverge.com',
            'wired.com', 'ieee.org', 'acm.org', 'nature.com',
            'sciencemag.org', 'nih.gov', 'gov', 'edu'
        ]
        
        # Medium credibility domains
        medium_credibility = [
            'cnn.com', 'forbes.com', 'bloomberg.com', 'wsj.com',
            'guardian.co.uk', 'nytimes.com', 'washingtonpost.com'
        ]
        
        domain_lower = domain.lower()
        
        # Check high credibility
        for cred_domain in high_credibility:
            if cred_domain in domain_lower:
                return 1.0
                
        # Check medium credibility  
        for cred_domain in medium_credibility:
            if cred_domain in domain_lower:
                return 0.7
                
        # Check for edu/gov domains
        if domain_lower.endswith('.edu') or domain_lower.endswith('.gov'):
            return 1.0
            
        # Default medium-low credibility for unknown domains
        return 0.4

    def process_ranked_topics(self, ranked_topics_file: str) -> str:
        """Process a file of ranked topics and enrich them."""
        input_path = os.path.join(self.output_dir, ranked_topics_file)
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Ranked topics file not found: {input_path}")
            
        with open(input_path, 'r') as f:
            data = json.load(f)
            
        topics = data.get('topics', [])
        print(f"Processing {len(topics)} ranked topics for enrichment...")
        
        enriched_topics = []
        for i, topic in enumerate(topics, 1):
            print(f"\nProcessing {i}/{len(topics)}")
            enriched_topic = self.enrich_topic(topic)
            enriched_topics.append(enriched_topic)
            
        # Save enriched topics
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"enriched_topics_{timestamp}.json"
        output_path = os.path.join(self.output_dir, output_file)
        
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "source_file": ranked_topics_file,
            "total_topics": len(enriched_topics),
            "enrichment_process": {
                "external_content_fetched": sum(1 for t in enriched_topics if t['enrichment']['external_content']),
                "verification_checks_performed": len(enriched_topics),
                "citations_generated": sum(len(t['enrichment']['citations']) for t in enriched_topics)
            },
            "topics": enriched_topics
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
            
        print(f"\nEnriched topics saved to: {output_path}")
        return output_path

def main():
    """Command line interface for content enrichment."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich ranked topics with research and fact-checking")
    parser.add_argument("ranked_file", help="Ranked topics JSON file to process")
    parser.add_argument("--output-dir", default="../output", help="Output directory")
    
    args = parser.parse_args()
    
    enricher = ContentEnricher(args.output_dir)
    output_file = enricher.process_ranked_topics(args.ranked_file)
    
    print(f"\nContent enrichment complete. Output: {output_file}")

if __name__ == "__main__":
    main()

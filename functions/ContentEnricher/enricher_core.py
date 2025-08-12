"""
ContentEnricher Core Logic - Pure functional implementation for content enrichment.

This module provides pure functions for:
- External content fetching and analysis
- Fact-checking and verification research
- Citation generation and content quality assessment
- Related content discovery

All functions are stateless and thread-safe for Azure Functions scalability.
"""

import json
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import re
from html import unescape
import logging


# Configuration constants
REQUEST_TIMEOUT = 10
REQUEST_DELAY = 1.0  # Respectful delay between requests
MAX_CONTENT_PREVIEW = 1000
MAX_RETRIES = 2

# Credibility scoring for domains
HIGH_CREDIBILITY_DOMAINS = [
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
    'techcrunch.com', 'arstechnica.com', 'theverge.com',
    'wired.com', 'ieee.org', 'acm.org', 'nature.com',
    'sciencemag.org', 'nih.gov'
]

MEDIUM_CREDIBILITY_DOMAINS = [
    'cnn.com', 'forbes.com', 'bloomberg.com', 'wsj.com',
    'guardian.co.uk', 'nytimes.com', 'washingtonpost.com',
    'engadget.com', 'mashable.com', 'venturebeat.com'
]

VERIFICATION_SOURCES = [
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org'
]

# Research sources for finding related content
RESEARCH_SOURCES = [
    'reuters.com', 'apnews.com', 'bbc.com', 'npr.org',
    'techcrunch.com', 'arstechnica.com', 'theverge.com',
    'wired.com', 'engadget.com', 'venturebeat.com',
    'cnn.com', 'forbes.com', 'bloomberg.com',
    'guardian.co.uk', 'nytimes.com', 'washingtonpost.com'
]

# Search engines for finding related articles
SEARCH_ENGINES = {
    'duckduckgo': 'https://duckduckgo.com/html/?q={}',
    'bing': 'https://www.bing.com/search?q={}',
    'google': 'https://www.google.com/search?q={}'
}


def assess_domain_credibility(domain: str) -> float:
    """
    Assess domain credibility score (0.0 to 1.0).

    Args:
        domain: Domain name to assess

    Returns:
        Credibility score between 0.0 and 1.0
    """
    domain_lower = domain.lower()

    # High credibility domains
    for cred_domain in HIGH_CREDIBILITY_DOMAINS:
        if cred_domain in domain_lower:
            return 1.0

    # Medium credibility domains
    for cred_domain in MEDIUM_CREDIBILITY_DOMAINS:
        if cred_domain in domain_lower:
            return 0.7

    # Government and education domains
    if domain_lower.endswith('.edu') or domain_lower.endswith('.gov'):
        return 1.0

    # Default medium-low credibility for unknown domains
    return 0.4


def extract_search_keywords(topic_title: str, max_keywords: int = 5) -> List[str]:
    """
    Extract key search terms from topic title for finding related sources.

    Args:
        topic_title: Original topic title
        max_keywords: Maximum number of keywords to extract

    Returns:
        List of search keywords
    """
    # Remove common stop words and extract meaningful terms
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
    }

    # Clean and tokenize title
    title_clean = re.sub(r'[^\w\s]', ' ', topic_title.lower())
    words = [word.strip()
             for word in title_clean.split() if len(word.strip()) > 2]

    # Filter out stop words and get meaningful keywords
    keywords = [word for word in words if word not in stop_words]

    # Prioritize longer words and limit to max_keywords
    keywords.sort(key=len, reverse=True)
    return keywords[:max_keywords]


def search_related_sources(topic_title: str, max_sources: int = 3) -> List[Dict[str, Any]]:
    """
    Search for related sources and articles about the topic.

    Args:
        topic_title: Topic title to search for
        max_sources: Maximum number of related sources to find

    Returns:
        List of related source information
    """
    keywords = extract_search_keywords(topic_title)
    search_query = ' '.join(keywords[:3])  # Use top 3 keywords

    related_sources = []

    # Strategy 1: Search high-credibility news sources
    for source_domain in RESEARCH_SOURCES[:max_sources]:
        search_url = f"https://www.google.com/search?q=site:{source_domain} {search_query}"

        related_source = {
            'search_query': f'site:{source_domain} {search_query}',
            'domain': source_domain,
            'credibility_score': assess_domain_credibility(source_domain),
            'search_url': search_url,
            'type': 'domain_specific_search',
            'keywords': keywords[:3],
            'recommendation': f'Search {source_domain} for additional perspectives on: {search_query}'
        }
        related_sources.append(related_source)

        if len(related_sources) >= max_sources:
            break

    return related_sources


def perform_fact_checking_research(topic_title: str, external_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Perform comprehensive fact-checking research for a topic.

    Args:
        topic_title: Topic title to fact-check
        external_url: Original external URL if available

    Returns:
        List of fact-checking recommendations and strategies
    """
    keywords = extract_search_keywords(topic_title)
    fact_checks = []

    # Strategy 1: Cross-reference with high-credibility sources
    for source in VERIFICATION_SOURCES:
        fact_check = {
            'type': 'cross_reference',
            'source': source,
            'search_query': f'site:{source} {" ".join(keywords[:3])}',
            'credibility_score': assess_domain_credibility(source),
            'priority': 'high',
            'action': f'Search {source} for independent coverage of this topic',
            'verification_method': 'compare_claims_and_facts'
        }
        fact_checks.append(fact_check)

    # Strategy 2: Check for contradictory information
    contradiction_search = {
        'type': 'contradiction_check',
        'search_query': f'"{keywords[0]}" debunked OR disputed OR false OR incorrect',
        'priority': 'high',
        'action': 'Search for contradictory information or debunking articles',
        'verification_method': 'identify_disputes_or_corrections'
    }
    fact_checks.append(contradiction_search)

    # Strategy 3: Source verification if external URL provided
    if external_url:
        domain = urlparse(external_url).netloc
        source_check = {
            'type': 'source_verification',
            'original_domain': domain,
            'credibility_score': assess_domain_credibility(domain),
            'priority': 'medium',
            'action': f'Verify credibility and track record of {domain}',
            'verification_method': 'assess_source_reliability_and_bias'
        }
        fact_checks.append(source_check)

    # Strategy 4: Timeline and recency check
    timeline_check = {
        'type': 'timeline_verification',
        'search_query': f'"{keywords[0]}" recent news latest update',
        'priority': 'medium',
        'action': 'Verify information is current and check for updates',
        'verification_method': 'confirm_information_currency'
    }
    fact_checks.append(timeline_check)

    return fact_checks


def generate_research_strategy(topic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive research strategy for the topic.

    Args:
        topic: Topic data from ranked topics

    Returns:
        Research strategy with multiple investigation approaches
    """
    title = topic['title']
    external_url = topic.get('external_url')
    subreddit = topic.get('subreddit', 'unknown')

    keywords = extract_search_keywords(title)

    strategy = {
        'primary_keywords': keywords[:3],
        'secondary_keywords': keywords[3:5] if len(keywords) > 3 else [],
        'research_approaches': {
            'multi_source_verification': search_related_sources(title, max_sources=4),
            'fact_checking': perform_fact_checking_research(title, external_url),
            'perspective_diversity': generate_perspective_sources(keywords, subreddit),
            'expert_sources': identify_expert_sources(keywords)
        },
        'quality_thresholds': {
            'minimum_sources': 3,
            'required_high_credibility': 2,
            'fact_check_methods': 4
        }
    }

    return strategy


def generate_perspective_sources(keywords: List[str], subreddit: str) -> List[Dict[str, Any]]:
    """
    Generate sources for different perspectives on the topic.

    Args:
        keywords: Search keywords
        subreddit: Original subreddit context

    Returns:
        List of perspective source recommendations
    """
    perspectives = []

    # Industry perspective
    if subreddit in ['technology', 'programming', 'MachineLearning']:
        perspectives.extend([
            {
                'type': 'industry_analysis',
                'sources': ['techcrunch.com', 'arstechnica.com', 'theverge.com'],
                'search_focus': f'{" ".join(keywords[:2])} industry impact analysis',
                'perspective': 'Technical and business implications'
            },
            {
                'type': 'academic_research',
                'sources': ['ieee.org', 'acm.org', 'arxiv.org'],
                'search_focus': f'{" ".join(keywords[:2])} research papers studies',
                'perspective': 'Scientific and academic analysis'
            }
        ])

    # News and policy perspective
    perspectives.append({
        'type': 'news_coverage',
        'sources': ['reuters.com', 'bbc.com', 'apnews.com'],
        'search_focus': f'{" ".join(keywords[:2])} news coverage',
        'perspective': 'Mainstream news and policy implications'
    })

    # Alternative viewpoints
    perspectives.append({
        'type': 'alternative_viewpoints',
        'sources': ['guardian.co.uk', 'washingtonpost.com', 'nytimes.com'],
        'search_focus': f'{" ".join(keywords[:2])} opinion analysis criticism',
        'perspective': 'Editorial and critical analysis'
    })

    return perspectives


def identify_expert_sources(keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Identify potential expert sources and authorities on the topic.

    Args:
        keywords: Topic keywords

    Returns:
        List of expert source recommendations
    """
    experts = []

    # Technology experts
    if any(tech_word in ' '.join(keywords).lower()
           for tech_word in ['ai', 'artificial', 'intelligence', 'tech', 'software', 'computer']):
        experts.extend([
            {
                'type': 'tech_authority',
                'search_focus': f'{" ".join(keywords[:2])} expert opinion researcher',
                'authority_types': ['university researchers', 'industry leaders', 'policy experts'],
                'verification_method': 'check_credentials_and_publications'
            }
        ])

    # Government and policy experts
    if any(policy_word in ' '.join(keywords).lower()
           for policy_word in ['law', 'policy', 'government', 'regulation', 'bill']):
        experts.extend([
            {
                'type': 'policy_authority',
                'search_focus': f'{" ".join(keywords[:2])} policy expert legal analysis',
                'authority_types': ['legal experts', 'policy researchers', 'government officials'],
                'verification_method': 'verify_official_positions_and_qualifications'
            }
        ])

    return experts
    """
    Assess domain credibility score (0.0 to 1.0).
    
    Args:
        domain: Domain name to assess
        
    Returns:
        Credibility score between 0.0 and 1.0
    """
    domain_lower = domain.lower()

    # High credibility domains
    for cred_domain in HIGH_CREDIBILITY_DOMAINS:
        if cred_domain in domain_lower:
            return 1.0

    # Medium credibility domains
    for cred_domain in MEDIUM_CREDIBILITY_DOMAINS:
        if cred_domain in domain_lower:
            return 0.7

    # Government and education domains
    if domain_lower.endswith('.edu') or domain_lower.endswith('.gov'):
        return 1.0

    # Default medium-low credibility for unknown domains
    return 0.4


def extract_html_metadata(html_content: str) -> Dict[str, Any]:
    """
    Extract metadata from HTML content.

    Args:
        html_content: Raw HTML content

    Returns:
        Dictionary with extracted metadata
    """
    result = {
        'title': None,
        'description': None,
        'content_preview': None,
        'word_count': 0
    }

    # Extract title
    title_match = re.search(
        r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    if title_match:
        result['title'] = unescape(title_match.group(1).strip())

    # Extract meta description
    desc_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
        html_content,
        re.IGNORECASE
    )
    if desc_match:
        result['description'] = unescape(desc_match.group(1).strip())

    # Extract Open Graph description as fallback
    if not result['description']:
        og_desc_match = re.search(
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']',
            html_content,
            re.IGNORECASE
        )
        if og_desc_match:
            result['description'] = unescape(og_desc_match.group(1).strip())

    # Clean content (remove scripts, styles, tags)
    content_clean = re.sub(
        r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    content_clean = re.sub(
        r'<style[^>]*>.*?</style>', '', content_clean, flags=re.DOTALL | re.IGNORECASE)
    content_clean = re.sub(r'<[^>]+>', ' ', content_clean)
    content_clean = re.sub(r'\s+', ' ', content_clean).strip()

    result['content_preview'] = content_clean[:MAX_CONTENT_PREVIEW]
    result['word_count'] = len(content_clean.split())

    return result


def fetch_external_content(url: str) -> Dict[str, Any]:
    """
    Fetch and analyze external content from URL.

    Args:
        url: URL to fetch content from

    Returns:
        Dictionary with content analysis results
    """
    headers = {
        'User-Agent': 'AI-Content-Farm-Research/1.0 (Educational Content Creation)'
    }

    result = {
        'url': url,
        'domain': urlparse(url).netloc,
        'success': False,
        'error': None,
        'status_code': None,
        'content_type': None,
        'title': None,
        'description': None,
        'content_preview': None,
        'word_count': 0,
        'credibility_score': 0.0
    }

    # Assess domain credibility first
    result['credibility_score'] = assess_domain_credibility(result['domain'])

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        result['success'] = True
        result['status_code'] = response.status_code
        result['content_type'] = response.headers.get(
            'content-type', '').lower()

        # Process HTML content
        if 'text/html' in result['content_type']:
            metadata = extract_html_metadata(response.text)
            result.update(metadata)

        elif 'application/json' in result['content_type']:
            # Handle JSON content
            try:
                json_data = response.json()
                result['content_preview'] = str(
                    json_data)[:MAX_CONTENT_PREVIEW]
                result['word_count'] = len(str(json_data).split())
            except:
                result['content_preview'] = response.text[:MAX_CONTENT_PREVIEW]

        else:
            # Handle plain text or other content
            result['content_preview'] = response.text[:MAX_CONTENT_PREVIEW]
            result['word_count'] = len(response.text.split())

    except requests.RequestException as e:
        result['error'] = str(e)
        logging.warning(f"Failed to fetch {url}: {e}")

    return result


def assess_content_quality(content_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess the quality of fetched content.

    Args:
        content_result: Result from fetch_external_content

    Returns:
        Quality assessment metrics
    """
    quality = {
        'has_title': bool(content_result.get('title')),
        'has_description': bool(content_result.get('description')),
        'substantial_content': content_result.get('word_count', 0) > 200,
        'domain_credibility': content_result.get('credibility_score', 0.0),
        'content_length': content_result.get('word_count', 0),
        'accessible': content_result.get('success', False),
        'overall_score': 0.0
    }

    # Calculate overall quality score
    score = 0.0
    if quality['accessible']:
        score += 0.2
    if quality['has_title']:
        score += 0.15
    if quality['has_description']:
        score += 0.15
    if quality['substantial_content']:
        score += 0.2
    score += quality['domain_credibility'] * 0.3

    quality['overall_score'] = round(score, 2)
    return quality


def generate_citations(topic: Dict[str, Any], external_content: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate proper citations for topic sources.

    Args:
        topic: Original topic data
        external_content: External content analysis result

    Returns:
        List of citation objects
    """
    citations = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Add Reddit citation
    reddit_citation = {
        'type': 'discussion_source',
        'url': topic['reddit_url'],
        'title': f"Reddit Discussion: {topic['title']}",
        'domain': 'reddit.com',
        'subreddit': topic['subreddit'],
        'engagement': f"{topic['score']} upvotes, {topic['num_comments']} comments",
        'accessed_date': current_date
    }
    citations.append(reddit_citation)

    # Add external source citation if available and successful
    if external_content and external_content.get('success'):
        external_citation = {
            'type': 'primary_source',
            'url': external_content['url'],
            'title': external_content.get('title', 'Source Article'),
            'domain': external_content['domain'],
            'credibility_score': external_content['credibility_score'],
            'accessed_date': current_date
        }
        citations.append(external_citation)

    return citations


def generate_verification_checks(topic_title: str) -> List[Dict[str, Any]]:
    """
    Generate verification check recommendations for fact-checking.

    Args:
        topic_title: Title of the topic to verify

    Returns:
        List of verification check recommendations
    """
    # Extract key terms from title for verification
    title_words = topic_title.lower().split()[:6]  # First 6 words
    search_query = ' '.join(title_words)

    verification_checks = [
        {
            'type': 'manual_verification',
            'query': search_query,
            'recommended_sources': VERIFICATION_SOURCES,
            'priority': 'high' if any(word in title_words for word in ['breaking', 'urgent', 'exclusive']) else 'medium',
            'notes': 'Cross-reference with reputable news sources before publication'
        },
        {
            'type': 'source_credibility',
            'action': 'verify_original_source',
            'priority': 'high',
            'notes': 'Ensure external source is reputable and information is current'
        }
    ]

    return verification_checks


def generate_research_notes(topic: Dict[str, Any], external_content: Optional[Dict[str, Any]], quality: Dict[str, Any]) -> List[str]:
    """
    Generate research notes for editorial review.

    Args:
        topic: Original topic data
        external_content: External content analysis result
        quality: Content quality assessment

    Returns:
        List of research notes
    """
    notes = []

    # Reddit engagement note
    notes.append(
        f"Topic trending on r/{topic['subreddit']} with {topic['score']} upvotes and {topic['num_comments']} comments")

    # External source quality note
    if external_content:
        if external_content.get('success'):
            credibility = external_content.get('credibility_score', 0)
            if credibility >= 0.8:
                notes.append(
                    f"High-credibility source ({external_content['domain']}) - {credibility:.1f}/1.0 credibility score")
            elif credibility >= 0.6:
                notes.append(
                    f"Medium-credibility source ({external_content['domain']}) - verify claims independently")
            else:
                notes.append(
                    f"Low-credibility source ({external_content['domain']}) - requires additional verification")

            if external_content.get('word_count', 0) < 200:
                notes.append(
                    "Limited content available from external source - may need additional research")
        else:
            notes.append(
                f"External source unavailable ({external_content.get('error', 'unknown error')}) - content may be outdated")

    # Content quality recommendation
    if quality['overall_score'] < 0.5:
        notes.append(
            "LOW QUALITY ALERT: Consider additional sources before publication")

    # Standard editorial notes
    notes.extend([
        "Requires manual fact-checking before publication",
        "Consider reaching out to original source for quotes or clarification",
        "Verify all claims against multiple reputable sources"
    ])

    return notes


def enrich_single_topic(topic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a single topic with comprehensive multi-source research and fact-checking.

    Args:
        topic: Single topic data from ranked topics

    Returns:
        Enriched topic with multi-source research data
    """
    logging.info(f"Enriching topic: {topic['title'][:50]}...")

    enriched_topic = topic.copy()
    external_content = None

    # Step 1: Fetch original external content if available
    external_url = topic.get('external_url')
    if external_url and not external_url.startswith('https://www.reddit.com'):
        logging.info(f"Fetching original external content: {external_url}")
        external_content = fetch_external_content(external_url)
        time.sleep(REQUEST_DELAY)  # Be respectful to external servers

    # Step 2: Generate comprehensive research strategy
    logging.info("Generating multi-source research strategy...")
    research_strategy = generate_research_strategy(topic)

    # Step 3: Assess content quality of original source
    quality_assessment = assess_content_quality(external_content) if external_content else {
        'overall_score': 0.3,  # Low score for topics without external sources
        'accessible': False,
        'has_title': False,
        'has_description': False,
        'substantial_content': False,
        'domain_credibility': 0.0,
        'content_length': 0
    }

    # Step 4: Generate citations (original + research recommendations)
    citations = generate_citations(topic, external_content)

    # Step 5: Enhanced verification checks with multi-source approach
    verification_checks = generate_enhanced_verification_checks(
        topic, research_strategy)

    # Step 6: Generate comprehensive research notes
    research_notes = generate_comprehensive_research_notes(
        topic, external_content, quality_assessment, research_strategy)

    # Add comprehensive enrichment data
    enriched_topic['enrichment_data'] = {
        'processed_at': datetime.now().isoformat(),
        'original_source': external_content,
        'content_quality': quality_assessment,
        'research_strategy': research_strategy,
        'citations': citations,
        'verification_checks': verification_checks,
        'research_notes': research_notes,
        'multi_source_recommendations': {
            'related_sources': research_strategy['research_approaches']['multi_source_verification'],
            'fact_checking_methods': research_strategy['research_approaches']['fact_checking'],
            'perspective_sources': research_strategy['research_approaches']['perspective_diversity'],
            'expert_sources': research_strategy['research_approaches']['expert_sources']
        }
    }

    return enriched_topic


def generate_enhanced_verification_checks(topic: Dict[str, Any], research_strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate enhanced verification checks using multi-source research strategy.

    Args:
        topic: Topic data
        research_strategy: Generated research strategy

    Returns:
        Enhanced verification check recommendations
    """
    title = topic['title']
    checks = []

    # Original verification checks
    original_checks = generate_verification_checks(title)
    checks.extend(original_checks)

    # Multi-source verification checks
    related_sources = research_strategy['research_approaches']['multi_source_verification']
    for source_info in related_sources[:3]:  # Top 3 sources
        check = {
            'type': 'multi_source_verification',
            'source_domain': source_info['domain'],
            'search_query': source_info['search_query'],
            'credibility_score': source_info['credibility_score'],
            'priority': 'high' if source_info['credibility_score'] >= 0.8 else 'medium',
            'action': f"Search {source_info['domain']} for independent coverage",
            'verification_method': 'cross_reference_claims_and_facts'
        }
        checks.append(check)

    # Fact-checking strategy checks
    fact_checks = research_strategy['research_approaches']['fact_checking']
    for fact_check in fact_checks[:2]:  # Top 2 fact-checking strategies
        checks.append(fact_check)

    return checks


def generate_comprehensive_research_notes(
    topic: Dict[str, Any],
    external_content: Optional[Dict[str, Any]],
    quality: Dict[str, Any],
    research_strategy: Dict[str, Any]
) -> List[str]:
    """
    Generate comprehensive research notes with multi-source recommendations.

    Args:
        topic: Original topic data
        external_content: External content analysis result
        quality: Content quality assessment
        research_strategy: Multi-source research strategy

    Returns:
        Comprehensive list of research notes
    """
    notes = []

    # Reddit engagement analysis
    notes.append(
        f"Topic trending on r/{topic['subreddit']} with {topic['score']} upvotes and {topic['num_comments']} comments")

    # Original source analysis
    if external_content:
        if external_content.get('success'):
            credibility = external_content.get('credibility_score', 0)
            if credibility >= 0.8:
                notes.append(
                    f"HIGH-CREDIBILITY original source ({external_content['domain']}) - {credibility:.1f}/1.0 credibility score")
            elif credibility >= 0.6:
                notes.append(
                    f"MEDIUM-CREDIBILITY original source ({external_content['domain']}) - verify claims independently")
            else:
                notes.append(
                    f"LOW-CREDIBILITY original source ({external_content['domain']}) - requires additional verification")

            if external_content.get('word_count', 0) < 200:
                notes.append(
                    "LIMITED CONTENT from original source - requires additional research")
        else:
            notes.append(
                f"ORIGINAL SOURCE UNAVAILABLE ({external_content.get('error', 'unknown error')}) - content may be outdated")
    else:
        notes.append(
            "NO EXTERNAL SOURCE - Reddit discussion only, requires independent research")

    # Multi-source research recommendations
    keywords = research_strategy['primary_keywords']
    notes.append(f"KEY RESEARCH TERMS: {', '.join(keywords)}")

    # High-credibility source recommendations
    high_cred_sources = [s for s in research_strategy['research_approaches']['multi_source_verification']
                         if s['credibility_score'] >= 0.8]
    if high_cred_sources:
        source_list = ', '.join([s['domain'] for s in high_cred_sources[:3]])
        notes.append(f"RECOMMENDED HIGH-CREDIBILITY SOURCES: {source_list}")

    # Perspective diversity recommendations
    perspectives = research_strategy['research_approaches']['perspective_diversity']
    if perspectives:
        perspective_types = [p['perspective'] for p in perspectives]
        notes.append(
            f"MULTIPLE PERSPECTIVES NEEDED: {'; '.join(perspective_types[:2])}")

    # Expert source recommendations
    expert_sources = research_strategy['research_approaches']['expert_sources']
    if expert_sources:
        expert_types = [e['type'] for e in expert_sources]
        notes.append(f"EXPERT SOURCES RECOMMENDED: {'; '.join(expert_types)}")

    # Content quality recommendations
    if quality['overall_score'] < 0.5:
        notes.append(
            "⚠️ LOW QUALITY ALERT: Additional sources REQUIRED before publication")
    elif quality['overall_score'] < 0.7:
        notes.append(
            "MODERATE QUALITY: Recommend 2-3 additional sources for verification")
    else:
        notes.append(
            "GOOD QUALITY: Verify key claims with 1-2 additional sources")

    # Fact-checking priorities
    fact_check_priorities = [fc for fc in research_strategy['research_approaches']['fact_checking']
                             if fc.get('priority') == 'high']
    if fact_check_priorities:
        notes.append(
            f"HIGH PRIORITY FACT-CHECKING: {len(fact_check_priorities)} critical verification methods required")

    # Standard editorial requirements
    notes.extend([
        "EDITORIAL CHECKLIST: Verify all claims against multiple reputable sources",
        "FACT-CHECK STATUS: Manual verification required before publication",
        "RESEARCH COMPLETENESS: Follow multi-source strategy for comprehensive coverage"
    ])

    return notes


def process_content_enrichment(ranked_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process ranked topics for comprehensive multi-source content enrichment.

    Args:
        ranked_data: Ranked topics data from ContentRanker

    Returns:
        Enriched topics data with multi-source research following API contract
    """
    logging.info(
        f"Starting multi-source content enrichment for {len(ranked_data.get('topics', []))} topics")

    topics = ranked_data.get('topics', [])
    enriched_topics = []

    for i, topic in enumerate(topics, 1):
        logging.info(
            f"Processing topic {i}/{len(topics)} with multi-source research")
        enriched_topic = enrich_single_topic(topic)
        enriched_topics.append(enriched_topic)

    # Calculate enhanced statistics
    stats = {
        'total_topics': len(enriched_topics),
        'original_sources_fetched': sum(1 for t in enriched_topics
                                        if t['enrichment_data']['original_source'] and
                                        t['enrichment_data']['original_source']['success']),
        'high_quality_sources': sum(1 for t in enriched_topics
                                    if t['enrichment_data']['content_quality']['overall_score'] > 0.7),
        'multi_source_strategies_generated': len(enriched_topics),
        'related_sources_identified': sum(len(t['enrichment_data']['multi_source_recommendations']['related_sources'])
                                          for t in enriched_topics),
        'fact_checking_methods': sum(len(t['enrichment_data']['multi_source_recommendations']['fact_checking_methods'])
                                     for t in enriched_topics),
        'verification_checks_created': sum(len(t['enrichment_data']['verification_checks']) for t in enriched_topics),
        'citations_generated': sum(len(t['enrichment_data']['citations']) for t in enriched_topics),
        'research_notes_created': sum(len(t['enrichment_data']['research_notes']) for t in enriched_topics)
    }

    # Build result following API contract with enhanced data
    result = {
        'generated_at': datetime.now().isoformat(),
        'source_file': ranked_data.get('source_files', ['unknown'])[0] if ranked_data.get('source_files') else 'unknown',
        'total_topics': stats['total_topics'],
        'enrichment_type': 'multi_source_research_and_fact_checking',
        'enrichment_statistics': stats,
        'topics': enriched_topics
    }

    logging.info(f"Multi-source content enrichment completed: {stats}")
    return result

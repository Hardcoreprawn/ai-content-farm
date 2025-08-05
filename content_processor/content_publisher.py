#!/usr/bin/env python3
"""
Content Publisher - Generates polished markdown content for JAMStack site.

This module takes enriched topics and generates publication-ready content:
- SEO-optimized markdown articles
- Proper citations and attribution
- Monetization-friendly formatting
- Meta tags and frontmatter
- Related content suggestions
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import re
import hashlib
from urllib.parse import quote

class ContentPublisher:
    def __init__(self, output_dir: str = "../output", site_dir: str = "../site"):
        self.output_dir = output_dir
        self.site_dir = site_dir
        self.content_dir = os.path.join(site_dir, "content", "articles")
        
        # Ensure directories exist
        os.makedirs(self.content_dir, exist_ok=True)

    def generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')
        
        # Limit length
        if len(slug) > 60:
            slug = slug[:60].rsplit('-', 1)[0]
            
        return slug

    def generate_excerpt(self, content: str, max_length: int = 150) -> str:
        """Generate article excerpt for SEO and previews."""
        # Remove markdown and extra whitespace
        text = re.sub(r'[#*_`\[\]()]', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) <= max_length:
            return text
            
        # Find last complete sentence within limit
        excerpt = text[:max_length]
        last_period = excerpt.rfind('.')
        if last_period > max_length * 0.7:  # If period is reasonably close to end
            return excerpt[:last_period + 1]
        else:
            return excerpt + "..."

    def estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (average 200 words per minute)."""
        word_count = len(content.split())
        return max(1, round(word_count / 200))

    def _deduplicate_for_publishing(self, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate topics before publishing based on title and URL similarity."""
        unique_topics = []
        seen_slugs = set()
        seen_urls = set()
        
        for topic in topics:
            title = topic.get('title', '')
            external_url = topic.get('external_url', '')
            
            # Generate slug for this topic
            slug = self.generate_slug(title)
            
            # Check for duplicates
            if slug in seen_slugs:
                print(f"  Duplicate slug detected: {slug}")
                continue
                
            if external_url and external_url in seen_urls:
                print(f"  Duplicate URL detected: {external_url}")
                continue
                
            # Add to unique list
            unique_topics.append(topic)
            seen_slugs.add(slug)
            if external_url:
                seen_urls.add(external_url)
                
        return unique_topics

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two article contents using word overlap."""
        # Extract just the main content (skip frontmatter)
        def extract_content(text):
            lines = text.split('\n')
            in_frontmatter = False
            content_lines = []
            frontmatter_end_count = 0
            
            for line in lines:
                if line.strip() == '---':
                    frontmatter_end_count += 1
                    if frontmatter_end_count == 2:
                        in_frontmatter = False
                        continue
                    in_frontmatter = True
                    continue
                    
                if not in_frontmatter and line.strip():
                    content_lines.append(line.strip().lower())
                    
            return ' '.join(content_lines)
        
        content1_clean = extract_content(content1)
        content2_clean = extract_content(content2)
        
        # Simple word-based similarity
        words1 = set(content1_clean.split())
        words2 = set(content2_clean.split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    def cleanup_duplicate_articles(self, similarity_threshold: float = 0.8, dry_run: bool = False) -> Dict[str, Any]:
        """Remove duplicate or highly similar articles from the content directory."""
        if not os.path.exists(self.content_dir):
            return {"status": "no_content_dir", "removed": [], "kept": []}
            
        # Get all markdown files
        article_files = [f for f in os.listdir(self.content_dir) if f.endswith('.md')]
        
        if len(article_files) < 2:
            return {"status": "insufficient_articles", "removed": [], "kept": article_files}
            
        print(f"Analyzing {len(article_files)} articles for duplicates...")
        
        articles_data = []
        
        # Read all articles and extract metadata
        for filename in article_files:
            filepath = os.path.join(self.content_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract title from frontmatter
                title_match = re.search(r'title:\s*["\']([^"\']*)["\']', content)
                title = title_match.group(1) if title_match else filename
                
                # Extract slug
                slug_match = re.search(r'slug:\s*["\']([^"\']*)["\']', content)
                slug = slug_match.group(1) if slug_match else self.generate_slug(title)
                
                # Get file stats
                stat = os.stat(filepath)
                
                articles_data.append({
                    'filename': filename,
                    'filepath': filepath,
                    'title': title,
                    'slug': slug,
                    'content': content,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'keep': True  # Default to keeping
                })
                
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
        
        # Find duplicates
        removed_files = []
        kept_files = []
        
        for i, article1 in enumerate(articles_data):
            if not article1['keep']:
                continue
                
            for j, article2 in enumerate(articles_data[i+1:], i+1):
                if not article2['keep']:
                    continue
                    
                # Check slug similarity (exact match)
                if article1['slug'] == article2['slug']:
                    print(f"Found exact slug match: {article1['slug']}")
                    # Keep the more recent one
                    if article1['modified'] > article2['modified']:
                        article2['keep'] = False
                        print(f"  Removing older: {article2['filename']}")
                    else:
                        article1['keep'] = False
                        print(f"  Removing older: {article1['filename']}")
                        break
                    continue
                
                # Check content similarity
                similarity = self._calculate_content_similarity(article1['content'], article2['content'])
                
                if similarity >= similarity_threshold:
                    print(f"Found similar articles ({similarity:.2f} similarity):")
                    print(f"  1: {article1['filename']} - {article1['title'][:50]}...")
                    print(f"  2: {article2['filename']} - {article2['title'][:50]}...")
                    
                    # Keep the one with more content or more recent
                    if article1['size'] > article2['size']:
                        article2['keep'] = False
                        print(f"  Keeping larger article: {article1['filename']}")
                    elif article2['size'] > article1['size']:
                        article1['keep'] = False
                        print(f"  Keeping larger article: {article2['filename']}")
                        break
                    else:
                        # Same size, keep more recent
                        if article1['modified'] > article2['modified']:
                            article2['keep'] = False
                            print(f"  Keeping more recent: {article1['filename']}")
                        else:
                            article1['keep'] = False
                            print(f"  Keeping more recent: {article2['filename']}")
                            break
        
        # Process removal/keeping
        for article in articles_data:
            if article['keep']:
                kept_files.append(article['filename'])
            else:
                removed_files.append(article['filename'])
                if not dry_run:
                    try:
                        os.remove(article['filepath'])
                        print(f"Removed: {article['filename']}")
                    except Exception as e:
                        print(f"Error removing {article['filename']}: {e}")
                else:
                    print(f"Would remove: {article['filename']} (dry run)")
        
        result = {
            "status": "completed",
            "total_analyzed": len(article_files),
            "removed": removed_files,
            "kept": kept_files,
            "similarity_threshold": similarity_threshold,
            "dry_run": dry_run
        }
        
        print(f"\nDuplicate cleanup completed:")
        print(f"  Analyzed: {len(article_files)} articles")
        print(f"  Removed: {len(removed_files)} duplicates")
        print(f"  Kept: {len(kept_files)} unique articles")
        
        return result

    def generate_tags(self, topic: Dict[str, Any]) -> List[str]:
        """Generate relevant tags for the article."""
        tags = []
        
        # Add subreddit as tag
        subreddit = topic.get('subreddit', '')
        if subreddit:
            tags.append(subreddit)
            
        # Extract tags from title
        title = topic.get('title', '').lower()
        
        # Technology-related tags
        tech_keywords = {
            'ai': 'artificial-intelligence',
            'artificial intelligence': 'artificial-intelligence', 
            'machine learning': 'machine-learning',
            'crypto': 'cryptocurrency',
            'bitcoin': 'cryptocurrency',
            'blockchain': 'blockchain',
            'startup': 'startups',
            'tech': 'technology',
            'software': 'software',
            'app': 'mobile-apps',
            'gaming': 'gaming',
            'security': 'cybersecurity'
        }
        
        for keyword, tag in tech_keywords.items():
            if keyword in title:
                tags.append(tag)
                
        # Remove duplicates and limit to 5 tags
        tags = list(dict.fromkeys(tags))[:5]
        
        return tags

    def generate_frontmatter(self, topic: Dict[str, Any], content: str, slug: str) -> str:
        """Generate YAML frontmatter for the article."""
        title = topic.get('title', 'Untitled')
        
        # Escape title for YAML
        title_escaped = title.replace('"', '\\"')
        
        excerpt = self.generate_excerpt(content)
        tags = self.generate_tags(topic)
        reading_time = self.estimate_reading_time(content)
        
        # Get publish date (use created_utc if available, otherwise now)
        created_utc = topic.get('created_utc')
        if created_utc:
            publish_date = datetime.fromtimestamp(created_utc)
        else:
            publish_date = datetime.now()
            
        # Generate SEO-friendly meta description
        meta_description = self.generate_excerpt(content, 160)
        
        reddit_url = topic.get('reddit_url', '')
        subreddit = topic.get('subreddit', '')
        engagement = f"{topic.get('score', 0)} upvotes, {topic.get('num_comments', 0)} comments"
        
        # Handle escaping for YAML
        excerpt_safe = excerpt.replace('"', '\\"')
        meta_description_safe = meta_description.replace('"', '\\"')
        title_safe = title_escaped.replace('"', '\\"')
        
        frontmatter = f'''---
title: "{title_safe}"
slug: "{slug}"
date: {publish_date.strftime('%Y-%m-%d')}
publishDate: {publish_date.isoformat()}
excerpt: "{excerpt_safe}"
description: "{meta_description_safe}"
tags: [{', '.join(f'"{tag}"' for tag in tags)}]
categories: ["tech-news"]
readingTime: {reading_time}
wordCount: {len(content.split())}
author: "AI Content Farm"
featured: false
draft: false

# SEO
seo:
  title: "{title_safe}"
  description: "{meta_description_safe}"
  canonical: ""
  noindex: false

# Social sharing
social:
  twitter: true
  facebook: true
  linkedin: true

# Monetization
monetization:
  ads: true
  affiliate: false
  sponsored: false

# Sources
originalSource:
  url: "{reddit_url}"
  platform: "Reddit"
  subreddit: "{subreddit}"
  engagement: "{engagement}"
---

'''
        return frontmatter

    def format_citations(self, enrichment: Dict[str, Any]) -> str:
        """Format citations section for the article."""
        citations = enrichment.get('citations', [])
        if not citations:
            return ""
            
        citation_text = "\n## Sources and References\n\n"
        
        for i, citation in enumerate(citations, 1):
            if citation['type'] == 'primary_source':
                citation_text += f"{i}. [{citation['title']}]({citation['url']}) - {citation['domain']} (accessed {citation['accessed_date']})\n"
            elif citation['type'] == 'discussion_source':
                citation_text += f"{i}. [Reddit Discussion: r/{citation.get('subreddit', 'unknown')}]({citation['url']}) - {citation.get('engagement', 'community discussion')} (accessed {citation['accessed_date']})\n"
                
        citation_text += "\n*This article aggregates information from multiple sources. Please verify important claims independently.*\n"
        
        return citation_text

    def generate_article_content(self, topic: Dict[str, Any]) -> str:
        """Generate the main article content."""
        title = topic.get('title', 'Untitled')
        enrichment = topic.get('enrichment', {})
        external_content = enrichment.get('external_content')
        
        # Start with introduction
        content = f"# {title}\n\n"
        
        # Add engagement context
        engagement_text = f"*This topic is currently trending on Reddit's r/{topic.get('subreddit', 'unknown')} community with {topic.get('score', 0)} upvotes and {topic.get('num_comments', 0)} comments, indicating significant community interest.*\n\n"
        content += engagement_text
        
        # Add main content based on available information
        if external_content and external_content.get('success'):
            # We have external source content
            content += "## What's Happening\n\n"
            
            if external_content.get('description'):
                content += f"{external_content['description']}\n\n"
                
            if external_content.get('content_preview'):
                # Use first paragraph of content preview
                preview_lines = external_content['content_preview'].split('\n')
                first_paragraph = next((line.strip() for line in preview_lines if line.strip() and len(line.strip()) > 50), '')
                if first_paragraph:
                    content += f"{first_paragraph}\n\n"
                    
            content += f"According to [{external_content['domain']}]({external_content['url']}), this development highlights the ongoing evolution in the tech industry.\n\n"
            
        else:
            # Reddit-only content
            content += "## Community Discussion\n\n"
            content += f"The Reddit community on r/{topic.get('subreddit', 'unknown')} is actively discussing this topic. "
            
            if topic.get('selftext'):
                content += f"Here's what sparked the conversation:\n\n> {topic['selftext'][:300]}{'...' if len(topic.get('selftext', '')) > 300 else ''}\n\n"
                
        # Add analysis section
        content += "## Why This Matters\n\n"
        content += "This topic has gained significant traction in the tech community for several reasons:\n\n"
        content += f"- **Community Engagement**: With {topic.get('num_comments', 0)} comments, this has sparked meaningful discussion\n"
        content += f"- **Trending Status**: {topic.get('score', 0)} upvotes indicate strong community interest\n"
        content += f"- **Relevance**: Posted in r/{topic.get('subreddit', 'unknown')}, a key community for tech discussions\n\n"
        
        # Add research notes if available
        research_notes = enrichment.get('research_notes', [])
        if research_notes:
            content += "## Key Insights\n\n"
            for note in research_notes[:3]:  # Limit to first 3 notes
                content += f"- {note}\n"
            content += "\n"
            
        # Add call-to-action
        content += "## Join the Discussion\n\n"
        content += f"What are your thoughts on this development? [Join the conversation on Reddit]({topic.get('reddit_url', '')}) "
        content += f"or share your perspective in the comments below.\n\n"
        
        # Add disclaimer
        content += "---\n\n"
        content += "*This content is generated from trending topics and community discussions. "
        content += "While we strive for accuracy, please verify important information from primary sources.*\n\n"
        
        return content

    def publish_topic(self, topic: Dict[str, Any]) -> str:
        """Publish a single topic as a markdown article."""
        title = topic.get('title', 'Untitled')
        slug = self.generate_slug(title)
        
        # Generate unique filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{timestamp}-{slug}.md"
        filepath = os.path.join(self.content_dir, filename)
        
        # Ensure filename is unique
        counter = 1
        while os.path.exists(filepath):
            filename = f"{timestamp}-{slug}-{counter}.md"
            filepath = os.path.join(self.content_dir, filename)
            counter += 1
            
        # Generate content
        article_content = self.generate_article_content(topic)
        frontmatter = self.generate_frontmatter(topic, article_content, slug)
        
        # Add citations
        enrichment = topic.get('enrichment', {})
        citations = self.format_citations(enrichment)
        
        # Combine everything
        full_content = frontmatter + article_content + citations
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
            
        print(f"Published: {filename}")
        return filepath

    def publish_enriched_topics(self, enriched_topics_file: str, max_articles: int = 5) -> List[str]:
        """Publish multiple enriched topics as articles."""
        input_path = os.path.join(self.output_dir, enriched_topics_file)
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Enriched topics file not found: {input_path}")
            
        with open(input_path, 'r') as f:
            data = json.load(f)
            
        topics = data.get('topics', [])
        
        # Deduplicate topics before publishing
        unique_topics = self._deduplicate_for_publishing(topics)
        print(f"After deduplication: {len(unique_topics)} unique topics for publishing")
        
        # Limit number of articles published
        topics_to_publish = unique_topics[:max_articles]
        
        print(f"Publishing {len(topics_to_publish)} articles...")
        
        published_files = []
        published_slugs = set()  # Track published slugs to prevent file conflicts
        
        for i, topic in enumerate(topics_to_publish, 1):
            title = topic.get('title', 'Untitled')
            print(f"\nPublishing {i}/{len(topics_to_publish)}: {title}")
            
            # Generate slug and check for conflicts
            slug = self.generate_slug(title)
            if slug in published_slugs:
                print(f"  Skipping duplicate slug: {slug}")
                continue
                
            try:
                filepath = self.publish_topic(topic)
                published_files.append(filepath)
                published_slugs.add(slug)
            except Exception as e:
                print(f"Error publishing topic: {e}")
                continue
                
        # Generate index/summary file
        self.generate_publication_summary(published_files, enriched_topics_file)
        
        # Final cleanup of any duplicates in the content directory
        print(f"\nRunning final duplicate cleanup...")
        cleanup_result = self.cleanup_duplicate_articles(similarity_threshold=0.85, dry_run=False)
        
        if cleanup_result["removed"]:
            print(f"Final cleanup removed {len(cleanup_result['removed'])} additional duplicates")
            # Update published_files list to remove any that were cleaned up
            removed_basenames = [os.path.basename(f) for f in cleanup_result["removed"]]
            published_files = [f for f in published_files if os.path.basename(f) not in removed_basenames]
        
        return published_files

    def generate_publication_summary(self, published_files: List[str], source_file: str):
        """Generate a summary of published articles."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = os.path.join(self.output_dir, f"publication_summary_{timestamp}.json")
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "source_file": source_file,
            "total_published": len(published_files),
            "published_articles": []
        }
        
        for filepath in published_files:
            filename = os.path.basename(filepath)
            # Extract slug from filename
            slug = filename.replace('.md', '').split('-', 1)[1] if '-' in filename else filename.replace('.md', '')
            
            summary["published_articles"].append({
                "filename": filename,
                "filepath": filepath,
                "slug": slug,
                "url_path": f"/articles/{slug}"
            })
            
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
            
        print(f"\nPublication summary saved: {summary_file}")

def main():
    """Command line interface for content publishing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Publish enriched topics as markdown articles")
    parser.add_argument("enriched_file", nargs='?', help="Enriched topics JSON file to publish")
    parser.add_argument("--output-dir", default="../output", help="Output directory")
    parser.add_argument("--site-dir", default="../site", help="Site directory")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum articles to publish")
    parser.add_argument("--cleanup-only", action="store_true", help="Only run duplicate cleanup, don't publish new articles")
    parser.add_argument("--similarity-threshold", type=float, default=0.85, help="Similarity threshold for duplicate detection (0.0-1.0)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    
    args = parser.parse_args()
    
    publisher = ContentPublisher(args.output_dir, args.site_dir)
    
    if args.cleanup_only:
        # Run cleanup only
        print("Running duplicate article cleanup...")
        result = publisher.cleanup_duplicate_articles(
            similarity_threshold=args.similarity_threshold,
            dry_run=args.dry_run
        )
        
        # Save cleanup report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(args.output_dir, f"cleanup_report_{timestamp}.json")
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Cleanup report saved: {report_file}")
        
    else:
        # Normal publishing workflow
        if not args.enriched_file:
            print("Error: enriched_file required for publishing (or use --cleanup-only)")
            return
            
        published_files = publisher.publish_enriched_topics(args.enriched_file, args.max_articles)
        print(f"\nContent publishing complete. Published {len(published_files)} articles to {publisher.content_dir}")

if __name__ == "__main__":
    main()

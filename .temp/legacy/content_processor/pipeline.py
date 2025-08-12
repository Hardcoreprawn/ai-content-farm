#!/usr/bin/env python3
"""
Content Processing Pipeline - Orchestrates the complete content workflow.

This script manages the entire process:
1. Rank collected topics for publishing worthiness
2. Enrich top topics with research and fact-checking
3. Generate polished markdown articles for JAMStack site
4. Monitor and report on the publishing pipeline
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from topic_ranker import TopicRanker
from content_enricher import ContentEnricher  
from content_publisher import ContentPublisher

class ContentPipeline:
    def __init__(self, output_dir: str = "../output", site_dir: str = "../site"):
        self.output_dir = output_dir
        self.site_dir = site_dir
        
        # Initialize processors
        self.ranker = TopicRanker(output_dir)
        self.enricher = ContentEnricher(output_dir)
        self.publisher = ContentPublisher(output_dir, site_dir)
        
        # Pipeline configuration
        self.config = {
            'ranking': {
                'hours_back': 24,
                'min_score': 0.3,
                'max_topics': 20
            },
            'enrichment': {
                'request_delay': 1.0,
                'max_retries': 3
            },
            'publishing': {
                'max_articles': 5,
                'content_format': 'markdown'
            }
        }

    def run_full_pipeline(self, config_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run the complete content processing pipeline."""
        if config_overrides:
            # Merge config overrides
            for section, values in config_overrides.items():
                if section in self.config:
                    self.config[section].update(values)
                    
        print("🚀 Starting Content Processing Pipeline")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 50)
        
        pipeline_results = {
            'started_at': datetime.now().isoformat(),
            'stages': {},
            'final_output': {},
            'errors': []
        }
        
        try:
            # Stage 1: Topic Ranking
            print("\n📊 Stage 1: Topic Ranking")
            print("-" * 30)
            
            ranked_topics = self.ranker.filter_and_rank_topics(
                hours_back=self.config['ranking']['hours_back'],
                min_final_score=self.config['ranking']['min_score']
            )
            
            if not ranked_topics:
                print("❌ No topics found meeting ranking criteria")
                pipeline_results['stages']['ranking'] = {'status': 'failed', 'reason': 'no_topics_found'}
                return pipeline_results
                
            # Limit topics for processing
            max_topics = self.config['ranking']['max_topics']
            ranked_topics = ranked_topics[:max_topics]
            
            ranked_file = self.ranker.save_ranked_topics(ranked_topics)
            
            pipeline_results['stages']['ranking'] = {
                'status': 'success',
                'topics_found': len(ranked_topics),
                'output_file': ranked_file
            }
            
            print(f"✅ Ranked {len(ranked_topics)} topics")
            
            # Stage 2: Content Enrichment
            print("\n🔍 Stage 2: Content Enrichment")
            print("-" * 30)
            
            enriched_file = self.enricher.process_ranked_topics(os.path.basename(ranked_file))
            
            pipeline_results['stages']['enrichment'] = {
                'status': 'success',
                'input_file': ranked_file,
                'output_file': enriched_file
            }
            
            print(f"✅ Enriched topics saved to {enriched_file}")
            
            # Stage 3: Content Publishing
            print("\n📝 Stage 3: Content Publishing")
            print("-" * 30)
            
            published_files = self.publisher.publish_enriched_topics(
                os.path.basename(enriched_file),
                max_articles=self.config['publishing']['max_articles']
            )
            
            pipeline_results['stages']['publishing'] = {
                'status': 'success',
                'input_file': enriched_file,
                'articles_published': len(published_files),
                'published_files': published_files
            }
            
            print(f"✅ Published {len(published_files)} articles")
            
            # Final summary
            pipeline_results['final_output'] = {
                'total_topics_processed': len(ranked_topics),
                'articles_published': len(published_files),
                'content_directory': self.publisher.content_dir,
                'pipeline_success': True
            }
            
            print("\n🎉 Pipeline Complete!")
            print(f"Published {len(published_files)} articles to {self.publisher.content_dir}")
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            print(f"❌ {error_msg}")
            pipeline_results['errors'].append(error_msg)
            pipeline_results['final_output']['pipeline_success'] = False
            
        finally:
            pipeline_results['completed_at'] = datetime.now().isoformat()
            
        return pipeline_results

    def run_ranking_only(self, hours_back: int = 24, min_score: float = 0.3) -> str:
        """Run only the topic ranking stage."""
        print("📊 Running Topic Ranking Only")
        
        ranked_topics = self.ranker.filter_and_rank_topics(hours_back, min_score)
        
        if not ranked_topics:
            print("No topics found meeting criteria")
            return None
            
        output_file = self.ranker.save_ranked_topics(ranked_topics)
        print(f"Ranked topics saved: {output_file}")
        
        return output_file

    def run_enrichment_only(self, ranked_file: str) -> str:
        """Run only the content enrichment stage."""
        print("🔍 Running Content Enrichment Only")
        
        output_file = self.enricher.process_ranked_topics(ranked_file)
        print(f"Enriched topics saved: {output_file}")
        
        return output_file

    def run_publishing_only(self, enriched_file: str, max_articles: int = 5) -> List[str]:
        """Run only the content publishing stage."""
        print("📝 Running Content Publishing Only")
        
        published_files = self.publisher.publish_enriched_topics(enriched_file, max_articles)
        print(f"Published {len(published_files)} articles")
        
        return published_files

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current status of content processing pipeline."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'directories': {
                'output': self.output_dir,
                'site': self.site_dir,
                'content': self.publisher.content_dir
            },
            'recent_files': {},
            'config': self.config
        }
        
        # Check for recent files
        if os.path.exists(self.output_dir):
            files = []
            for filename in os.listdir(self.output_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.output_dir, filename)
                    files.append({
                        'filename': filename,
                        'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                        'size': os.path.getsize(filepath)
                    })
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            status['recent_files']['output'] = files[:10]  # Last 10 files
            
        # Check for recent articles
        if os.path.exists(self.publisher.content_dir):
            articles = []
            for filename in os.listdir(self.publisher.content_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(self.publisher.content_dir, filename)
                    articles.append({
                        'filename': filename,
                        'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                        'size': os.path.getsize(filepath)
                    })
                    
            articles.sort(key=lambda x: x['modified'], reverse=True)
            status['recent_files']['articles'] = articles[:10]
            
        return status

def main():
    """Command line interface for the content pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Content Farm Processing Pipeline")
    parser.add_argument("--mode", choices=['full', 'rank', 'enrich', 'publish', 'status'], 
                       default='full', help="Pipeline mode to run")
    parser.add_argument("--output-dir", default="../output", help="Output directory")
    parser.add_argument("--site-dir", default="../site", help="Site directory")
    parser.add_argument("--hours-back", type=int, default=24, help="Hours back to look for topics")
    parser.add_argument("--min-score", type=float, default=0.3, help="Minimum ranking score")
    parser.add_argument("--max-articles", type=int, default=5, help="Maximum articles to publish")
    parser.add_argument("--input-file", help="Input file for single-stage operations")
    
    args = parser.parse_args()
    
    pipeline = ContentPipeline(args.output_dir, args.site_dir)
    
    if args.mode == 'full':
        config_overrides = {
            'ranking': {
                'hours_back': args.hours_back,
                'min_score': args.min_score
            },
            'publishing': {
                'max_articles': args.max_articles
            }
        }
        results = pipeline.run_full_pipeline(config_overrides)
        
        # Save pipeline results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(args.output_dir, f"pipeline_results_{timestamp}.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nPipeline results saved: {results_file}")
        
    elif args.mode == 'rank':
        pipeline.run_ranking_only(args.hours_back, args.min_score)
        
    elif args.mode == 'enrich':
        if not args.input_file:
            print("Error: --input-file required for enrich mode")
            sys.exit(1)
        pipeline.run_enrichment_only(args.input_file)
        
    elif args.mode == 'publish':
        if not args.input_file:
            print("Error: --input-file required for publish mode")
            sys.exit(1)
        pipeline.run_publishing_only(args.input_file, args.max_articles)
        
    elif args.mode == 'status':
        status = pipeline.get_pipeline_status()
        print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()

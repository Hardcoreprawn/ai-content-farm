"""
Unit tests for ContentEnricher function core logic.

Tests the pure functional components of content enrichment:
- External content fetching and analysis
- Domain credibility assessment
- Content quality evaluation
- Citation generation
- Research note generation
"""

from enricher_core import (
    assess_domain_credibility,
    extract_html_metadata,
    fetch_external_content,
    assess_content_quality,
    generate_citations,
    generate_verification_checks,
    generate_research_notes,
    enrich_single_topic,
    process_content_enrichment
)
import unittest
from unittest.mock import patch, Mock
import json
import sys
import os

# Add functions directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__),
                '../../functions/ContentEnricher'))


class TestDomainCredibility(unittest.TestCase):
    """Test domain credibility assessment."""

    def test_high_credibility_domains(self):
        """Test high credibility domain scoring."""
        self.assertEqual(assess_domain_credibility('reuters.com'), 1.0)
        self.assertEqual(assess_domain_credibility('techcrunch.com'), 1.0)
        self.assertEqual(assess_domain_credibility('nature.com'), 1.0)

    def test_medium_credibility_domains(self):
        """Test medium credibility domain scoring."""
        self.assertEqual(assess_domain_credibility('cnn.com'), 0.7)
        self.assertEqual(assess_domain_credibility('forbes.com'), 0.7)
        self.assertEqual(assess_domain_credibility('venturebeat.com'), 0.7)

    def test_edu_gov_domains(self):
        """Test education and government domains."""
        self.assertEqual(assess_domain_credibility('stanford.edu'), 1.0)
        self.assertEqual(assess_domain_credibility('nasa.gov'), 1.0)
        self.assertEqual(assess_domain_credibility('cdc.gov'), 1.0)

    def test_unknown_domains(self):
        """Test unknown domain default scoring."""
        self.assertEqual(assess_domain_credibility('unknown-site.com'), 0.4)
        self.assertEqual(assess_domain_credibility('blog.example.org'), 0.4)


class TestHTMLMetadataExtraction(unittest.TestCase):
    """Test HTML metadata extraction."""

    def test_title_extraction(self):
        """Test title extraction from HTML."""
        html = '<html><head><title>Test Article Title</title></head><body>Content</body></html>'
        result = extract_html_metadata(html)
        self.assertEqual(result['title'], 'Test Article Title')

    def test_meta_description_extraction(self):
        """Test meta description extraction."""
        html = '''
        <html>
        <head>
            <meta name="description" content="This is a test description">
        </head>
        <body>Content</body>
        </html>
        '''
        result = extract_html_metadata(html)
        self.assertEqual(result['description'], 'This is a test description')

    def test_og_description_fallback(self):
        """Test Open Graph description as fallback."""
        html = '''
        <html>
        <head>
            <meta property="og:description" content="Open Graph description">
        </head>
        <body>Content</body>
        </html>
        '''
        result = extract_html_metadata(html)
        self.assertEqual(result['description'], 'Open Graph description')

    def test_content_cleaning(self):
        """Test HTML content cleaning and word count."""
        html = '''
        <html>
        <head><script>alert('test');</script></head>
        <body>
            <h1>Main Content</h1>
            <p>This is some test content with multiple words.</p>
            <style>body { color: red; }</style>
        </body>
        </html>
        '''
        result = extract_html_metadata(html)
        self.assertIn('Main Content', result['content_preview'])
        self.assertNotIn('alert', result['content_preview'])
        self.assertNotIn('color: red', result['content_preview'])
        self.assertGreater(result['word_count'], 5)


class TestContentQualityAssessment(unittest.TestCase):
    """Test content quality assessment."""

    def test_high_quality_content(self):
        """Test high quality content scoring."""
        content_result = {
            'success': True,
            'title': 'Great Article Title',
            'description': 'Comprehensive description',
            'word_count': 500,
            'credibility_score': 1.0
        }
        quality = assess_content_quality(content_result)
        self.assertGreater(quality['overall_score'], 0.8)
        self.assertTrue(quality['has_title'])
        self.assertTrue(quality['has_description'])
        self.assertTrue(quality['substantial_content'])

    def test_low_quality_content(self):
        """Test low quality content scoring."""
        content_result = {
            'success': False,
            'title': None,
            'description': None,
            'word_count': 50,
            'credibility_score': 0.2
        }
        quality = assess_content_quality(content_result)
        self.assertLess(quality['overall_score'], 0.5)
        self.assertFalse(quality['has_title'])
        self.assertFalse(quality['has_description'])
        self.assertFalse(quality['substantial_content'])


class TestCitationGeneration(unittest.TestCase):
    """Test citation generation."""

    def test_reddit_citation_generation(self):
        """Test Reddit citation creation."""
        topic = {
            'title': 'Test Topic',
            'reddit_url': 'https://reddit.com/r/test/comments/abc123/',
            'subreddit': 'technology',
            'score': 1500,
            'num_comments': 125
        }

        citations = generate_citations(topic, None)
        reddit_citation = citations[0]

        self.assertEqual(reddit_citation['type'], 'discussion_source')
        self.assertEqual(reddit_citation['domain'], 'reddit.com')
        self.assertEqual(reddit_citation['subreddit'], 'technology')
        self.assertIn('1500 upvotes', reddit_citation['engagement'])

    def test_external_citation_generation(self):
        """Test external source citation creation."""
        topic = {
            'title': 'Test Topic',
            'reddit_url': 'https://reddit.com/r/test/comments/abc123/',
            'subreddit': 'technology',
            'score': 1500,
            'num_comments': 125
        }

        external_content = {
            'success': True,
            'url': 'https://techcrunch.com/article',
            'domain': 'techcrunch.com',
            'title': 'Original Article',
            'credibility_score': 1.0
        }

        citations = generate_citations(topic, external_content)
        self.assertEqual(len(citations), 2)

        external_citation = citations[1]
        self.assertEqual(external_citation['type'], 'primary_source')
        self.assertEqual(external_citation['domain'], 'techcrunch.com')
        self.assertEqual(external_citation['credibility_score'], 1.0)


class TestVerificationChecks(unittest.TestCase):
    """Test verification check generation."""

    def test_verification_check_generation(self):
        """Test verification check creation."""
        checks = generate_verification_checks(
            'Breaking: New AI breakthrough announced')

        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0]['type'], 'manual_verification')
        self.assertEqual(checks[0]['priority'], 'high')  # Contains 'breaking'
        self.assertEqual(checks[1]['type'], 'source_credibility')

    def test_normal_priority_topic(self):
        """Test normal priority for regular topics."""
        checks = generate_verification_checks('Regular technology update')
        self.assertEqual(checks[0]['priority'], 'medium')


class TestResearchNotes(unittest.TestCase):
    """Test research note generation."""

    def test_research_notes_generation(self):
        """Test comprehensive research notes."""
        topic = {
            'title': 'Test Topic',
            'subreddit': 'technology',
            'score': 1500,
            'num_comments': 125
        }

        external_content = {
            'success': True,
            'domain': 'techcrunch.com',
            'credibility_score': 1.0,
            'word_count': 500
        }

        quality = {'overall_score': 0.8}

        notes = generate_research_notes(topic, external_content, quality)

        self.assertGreater(len(notes), 3)
        self.assertTrue(
            any('trending on r/technology' in note for note in notes))
        self.assertTrue(
            any('High-credibility source' in note for note in notes))
        self.assertTrue(any('fact-checking' in note for note in notes))

    def test_low_quality_warning(self):
        """Test low quality content warning."""
        topic = {'title': 'Test', 'subreddit': 'test',
                 'score': 100, 'num_comments': 10}
        external_content = {'success': True, 'domain': 'unknown.com',
                            'credibility_score': 0.3, 'word_count': 100}
        quality = {'overall_score': 0.3}

        notes = generate_research_notes(topic, external_content, quality)
        self.assertTrue(any('LOW QUALITY ALERT' in note for note in notes))


class TestContentEnrichmentIntegration(unittest.TestCase):
    """Test complete content enrichment process."""

    @patch('enricher_core.fetch_external_content')
    @patch('enricher_core.time.sleep')
    def test_enrich_single_topic(self, mock_sleep, mock_fetch):
        """Test single topic enrichment."""
        # Mock external content fetch
        mock_fetch.return_value = {
            'success': True,
            'url': 'https://techcrunch.com/article',
            'domain': 'techcrunch.com',
            'title': 'Test Article',
            'description': 'Test description',
            'word_count': 300,
            'credibility_score': 1.0
        }

        topic = {
            'title': 'Test AI Breakthrough',
            'external_url': 'https://techcrunch.com/article',
            'reddit_url': 'https://reddit.com/r/test/comments/abc123/',
            'subreddit': 'technology',
            'score': 1500,
            'num_comments': 125,
            'ranking_score': 0.8
        }

        enriched = enrich_single_topic(topic)

        # Check enrichment data structure
        self.assertIn('enrichment_data', enriched)
        enrichment = enriched['enrichment_data']

        self.assertIn('processed_at', enrichment)
        self.assertIn('external_content', enrichment)
        self.assertIn('content_quality', enrichment)
        self.assertIn('citations', enrichment)
        self.assertIn('verification_checks', enrichment)
        self.assertIn('research_notes', enrichment)

        # Check data quality
        self.assertEqual(len(enrichment['citations']), 2)  # Reddit + external
        self.assertEqual(len(enrichment['verification_checks']), 2)
        self.assertGreater(len(enrichment['research_notes']), 3)

        # Verify external content was fetched
        mock_fetch.assert_called_once()
        mock_sleep.assert_called_once()

    def test_process_content_enrichment(self):
        """Test complete enrichment process."""
        ranked_data = {
            'source_files': ['test_ranked.json'],
            'total_topics': 2,
            'topics': [
                {
                    'title': 'Test Topic 1',
                    'external_url': None,  # No external URL
                    'reddit_url': 'https://reddit.com/r/test/comments/abc123/',
                    'subreddit': 'technology',
                    'score': 1000,
                    'num_comments': 50,
                    'ranking_score': 0.7
                },
                {
                    'title': 'Test Topic 2',
                    # Reddit URL (should be skipped)
                    'external_url': 'https://reddit.com/external',
                    'reddit_url': 'https://reddit.com/r/test/comments/def456/',
                    'subreddit': 'programming',
                    'score': 800,
                    'num_comments': 30,
                    'ranking_score': 0.6
                }
            ]
        }

        result = process_content_enrichment(ranked_data)

        # Check result structure
        self.assertIn('generated_at', result)
        self.assertIn('source_file', result)
        self.assertIn('total_topics', result)
        self.assertIn('enrichment_statistics', result)
        self.assertIn('topics', result)

        # Check statistics
        stats = result['enrichment_statistics']
        self.assertEqual(stats['total_topics'], 2)
        # No valid external URLs
        self.assertEqual(stats['external_content_fetched'], 0)
        self.assertEqual(
            stats['verification_checks_created'], 4)  # 2 per topic

        # Check enriched topics
        self.assertEqual(len(result['topics']), 2)
        for topic in result['topics']:
            self.assertIn('enrichment_data', topic)


if __name__ == '__main__':
    unittest.main()

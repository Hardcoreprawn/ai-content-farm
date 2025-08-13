// Get latest content from content processing services
import type { APIRoute } from 'astro';
import type { Article, ContentResponse } from '../../types/api';
import { contentService } from '../../services/content';

export const GET: APIRoute = async ({ url }) => {
  const limit = parseInt(url.searchParams.get('limit') || '20', 10);
  const source = url.searchParams.get('source') || '';
  
  try {
    // Try to get real content from services
    let articles = await contentService.getAllContent(source, limit);
    
    // If no real content is available, use mock data
    if (articles.length === 0) {
      articles = [
        {
          title: "AI breakthrough in neural network architecture",
          content: "Researchers have developed a new approach to neural network design that improves efficiency by 40%.",
          url: "https://example.com/ai-breakthrough",
          source: "reddit",
          author: "researcher123",
          score: 1250,
          num_comments: 87,
          created_utc: new Date().toISOString(),
          final_score: 0.92,
          engagement_score: 0.85,
          monetization_score: 0.95,
          recency_score: 1.0,
          title_quality_score: 0.88
        },
        {
          title: "LinkedIn launches new AI-powered content tools",
          content: "Professional networking platform introduces machine learning features for content creators.",
          url: "https://example.com/linkedin-ai",
          source: "linkedin",
          author: "linkedin_official",
          score: 890,
          num_comments: 45,
          created_utc: new Date(Date.now() - 3600000).toISOString(),
          final_score: 0.78,
          engagement_score: 0.70,
          monetization_score: 0.85,
          recency_score: 0.95,
          title_quality_score: 0.80
        },
        {
          title: "ArsTechnica: The future of edge computing in 2025",
          content: "Comprehensive analysis of edge computing trends and their impact on enterprise infrastructure.",
          url: "https://arstechnica.com/example",
          source: "arstechnica",
          author: "tech_journalist",
          score: 654,
          num_comments: 32,
          created_utc: new Date(Date.now() - 7200000).toISOString(),
          final_score: 0.72,
          engagement_score: 0.65,
          monetization_score: 0.80,
          recency_score: 0.90,
          title_quality_score: 0.85
        }
      ];
      
      // Filter mock data by source if specified
      if (source) {
        articles = articles.filter(article => article.source === source);
      }
    }
    
    // Limit results
    articles = articles.slice(0, limit);
    
    const response: ContentResponse = {
      status: "success",
      total: articles.length,
      articles: articles,
      metadata: {
        timestamp: new Date().toISOString(),
        source_filter: source || 'all',
        limit: limit
      }
    };
    
    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=300' // Cache for 5 minutes
      }
    });
    
  } catch (error) {
    console.error('Failed to fetch content:', error);
    
    const response: ContentResponse = {
      status: "error",
      message: "Failed to fetch content",
      error: error instanceof Error ? error.message : 'Unknown error'
    };
    
    return new Response(JSON.stringify(response), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
};

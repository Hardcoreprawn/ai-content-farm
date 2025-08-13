import axios from 'axios';
import type { Article } from '../types/api';

const CONTENT_PROCESSOR_URL = process.env.CONTENT_PROCESSOR_URL || 'http://content-processor:8000';
const CONTENT_RANKER_URL = process.env.CONTENT_RANKER_URL || 'http://content-ranker:8001';

export class ContentService {
  
  /**
   * Fetch raw content from the content processor
   */
  async fetchRawContent(source?: string, limit: number = 20): Promise<any[]> {
    try {
      const params = new URLSearchParams();
      if (source) params.append('source', source);
      params.append('limit', limit.toString());
      
      const response = await axios.get(`${CONTENT_PROCESSOR_URL}/collect`, {
        params,
        timeout: 10000
      });
      
      return response.data.items || [];
    } catch (error) {
      console.error('Failed to fetch raw content:', error);
      return [];
    }
  }
  
  /**
   * Fetch ranked content from the content ranker
   */
  async fetchRankedContent(limit: number = 20): Promise<Article[]> {
    try {
      const response = await axios.get(`${CONTENT_RANKER_URL}/rank`, {
        params: { limit },
        timeout: 10000
      });
      
      return response.data.ranked_items || [];
    } catch (error) {
      console.error('Failed to fetch ranked content:', error);
      return [];
    }
  }
  
  /**
   * Get comprehensive content from all sources
   */
  async getAllContent(source?: string, limit: number = 20): Promise<Article[]> {
    try {
      // Try to get ranked content first (more valuable)
      const rankedContent = await this.fetchRankedContent(limit);
      
      if (rankedContent.length > 0) {
        // Filter by source if specified
        if (source) {
          return rankedContent.filter(article => article.source === source);
        }
        return rankedContent.slice(0, limit);
      }
      
      // Fallback to raw content if ranked content is not available
      const rawContent = await this.fetchRawContent(source, limit);
      
      // Transform raw content to Article format
      return rawContent.map(item => ({
        title: item.title || 'Untitled',
        content: item.selftext || item.content || 'No content available',
        url: item.url || '',
        source: item.source || source || 'unknown',
        author: item.author || 'Anonymous',
        score: item.score || 0,
        num_comments: item.num_comments || 0,
        created_utc: item.created_utc || new Date().toISOString(),
        final_score: 0,
        engagement_score: 0,
        monetization_score: 0,
        recency_score: 0,
        title_quality_score: 0
      }));
      
    } catch (error) {
      console.error('Failed to get all content:', error);
      return [];
    }
  }
}

export const contentService = new ContentService();

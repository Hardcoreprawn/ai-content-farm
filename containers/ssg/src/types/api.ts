// Types for content API responses
export interface Article {
  title: string;
  content: string;
  url: string;
  source: string;
  author: string;
  score: number;
  num_comments: number;
  created_utc: string;
  final_score: number;
  engagement_score: number;
  monetization_score: number;
  recency_score: number;
  title_quality_score: number;
}

export interface ContentResponse {
  status: "success" | "error";
  total?: number;
  articles?: Article[];
  metadata?: {
    timestamp: string;
    source_filter: string;
    limit: number;
  };
  message?: string;
  error?: string;
}

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  service: string;
  version: string;
  uptime: number;
  environment: string;
}

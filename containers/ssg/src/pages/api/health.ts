// SSG Health Check API
import type { APIRoute } from 'astro';
import type { HealthResponse } from '../../types/api';

const START_TIME = Date.now();

export const GET: APIRoute = async () => {
  try {
    const response: HealthResponse = {
      status: "healthy",
      timestamp: new Date().toISOString(),
      service: "ai-content-farm-ssg",
      version: "1.0.0",
      uptime: Math.floor((Date.now() - START_TIME) / 1000),
      environment: process.env.NODE_ENV || 'development'
    };

    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    const response: HealthResponse = {
      status: "unhealthy",
      timestamp: new Date().toISOString(),
      service: "ai-content-farm-ssg",
      version: "1.0.0",
      uptime: Math.floor((Date.now() - START_TIME) / 1000),
      environment: process.env.NODE_ENV || 'development'
    };

    return new Response(JSON.stringify(response), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
};

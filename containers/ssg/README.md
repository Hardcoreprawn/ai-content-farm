# AI Content Farm - Static Site Generator

**Modern, fast static site built with Astro**

## Overview

This Static Site Generator (SSG) service automatically builds and deploys a public-facing website from the processed content in our AI Content Farm pipeline. It integrates with the content processing services to create a dynamic, SEO-optimized website.

## Architecture

### Content Pipeline Integration
```
Content Processor → Content Ranker → Content Enricher → SSG → Static Website
     (Reddit)         (Scoring)       (AI Summary)      (Astro)   (Deployment)
```

### Features

- **Modern Astro Framework**: Fast, component-based architecture
- **Markdown Support**: Direct processing of enriched content
- **SEO Optimized**: Meta tags, structured data, sitemap generation
- **Responsive Design**: Mobile-first, accessible design
- **API Integration**: Real-time content updates from other services
- **Hot Reload**: Development server with instant updates

### Content Types

1. **Articles**: Processed and ranked content from various sources
2. **Topics**: Trending topics with engagement metrics
3. **Categories**: Organized content by source and theme
4. **Analytics**: Content performance and engagement data

## Development

### Local Development
```bash
# Start all services (includes SSG)
./scripts/start-all-services.sh

# SSG specific commands
cd containers/ssg
npm install
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview built site
```

### Content Updates
The SSG service automatically rebuilds when:
- New content is processed by Content Processor
- Content is ranked by Content Ranker
- Content is enriched with AI summaries
- Manual rebuild is triggered via API

### API Endpoints
- `GET /api/ssg/health` - Health check
- `POST /api/ssg/rebuild` - Trigger site rebuild
- `GET /api/ssg/status` - Build status
- `POST /api/ssg/webhook` - Content update webhook

## Deployment

### Local Preview
The SSG runs on `http://localhost:3000` in development mode with hot reload.

### Production Build
Built site is optimized and ready for deployment to:
- **Azure Static Web Apps**
- **Netlify** 
- **Vercel**
- **GitHub Pages**
- **CDN + Storage Account**

## Content Sources

The SSG consumes content from:
1. **Blob Storage**: Processed JSON files from content pipeline
2. **API Endpoints**: Real-time content from other services
3. **Configuration**: Site settings and themes
4. **Static Assets**: Images, logos, and design assets

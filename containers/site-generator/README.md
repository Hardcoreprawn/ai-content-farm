# Site Generator Container

Python-based JAMStack static site generator for AI Content Farm. Converts processed articles to markdown and generates modern, mobile-friendly static websites.

*Version: 1.0.0 - Initial Release*

<!-- Updated: 2025-09-17 - Pipeline deployment verification -->

## 🎯 Purpose

Transform AI-generated articles into beautiful, fast-loading static websites suitable for deployment to Azure Static Web Apps with custom domain support.

## 🚀 Features

### Core Functionality
- **Markdown Generation**: Convert JSON articles to clean markdown with frontmatter
- **Static Site Generation**: Build complete HTML sites using Jinja2 templates
- **Mobile-First Design**: Responsive, iPad-friendly layouts
- **JAMStack Architecture**: Fast, secure, and scalable static sites
- **SEO Optimization**: Proper meta tags, structured data, and RSS feeds

### Technical Features
- **Python-Based**: Consistent with existing tech stack
- **Azure Integration**: Native blob storage and deployment support
- **Theme System**: Modular template system (starting with "minimal" theme)
- **Cost Tracking**: Full visibility into generation costs and metrics
- **Progressive Enhancement**: Works without JavaScript, enhanced with it

## 📡 API Endpoints

### Standard Endpoints
```http
GET /health                                    # Container health check
GET /status                                    # Current generator status
GET /                                          # Service information
```

### Generation Endpoints
```http
POST /generate-markdown                        # Convert JSON to markdown
POST /generate-site                           # Build static HTML site
POST /wake-up                                 # Process new content
```

### Preview & Management
```http
GET /preview/{site_id}                        # Get preview URL
```

## 🔧 Configuration

### Environment Variables
```bash
# Azure Storage - Option 1: Connection String (Development)
AZURE_STORAGE_CONNECTION_STRING=your_azure_storage_connection

# Azure Storage - Option 2: Managed Identity (Production)
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account_name
AZURE_CLIENT_ID=your_managed_identity_client_id

# Container Names
PROCESSED_CONTENT_CONTAINER=processed-content
MARKDOWN_CONTENT_CONTAINER=markdown-content
STATIC_SITES_CONTAINER=static-sites

# Site Configuration
SITE_TITLE="JabLab Tech News"
SITE_DESCRIPTION="AI-curated technology news and insights"
SITE_DOMAIN="jablab.com"
SITE_URL="https://jablab.com"

# Generation Settings
ARTICLES_PER_PAGE=10
MAX_ARTICLES_TOTAL=100
DEFAULT_THEME=minimal
```

## 🎨 Theme System

### Minimal Theme
- **Clean Design**: Focused on readability and performance
- **Mobile-First**: Optimized for iPad and mobile devices
- **Fast Loading**: Minimal CSS/JS, optimized assets
- **Accessible**: WCAG compliant, keyboard navigation
- **Dark Mode**: Automatic system preference detection

### Template Structure
```
templates/minimal/
├── base.html           # Base layout with navigation
├── index.html          # Homepage with article grid
├── article.html        # Individual article pages
└── rss.xml            # RSS feed template
```

### Static Assets
```
static/
├── style.css          # Responsive CSS with CSS variables
├── script.js          # Progressive enhancement JavaScript
└── favicon.ico        # Site icon
```

## 🔄 Processing Flow

```
Processed Articles (JSON) → Markdown Generation → Static Site → Azure Deployment
        ↓                       ↓                    ↓              ↓
   blob://processed-content  blob://markdown-content  blob://static-sites  jablab.com
```

### Markdown Generation
1. **Source**: Read from `processed-content` container
2. **Transform**: Convert JSON to markdown with frontmatter
3. **Enrich**: Add SEO metadata, tags, and structured data
4. **Store**: Save to `markdown-content` container

### Site Generation  
1. **Source**: Read from `markdown-content` container
2. **Render**: Process through Jinja2 templates
3. **Optimize**: Minify assets, generate sitemaps
4. **Package**: Create deployment-ready site archive
5. **Deploy**: Upload to `static-sites` container

## 🧪 Testing

### Local Development
```bash
# Install dependencies
cd containers/site-generator
pip install -r requirements.txt

# Run tests
python test_generator.py

# Start development server
python main.py
```

### Container Testing
```bash
# Build container
docker build -t site-generator .

# Run locally
docker run -p 8000:8000 site-generator

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/status
```

## 📊 Output Examples

### Generated Markdown
```markdown
---
title: "U.S. And Allies Declare Salt Typhoon Hack A National Defense Crisis"
slug: "us-and-allies-declare-salt-typhoon-hack-a-national"
date: "2025-09-01"
tags: ["tech", "ai-curated", "cybersecurity"]
source:
  name: "reddit"
  url: "https://www.forbes.com/..."
metadata:
  word_count: 497
  quality_score: 0.5
  cost: 0.0010515
---

# Article Content Here...
```

### Site Structure
```
generated-site/
├── index.html              # Homepage with article grid
├── articles/               # Individual article pages
│   ├── article-1.html
│   └── article-2.html
├── feed.xml               # RSS feed
├── style.css              # Compiled styles
├── script.js              # Enhanced functionality
└── sitemap.xml            # SEO sitemap
```

## 🌐 Deployment Strategy

### Azure Static Web Apps
- **Custom Domain**: jablab.com via Azure DNS
- **HTTPS**: Automatic SSL certificates
- **CDN**: Global content delivery
- **Preview**: Branch-based preview deployments

### Cost Optimization
- **Static Assets**: Efficient caching and compression
- **Minimal Resources**: ~$5-10/month for hosting
- **Performance**: Fast loading, minimal bandwidth usage

## 🔗 Integration Points

### Reads From
- **Container**: `processed-content`
- **Format**: JSON articles from content processor
- **Trigger**: Manual wake-up or scheduled processing

### Writes To
- **Container**: `markdown-content` (intermediate)
- **Container**: `static-sites` (final output)
- **Format**: Markdown files and site archives

### Triggers
- **Manual**: POST to `/wake-up` endpoint
- **Automated**: Content processor completion events
- **Scheduled**: Daily site rebuilds for freshness

## 🛡️ Security & Standards

### Security Features
- **Input Validation**: Sanitize all content and metadata
- **XSS Prevention**: Proper template escaping
- **CSP Headers**: Content Security Policy implementation
- **HTTPS Only**: Secure communication

### Standards Compliance
- **HTML5**: Semantic markup
- **WCAG 2.1**: Accessibility standards
- **RSS 2.0**: Standard feed format
- **Schema.org**: Structured data markup

## 🚧 Future Enhancements

### Phase 1 (Current)
- [x] Basic markdown generation
- [x] Minimal theme implementation
- [x] Azure blob integration
- [ ] Site generation and packaging

### Phase 2 (Next Sprint)
- [ ] Azure Static Web Apps deployment
- [ ] Custom domain configuration (jablab.com)
- [ ] RSS feed generation
- [ ] SEO optimization

### Phase 3 (Future)
- [ ] Multiple theme support
- [ ] Search functionality
- [ ] Comment system integration
- [ ] WASM/Rust frontend components
- [ ] Progressive Web App features

## 📈 Performance Targets

- **Build Time**: < 30 seconds for 100 articles
- **Page Load**: < 2 seconds first contentful paint
- **Lighthouse Score**: 95+ on all metrics
- **Mobile Friendly**: 100% mobile usability score

---

**Built for**: AI Content Farm  
**Technology**: Python + Jinja2 + JAMStack  
**Deployment**: Azure Static Web Apps  
**Domain**: jablab.com

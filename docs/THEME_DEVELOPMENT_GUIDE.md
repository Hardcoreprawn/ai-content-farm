# Theme Development Guide

This guide covers how to create, customize, and manage themes for the AI Content Farm static site generator.

## Overview

The theme system provides a flexible, extensible way to customize the appearance and behavior of generated static sites. Themes are directory-based with JSON configuration files and support modern web technologies.

## Theme Architecture

### Directory Structure

```
templates/
├── theme-name/
│   ├── theme.json          # Theme configuration and metadata
│   ├── base.html           # Base template (required)
│   ├── index.html          # Homepage template (required)
│   ├── article.html        # Article page template (required)
│   ├── 404.html            # 404 error page (optional)
│   ├── feed.xml            # RSS feed template (optional)
│   ├── sitemap.xml         # Sitemap template (optional)
│   ├── theme-name.css      # Theme-specific CSS
│   ├── theme-name.js       # Theme-specific JavaScript
│   └── assets/             # Additional static assets
│       ├── images/
│       ├── fonts/
│       └── icons/
```

### Required Templates

Every theme must include these three core templates:

1. **base.html** - Base layout with common HTML structure
2. **index.html** - Homepage template for article listings
3. **article.html** - Individual article page template

### Optional Templates

- **404.html** - Custom error page
- **feed.xml** - RSS/Atom feed
- **sitemap.xml** - XML sitemap

## Theme Configuration (theme.json)

```json
{
  "name": "theme-name",
  "display_name": "Theme Display Name",
  "description": "A description of what this theme provides",
  "version": "1.0.0",
  "author": "Your Name",
  "homepage": "https://example.com",
  "license": "MIT",
  "tags": ["responsive", "grid", "modern"],
  "grid_layout": true,
  "tech_optimized": true,
  "responsive": true,
  "supports_dark_mode": true,
  "required_templates": ["base.html", "index.html", "article.html"],
  "optional_templates": ["404.html", "feed.xml", "sitemap.xml"],
  "static_assets": ["theme-name.css", "theme-name.js"]
}
```

### Configuration Fields

- **name** (required): Unique identifier matching directory name
- **display_name** (required): Human-readable theme name
- **description** (required): Brief description of theme features
- **version** (required): Semantic version (e.g., "1.0.0")
- **author** (required): Theme creator name
- **homepage** (optional): Theme homepage URL
- **license** (optional): License identifier (e.g., "MIT", "GPL-3.0")
- **tags** (optional): Array of descriptive tags
- **grid_layout** (optional): Whether theme uses CSS Grid layouts
- **tech_optimized** (optional): Whether theme is optimized for tech content
- **responsive** (optional): Whether theme is mobile-responsive
- **supports_dark_mode** (optional): Whether theme includes dark mode support

## Template Variables

### Global Variables

Available in all templates:

```jinja2
{{ site.title }}              # Site title
{{ site.description }}        # Site description
{{ site.url }}               # Site base URL
{{ site.language }}          # Site language code
{{ site.generated_at }}      # Generation timestamp
{{ theme.name }}             # Current theme name
{{ theme.version }}          # Theme version
{{ articles | length }}      # Total article count
```

### Article Variables

Available in article.html and index.html:

```jinja2
{{ article.title }}          # Article title
{{ article.slug }}           # URL-friendly slug
{{ article.content }}        # HTML content
{{ article.summary }}        # Article summary/excerpt
{{ article.author }}         # Author name
{{ article.published_at }}   # Publication date
{{ article.updated_at }}     # Last update date
{{ article.tags }}           # Array of tags
{{ article.category }}       # Article category
{{ article.reading_time }}   # Estimated reading time
{{ article.word_count }}     # Word count
{{ article.url }}            # Article URL
{{ article.featured_image }} # Featured image URL
```

### Homepage Variables

Available in index.html:

```jinja2
{{ articles }}               # Array of all articles
{{ featured_articles }}      # Array of featured articles
{{ recent_articles }}        # Array of recent articles
{{ categories }}             # Array of available categories
{{ tags }}                   # Array of all tags
{{ pagination }}             # Pagination data
```

## Styling Guidelines

### CSS Architecture

Themes should follow modern CSS practices:

```css
/* CSS Custom Properties for theming */
:root {
  --primary-color: #2563eb;
  --secondary-color: #64748b;
  --text-color: #1e293b;
  --bg-color: #ffffff;
  --border-color: #e2e8f0;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  :root {
    --text-color: #f1f5f9;
    --bg-color: #0f172a;
    --border-color: #334155;
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .grid-container {
    grid-template-columns: 1fr;
  }
}
```

### Grid Layouts

For grid-based themes, use CSS Grid:

```css
.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin: 2rem 0;
}

.article-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.2s ease;
}

.article-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
}
```

### Accessibility

Ensure themes are accessible:

```css
/* Focus indicators */
a:focus, button:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* High contrast support */
@media (prefers-contrast: high) {
  :root {
    --border-color: #000000;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## JavaScript Enhancement

Themes can include progressive enhancement JavaScript:

```javascript
// theme-name.js
document.addEventListener('DOMContentLoaded', function() {
  // Search functionality
  const searchInput = document.getElementById('search');
  if (searchInput) {
    searchInput.addEventListener('input', filterArticles);
  }
  
  // Dark mode toggle
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleDarkMode);
  }
  
  // Lazy loading images
  if ('IntersectionObserver' in window) {
    lazyLoadImages();
  }
});

function filterArticles(event) {
  const searchTerm = event.target.value.toLowerCase();
  const articles = document.querySelectorAll('.article-card');
  
  articles.forEach(article => {
    const title = article.querySelector('.article-title').textContent.toLowerCase();
    const description = article.querySelector('.article-description').textContent.toLowerCase();
    
    if (title.includes(searchTerm) || description.includes(searchTerm)) {
      article.style.display = 'block';
    } else {
      article.style.display = 'none';
    }
  });
}
```

## Template Examples

### Base Template (base.html)

```html
<!DOCTYPE html>
<html lang="{{ site.language | default('en') }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ site.title }}{% endblock %}</title>
    <meta name="description" content="{% block description %}{{ site.description }}{% endblock %}">
    
    <!-- Theme CSS -->
    <link rel="stylesheet" href="/static/{{ theme.name }}.css">
    
    <!-- SEO Meta Tags -->
    <meta property="og:title" content="{% block og_title %}{{ site.title }}{% endblock %}">
    <meta property="og:description" content="{% block og_description %}{{ site.description }}{% endblock %}">
    <meta property="og:type" content="{% block og_type %}website{% endblock %}">
    
    {% block head %}{% endblock %}
</head>
<body>
    <header class="site-header">
        <nav class="main-navigation">
            <a href="/" class="site-title">{{ site.title }}</a>
            {% block navigation %}{% endblock %}
        </nav>
    </header>

    <main class="site-main">
        {% block content %}{% endblock %}
    </main>

    <footer class="site-footer">
        <p>&copy; {{ site.generated_at.year }} {{ site.title }}. Generated with ❤️ by AI Content Farm.</p>
    </footer>

    <!-- Theme JavaScript -->
    <script src="/static/{{ theme.name }}.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Homepage Template (index.html)

```html
{% extends "base.html" %}

{% block content %}
<section class="hero">
    <h1>{{ site.title }}</h1>
    <p>{{ site.description }}</p>
</section>

<section class="articles-section">
    <div class="articles-filter">
        <input type="search" id="search" placeholder="Search articles...">
        <select id="category-filter">
            <option value="">All Categories</option>
            {% for category in categories %}
            <option value="{{ category }}">{{ category }}</option>
            {% endfor %}
        </select>
    </div>

    <div class="articles-grid">
        {% for article in articles %}
        <article class="article-card" data-category="{{ article.category }}">
            {% if article.featured_image %}
            <img src="{{ article.featured_image }}" alt="{{ article.title }}" class="article-image">
            {% endif %}
            
            <div class="article-content">
                <h2 class="article-title">
                    <a href="{{ article.url }}">{{ article.title }}</a>
                </h2>
                
                <p class="article-description">{{ article.summary }}</p>
                
                <div class="article-meta">
                    <time datetime="{{ article.published_at }}">
                        {{ article.published_at | date('%B %d, %Y') }}
                    </time>
                    <span class="reading-time">{{ article.reading_time }} min read</span>
                </div>
                
                {% if article.tags %}
                <div class="article-tags">
                    {% for tag in article.tags %}
                    <span class="tag">{{ tag }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
        </article>
        {% endfor %}
    </div>
</section>
{% endblock %}
```

## Testing Themes

### Validation

Use the theme validation API to check your theme:

```bash
curl -X POST http://localhost:8080/themes/my-theme/validate
```

### Preview Generation

Generate a preview with sample content:

```bash
curl -X GET http://localhost:8080/themes/my-theme/preview
```

### Local Testing

Test themes locally during development:

```python
from theme_manager import ThemeManager
from pathlib import Path

theme_manager = ThemeManager(Path("templates"))
validation = theme_manager.validate_theme("my-theme")

if not validation["valid"]:
    for error in validation["errors"]:
        print(f"Error: {error}")
```

## Best Practices

### Performance

1. **Optimize Assets**: Minify CSS and JavaScript in production
2. **Image Optimization**: Use appropriate formats and sizes
3. **Lazy Loading**: Implement for images and non-critical content
4. **Caching**: Set appropriate cache headers for static assets

### Accessibility

1. **Semantic HTML**: Use proper heading hierarchy and semantic elements
2. **Alt Text**: Provide descriptive alt text for images
3. **Focus Management**: Ensure keyboard navigation works properly
4. **Color Contrast**: Meet WCAG guidelines for text contrast

### SEO

1. **Meta Tags**: Include proper meta descriptions and titles
2. **Structured Data**: Add JSON-LD structured data for articles
3. **Open Graph**: Include social media sharing meta tags
4. **Performance**: Optimize Core Web Vitals metrics

### Responsive Design

1. **Mobile-First**: Design for mobile devices first
2. **Flexible Grids**: Use CSS Grid and Flexbox appropriately
3. **Touch Targets**: Ensure interactive elements are large enough
4. **Performance**: Optimize for mobile connections

## API Reference

### Theme Management Endpoints

- `GET /themes` - List all available themes
- `GET /themes/{theme_name}` - Get theme details
- `POST /themes/{theme_name}/validate` - Validate theme structure
- `GET /themes/{theme_name}/preview` - Generate theme preview

### Response Format

```json
{
  "status": "success",
  "message": "Operation description",
  "data": {
    "themes": [...],
    "default_theme": "minimal"
  },
  "metadata": {
    "function": "site-generator",
    "timestamp": "2025-01-XX",
    "version": "1.0.0"
  }
}
```

## Migration Guide

### From Basic Themes

1. Create `theme.json` configuration file
2. Update templates to use new variable names
3. Add responsive CSS and JavaScript enhancements
4. Test with validation API

### Adding New Features

1. Update `theme.json` with new configuration options
2. Add feature detection in templates
3. Implement progressive enhancement in JavaScript
4. Update documentation and examples

---

For questions or contributions, please see the main project documentation or create an issue in the repository.
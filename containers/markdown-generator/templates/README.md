# Markdown Templates

Jinja2 templates for generating markdown articles with frontmatter.

## Available Templates

### `default.md.j2`
Standard article template with full frontmatter and structured sections:
- Complete YAML frontmatter (title, url, source, author, dates, category, tags)
- Summary section
- Content section
- Key Points section
- Source reference

### `with-toc.md.j2`
Enhanced template with automatic table of contents:
- All features from default template
- Auto-generated table of contents with section links
- Useful for longer articles

### `minimal.md.j2`
Minimal template with essential fields only:
- Basic frontmatter (title, url, source, generated_date)
- Summary and content without section headers
- Compact source reference

## Template Variables

All templates have access to:

- `metadata` - ArticleMetadata object with fields:
  - `title` (str): Article title
  - `url` (str): Source URL
  - `source` (str): Source identifier
  - `author` (Optional[str]): Article author
  - `published_date` (Optional[datetime]): Publication date
  - `category` (Optional[str]): Content category
  - `tags` (List[str]): Content tags

- `article_data` - Dict with fields:
  - `summary` (Optional[str]): Article summary
  - `content` (Optional[str]): Main content
  - `key_points` (Optional[List[str]]): Key takeaways

- `generated_date` - ISO 8601 timestamp of generation

## Usage in Code

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('default.md.j2')

markdown = template.render(
    metadata=article_metadata,
    article_data=article_data,
    generated_date=datetime.utcnow().isoformat() + 'Z'
)
```

## Adding New Templates

1. Create new `.md.j2` file in this directory
2. Use Jinja2 syntax with conditional blocks (`{% if %}`) for optional fields
3. Maintain consistent frontmatter structure
4. Test with articles that have missing optional fields
5. Update this README with template description

## Template Design Principles

- **Graceful Degradation**: Handle missing optional fields without errors
- **Consistent Structure**: Maintain YAML frontmatter compatibility
- **Clean Output**: No extra whitespace from conditionals
- **Semantic HTML**: Use proper markdown headers and structure
- **Version Control**: Templates are part of container image (Git tracked)

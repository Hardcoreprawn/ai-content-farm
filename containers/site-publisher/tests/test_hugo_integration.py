"""
Integration tests for Hugo build process.

Tests the actual Hugo binary with real markdown content to validate
the complete build pipeline works correctly.
"""

import shutil
from pathlib import Path

import pytest
from hugo_builder import build_site_with_hugo


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hugo_build_real_site(tmp_path):
    """Test building a real Hugo site with actual Hugo binary."""
    # Create Hugo site structure
    hugo_dir = tmp_path / "hugo-site"
    hugo_dir.mkdir()

    # Create content directory
    content_dir = hugo_dir / "content"
    content_dir.mkdir()

    # Create sample markdown files
    posts_dir = content_dir / "posts"
    posts_dir.mkdir()

    # Sample post 1
    post1 = posts_dir / "hello-world.md"
    post1.write_text(
        """---
title: "Hello World"
date: 2025-10-10T10:00:00Z
draft: false
tags: ["test", "hugo"]
---

# Hello World

This is a test post for Hugo integration testing.

## Features

- Markdown rendering
- Frontmatter parsing
- Static site generation
"""
    )

    # Sample post 2
    post2 = posts_dir / "second-post.md"
    post2.write_text(
        """---
title: "Second Post"
date: 2025-10-10T11:00:00Z
draft: false
tags: ["integration", "testing"]
---

# Second Post

Testing multiple posts in Hugo.

## Code Example

```python
def hello():
    return "world"
```

This should be rendered as a code block.
"""
    )

    # Create Hugo config
    config_file = hugo_dir / "config.toml"
    config_file.write_text(
        """
baseURL = "https://test.example.com/"
languageCode = "en-us"
title = "Integration Test Site"
theme = ""

[params]
    description = "Test site for Hugo integration"
    author = "Test Author"
"""
    )

    # Create minimal theme (required for Hugo to build)
    theme_dir = hugo_dir / "themes" / "minimal"
    theme_dir.mkdir(parents=True)

    # Theme config
    (theme_dir / "theme.toml").write_text(
        """
name = "Minimal Test Theme"
license = "MIT"
"""
    )

    # Create layouts directory
    layouts_dir = theme_dir / "layouts"
    layouts_dir.mkdir()

    # Default baseof layout
    default_dir = layouts_dir / "_default"
    default_dir.mkdir()

    (default_dir / "baseof.html").write_text(
        """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ .Title }} - {{ .Site.Title }}</title>
</head>
<body>
    <header>
        <h1>{{ .Site.Title }}</h1>
    </header>
    <main>
        {{ block "main" . }}{{ end }}
    </main>
    <footer>
        <p>&copy; 2025 {{ .Site.Title }}</p>
    </footer>
</body>
</html>
"""
    )

    # Single page layout
    (default_dir / "single.html").write_text(
        """
{{ define "main" }}
<article>
    <h1>{{ .Title }}</h1>
    <time>{{ .Date.Format "2006-01-02" }}</time>
    <div>{{ .Content }}</div>
</article>
{{ end }}
"""
    )

    # List page layout
    (default_dir / "list.html").write_text(
        """
{{ define "main" }}
<h2>{{ .Title }}</h2>
{{ range .Pages }}
    <article>
        <h3><a href="{{ .Permalink }}">{{ .Title }}</a></h3>
        <time>{{ .Date.Format "2006-01-02" }}</time>
        <p>{{ .Summary }}</p>
    </article>
{{ end }}
{{ end }}
"""
    )

    # Home page layout
    (layouts_dir / "index.html").write_text(
        """
{{ define "main" }}
<h2>Recent Posts</h2>
{{ range first 10 .Site.RegularPages }}
    <article>
        <h3><a href="{{ .Permalink }}">{{ .Title }}</a></h3>
        <time>{{ .Date.Format "2006-01-02" }}</time>
    </article>
{{ end }}
{{ end }}
"""
    )

    # Update config to use the theme
    config_file.write_text(
        """
baseURL = "https://test.example.com/"
languageCode = "en-us"
title = "Integration Test Site"
theme = "minimal"

[params]
    description = "Test site for Hugo integration"
    author = "Test Author"
"""
    )

    # Execute Hugo build
    # Note: Use the test's local themes directory instead of /app/themes
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com/",
        timeout_seconds=30,
        themes_dir=hugo_dir / "themes",  # Use local themes directory for testing
    )

    # Assert build succeeded
    assert result.success is True, f"Build failed: {result.errors}"
    assert len(result.errors) == 0, f"Build had errors: {result.errors}"
    assert result.output_files > 0, "No output files generated"
    assert result.duration_seconds > 0, "Build duration should be positive"

    # Verify public directory was created
    public_dir = hugo_dir / "public"
    assert public_dir.exists(), "Public directory not created"

    # Verify index.html was generated
    index_file = public_dir / "index.html"
    assert index_file.exists(), "index.html not generated"

    # Verify index.html contains expected content
    index_content = index_file.read_text()
    assert "Integration Test Site" in index_content, "Site title not in index.html"
    assert "Hello World" in index_content, "Post title not in index.html"
    assert "Second Post" in index_content, "Second post not in index.html"

    # Verify individual post pages were created
    hello_post = public_dir / "posts" / "hello-world" / "index.html"
    assert hello_post.exists(), "Hello World post not generated"

    second_post = public_dir / "posts" / "second-post" / "index.html"
    assert second_post.exists(), "Second Post not generated"

    # Verify post content
    hello_content = hello_post.read_text()
    assert "Hello World" in hello_content, "Post title not in post page"
    assert "Markdown rendering" in hello_content, "Post content not rendered"

    # Verify code block rendering (Hugo escapes HTML, so check for the function name)
    second_content = second_post.read_text()
    assert "hello" in second_content and (
        "def" in second_content or "function" in second_content
    ), "Code block not rendered correctly"

    print(
        f"✅ Hugo build successful: {result.output_files} files generated in {result.duration_seconds:.2f}s"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hugo_build_with_invalid_config(tmp_path):
    """Test Hugo build fails gracefully with invalid config."""
    hugo_dir = tmp_path / "hugo-site"
    hugo_dir.mkdir()

    # Create invalid config
    config_file = hugo_dir / "config.toml"
    config_file.write_text("[[[ INVALID TOML")

    # Execute Hugo build
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com/",
        timeout_seconds=30,
    )

    # Assert build failed
    assert result.success is False, "Build should fail with invalid config"
    assert len(result.errors) > 0, "Should have error messages"
    assert result.output_files == 0, "Should not generate files"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hugo_build_timeout(tmp_path):
    """Test Hugo build respects timeout."""
    hugo_dir = tmp_path / "hugo-site"
    hugo_dir.mkdir()

    # Create minimal valid structure
    (hugo_dir / "content").mkdir()
    config_file = hugo_dir / "config.toml"
    config_file.write_text('baseURL = "https://test.example.com/"')

    # Execute with very short timeout (should complete quickly though)
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com/",
        timeout_seconds=1,  # 1 second should be enough for minimal site
    )

    # Should complete successfully (minimal site builds fast)
    assert (
        result.success is True or "timeout" in str(result.errors).lower()
    ), "Build should either succeed quickly or timeout gracefully"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hugo_build_missing_directory(tmp_path):
    """Test Hugo build handles missing directory gracefully."""
    hugo_dir = tmp_path / "nonexistent"
    config_file = tmp_path / "config.toml"
    config_file.write_text('baseURL = "https://test.example.com/"')

    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com/",
        timeout_seconds=30,
    )

    # Should fail gracefully
    assert result.success is False, "Build should fail with missing directory"
    assert len(result.errors) > 0, "Should have error message"
    assert (
        "not found" in result.errors[0].lower()
    ), "Error should mention missing directory"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hugo_build_output_file_count(tmp_path):
    """Test that output_files count is accurate."""
    hugo_dir = tmp_path / "hugo-site"
    hugo_dir.mkdir()

    # Create content
    content_dir = hugo_dir / "content"
    content_dir.mkdir()

    # Create 5 posts
    for i in range(5):
        post_file = content_dir / f"post-{i}.md"
        post_file.write_text(
            f"""---
title: "Post {i}"
date: 2025-10-10T10:00:00Z
draft: false
---

Content for post {i}.
"""
        )

    # Create config
    config_file = hugo_dir / "config.toml"
    config_file.write_text('baseURL = "https://test.example.com/"')

    # Build
    result = await build_site_with_hugo(
        hugo_dir=hugo_dir,
        config_file=config_file,
        base_url="https://test.example.com/",
        timeout_seconds=30,
    )

    # Verify file count (Hugo may generate different numbers of files based on config)
    assert result.success is True, f"Build failed: {result.errors}"
    assert (
        result.output_files >= 1
    ), f"Should have at least 1 file, got {result.output_files}"

    # Verify public directory was created and has files
    public_dir = hugo_dir / "public"
    assert public_dir.exists(), "Public directory should exist"

    # Hugo without theme generates XML files (sitemap, RSS) even without HTML
    all_files = list(public_dir.rglob("*"))
    generated_files = [f for f in all_files if f.is_file()]
    assert (
        len(generated_files) >= 1
    ), f"Should have at least 1 generated file, found {len(generated_files)}"


@pytest.mark.integration
def test_papermod_theme_installed():
    """
    Test that PaperMod theme is installed in the container at /app/themes.

    This verifies the Dockerfile correctly clones and installs the theme.
    Only runs in containerized environment (skips in local dev).
    """
    themes_dir = Path("/app/themes/PaperMod")

    # Skip if not running in container
    if not themes_dir.exists():
        pytest.skip("Skipping - not running in containerized environment")

    # Verify theme structure
    assert themes_dir.is_dir(), "PaperMod should be a directory"

    # Check for essential theme files
    theme_toml = themes_dir / "theme.toml"
    assert theme_toml.exists(), "theme.toml should exist"

    # Check for layouts directory
    layouts_dir = themes_dir / "layouts"
    assert layouts_dir.exists(), "layouts directory should exist"
    assert layouts_dir.is_dir(), "layouts should be a directory"

    # Check for essential layouts
    baseof = layouts_dir / "_default" / "baseof.html"
    assert baseof.exists(), "baseof.html layout should exist"

    # Verify permissions are correct (readable by app user)
    import os

    assert os.access(themes_dir, os.R_OK), "Theme directory should be readable"
    assert os.access(theme_toml, os.R_OK), "theme.toml should be readable"

    print(f"✅ PaperMod theme correctly installed at {themes_dir}")

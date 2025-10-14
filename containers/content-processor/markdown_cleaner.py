"""
Markdown post-processing utilities for AI-generated content.

This module provides functions to clean up and fix common issues in
AI-generated markdown, particularly malformed headings that should be paragraphs.

NOTE: This is different from markdown-generator's markdown_processor.py:
- markdown_cleaner.py (content-processor): Fixes/cleans AI-generated markdown
- markdown_processor.py (markdown-generator): Processes markdown for Hugo output

Both work with markdown but serve different purposes in the pipeline.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Optional markdown processing library
try:
    import mistune

    MISTUNE_AVAILABLE = True
except ImportError:
    MISTUNE_AVAILABLE = False
    logger.debug("mistune not available, markdown processing will use regex fallback")


def fix_malformed_headings(content: str) -> str:
    """
    Fix malformed markdown headings that should be paragraphs.

    Uses mistune to parse markdown AST and identify headings that are:
    1. Too long (>100 characters) - likely paragraphs mistakenly formatted as headings
    2. Start with conclusion phrases - should be paragraph text, not headings

    Args:
        content: Raw markdown content from AI

    Returns:
        Cleaned markdown with proper heading structure
    """
    if not MISTUNE_AVAILABLE:
        logger.debug("Using regex fallback for heading cleanup")
        return _fix_malformed_headings_regex(content)

    try:
        # Parse markdown into AST
        markdown = mistune.create_markdown(renderer="ast")
        ast = markdown(content)

        # Process AST to fix malformed headings
        fixed_ast = _process_ast_headings(ast)

        # Render back to markdown
        renderer = mistune.create_markdown(renderer=None)
        return renderer(fixed_ast)

    except Exception as e:
        logger.warning(f"Markdown AST processing failed: {e}, using regex fallback")
        return _fix_malformed_headings_regex(content)


def _process_ast_headings(ast: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process markdown AST to convert malformed headings to paragraphs.

    Args:
        ast: Mistune AST nodes

    Returns:
        Processed AST with fixed headings
    """
    conclusion_starters = [
        "In conclusion",
        "Ultimately",
        "In summary",
        "To sum up",
        "All in all",
        "Overall",
        "In the end",
        "Finally",
    ]

    fixed_nodes = []
    for node in ast:
        if node["type"] == "heading" and node["attrs"]["level"] == 2:
            # Extract text from heading
            heading_text = _extract_text_from_node(node)

            # Check if heading should be a paragraph
            is_too_long = len(heading_text) > 100
            is_conclusion_paragraph = any(
                heading_text.startswith(starter) for starter in conclusion_starters
            )

            if is_too_long or is_conclusion_paragraph:
                # Convert heading to paragraph
                paragraph_node = {"type": "paragraph", "children": node["children"]}
                fixed_nodes.append(paragraph_node)
                logger.debug(
                    f"Converted malformed H2 to paragraph: {heading_text[:50]}..."
                )
            else:
                fixed_nodes.append(node)
        else:
            fixed_nodes.append(node)

    return fixed_nodes


def _extract_text_from_node(node: Dict[str, Any]) -> str:
    """Extract plain text from AST node recursively."""
    if "children" in node:
        return "".join(_extract_text_from_node(child) for child in node["children"])
    elif "raw" in node:
        return node["raw"]
    return ""


def _fix_malformed_headings_regex(content: str) -> str:
    """
    Regex fallback for fixing malformed headings (when mistune unavailable).

    Args:
        content: Raw markdown content

    Returns:
        Cleaned markdown
    """
    lines = content.split("\n")
    cleaned_lines = []

    conclusion_starters = [
        "In conclusion,",
        "Ultimately,",
        "In summary,",
        "To sum up,",
        "All in all,",
        "Overall,",
        "In the end,",
        "Finally,",
    ]

    for line in lines:
        # Check if line is an H2 heading
        if line.startswith("## "):
            heading_text = line[3:].strip()

            # Check if heading should be a paragraph
            is_too_long = len(heading_text) > 100
            is_conclusion_paragraph = any(
                heading_text.startswith(starter) for starter in conclusion_starters
            )

            if is_too_long or is_conclusion_paragraph:
                # Convert to paragraph (remove ##)
                cleaned_lines.append(heading_text)
                logger.debug(
                    f"Converted malformed H2 to paragraph: {heading_text[:50]}..."
                )
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

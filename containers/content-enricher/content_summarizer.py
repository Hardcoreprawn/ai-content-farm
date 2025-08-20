"""
Content Summarization Module

Simple extractive summarization - just takes the first sentences.
No complex NLP, keeps it reliable and fast.
"""

import re
from typing import Any, Dict


def generate_summary(content: Dict[str, Any], max_length: int = 200) -> Dict[str, Any]:
    """
    Generate a simple extractive summary from content.

    Args:
        content: Content dictionary with title and content fields
        max_length: Maximum length of summary in characters

    Returns:
        Dictionary with summary and metadata
    """
    title = content.get("title", "")
    content_text = content.get("content", "")

    if not content_text.strip():
        return {
            "summary": title[:max_length] if title else "",
            "summary_length": len(title) if title else 0,
            "compression_ratio": 0.0,
            "method": "title_only",
        }

    # Clean up the content text
    text = content_text.strip()

    # Split into sentences (simple approach)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return {
            "summary": title[:max_length] if title else "",
            "summary_length": len(title) if title else 0,
            "compression_ratio": 0.0,
            "method": "title_only",
        }

    # Take first few sentences until we hit max_length
    summary_parts = []
    current_length = 0

    for sentence in sentences:
        # Add period back if it doesn't end with punctuation
        if not sentence.endswith((".", "!", "?")):
            sentence += "."

        if current_length + len(sentence) + 1 <= max_length:
            summary_parts.append(sentence)
            current_length += len(sentence) + 1  # +1 for space
        else:
            break

    if not summary_parts:
        # If first sentence is too long, truncate it
        first_sentence = sentences[0]
        if not first_sentence.endswith((".", "!", "?")):
            first_sentence += "."
        summary = (
            first_sentence[: max_length - 3] + "..."
            if len(first_sentence) > max_length
            else first_sentence
        )
    else:
        summary = " ".join(summary_parts)

    # Calculate compression ratio
    original_length = len(content_text)
    summary_length = len(summary)
    compression_ratio = (
        1.0 - (summary_length / original_length) if original_length > 0 else 0.0
    )

    return {
        "summary": summary,
        "summary_length": summary_length,
        "compression_ratio": compression_ratio,
        "method": "extractive",
    }

"""
Quick test to verify strict_mode parameter works in quality checking.
Tests permissive vs strict quality review modes.
"""

from quality.review import review_item


def test_permissive_mode_accepts_generic_content():
    """Verify permissive mode accepts content without technical keywords."""
    item = {
        "id": "test_001",
        "title": "A pleasant morning walk in the park",
        "content": "This morning I took a wonderful walk through the local park. The weather was perfect, the birds were singing, and I felt refreshed.",
        "source": "mastodon",
        "collected_at": "2025-10-24T10:30:00Z",
        "metadata": {"instance": "fosstodon.org"},
    }

    # In permissive mode, should PASS (no technical keywords required)
    passes, reason = review_item(item, strict_mode=False)
    print(f"✅ Permissive mode result: passes={passes}, reason={reason}")
    assert passes is True, f"Expected to pass in permissive mode, got: {reason}"

    # In strict mode, should FAIL (no technical keywords)
    passes, reason = review_item(item, strict_mode=True)
    print(f"❌ Strict mode result: passes={passes}, reason={reason}")
    assert passes is False, f"Expected to fail in strict mode due to {reason}"


def test_strict_mode_rejects_non_technical():
    """Verify strict mode rejects non-technical content."""
    item = {
        "id": "test_002",
        "title": "Best pizza recipes for dinner tonight",
        "content": "Here are my top 5 pizza recipes that will make your family dinner amazing. The first one uses fresh basil and mozzarella.",
        "source": "mastodon",
        "collected_at": "2025-10-24T10:30:00Z",
        "metadata": {"instance": "techhub.social"},
    }

    passes, reason = review_item(item, strict_mode=True)
    print(f"Strict mode on non-tech: passes={passes}, reason={reason}")
    assert passes is False, f"Expected strict mode to reject this"


def test_strict_mode_accepts_technical_content():
    """Verify strict mode accepts technical content."""
    item = {
        "id": "test_003",
        "title": "Building scalable APIs with Python and FastAPI frameworks",
        "content": "In this article we explore how to build production-grade REST APIs using Python and the FastAPI framework. We cover authentication, database integration, and deployment strategies.",
        "source": "mastodon",
        "collected_at": "2025-10-24T10:30:00Z",
        "metadata": {"instance": "techhub.social"},
    }

    passes, reason = review_item(item, strict_mode=True)
    print(f"Strict mode on tech content: passes={passes}, reason={reason}")
    assert (
        passes is True
    ), f"Expected strict mode to accept technical content, got: {reason}"


def test_content_validation_still_applies():
    """Verify basic validation rules apply in both modes."""
    item = {
        "id": "test_004",
        "title": "Hi",  # Too short
        "content": "Short",  # Too short
        "source": "mastodon",
        "collected_at": "2025-10-24T10:30:00Z",
        "metadata": {"instance": "fosstodon.org"},
    }

    # Even permissive mode should reject too-short content
    passes, reason = review_item(item, strict_mode=False)
    print(f"Permissive mode on short content: passes={passes}, reason={reason}")
    assert passes is False, f"Expected to reject short content"


if __name__ == "__main__":
    print("Testing quality review modes...\n")
    test_permissive_mode_accepts_generic_content()
    print()
    test_strict_mode_rejects_non_technical()
    print()
    test_strict_mode_accepts_technical_content()
    print()
    test_content_validation_still_applies()
    print("\n✅ All quality mode tests passed!")

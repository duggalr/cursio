"""
Core utility tests — slugify, scene names extraction, model validation.

These test pure functions that don't require external services.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Slugify ────────────────────────────────────────────────────────


def test_worker_slugify():
    """Worker's url_slugify produces clean URL slugs."""
    from web.backend.worker import url_slugify

    assert url_slugify("The Point of No Return") == "the-point-of-no-return"
    assert url_slugify("Why 0.999... Equals 1") == "why-0999-equals-1"
    assert url_slugify("ARM vs x86: The $100K Decision") == "arm-vs-x86-the-100k-decision"
    assert url_slugify("  Extra   Spaces  ") == "extra-spaces"


def test_slugify_truncation():
    """Slugify truncates to 80 chars."""
    from web.backend.worker import url_slugify

    long_title = "A" * 200
    slug = url_slugify(long_title)
    assert len(slug) <= 80


def test_slugify_special_chars():
    """Slugify strips special characters."""
    from web.backend.worker import url_slugify

    assert url_slugify("Hello! @World# $Test%") == "hello-world-test"
    assert url_slugify("café résumé") == "caf-rsum"  # strips accented chars


# ─── Scene Name Extraction ──────────────────────────────────────────


def test_get_scene_names():
    """get_scene_names extracts Scene class names from Manim code."""
    from core.renderer import get_scene_names

    code = '''
from manim import *

class Scene01(Scene):
    def construct(self):
        pass

class Scene02(Scene):
    def construct(self):
        pass

class HelperClass:
    pass
'''
    names = get_scene_names(code)
    assert names == ["Scene01", "Scene02"]


def test_get_scene_names_empty():
    """get_scene_names returns empty list for code without Scene classes."""
    from core.renderer import get_scene_names

    assert get_scene_names("x = 1") == []
    assert get_scene_names("class Foo(Bar): pass") == []


# ─── CLI Slugify ────────────────────────────────────────────────────


def test_cli_slugify():
    """CLI generate.py slugify works correctly."""
    from generate import slugify

    assert slugify("How Gravity Works") == "how_gravity_works"
    assert len(slugify("A" * 200)) <= 60


# ─── Model Validation ──────────────────────────────────────────────


def test_duration_profile_enum():
    """DurationProfile enum has expected values."""
    from web.backend.models import DurationProfile

    assert DurationProfile.short.value == "short"
    assert DurationProfile.medium.value == "medium"
    assert DurationProfile.long.value == "long"


def test_job_status_model():
    """JobStatus model accepts all required fields."""
    from web.backend.models import JobStatus

    j = JobStatus(id="1", status="rendering", created_at="2024-01-01")
    assert j.status == "rendering"
    assert j.video_id is None
    assert j.error_message is None

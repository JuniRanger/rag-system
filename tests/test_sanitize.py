import pytest

from app.core.sanitize import (
    SanitizeError,
    clamp_limit,
    escape_like_pattern,
    ilike_contains,
    sanitize_cita_fecha,
    sanitize_identifier,
    sanitize_relative_path,
    sanitize_text,
)


def test_escape_like_pattern_escapes_wildcards():
    assert escape_like_pattern("100%") == "100"
    assert escape_like_pattern("a_b") == "ab"
    assert escape_like_pattern("%_%") == ""


def test_ilike_contains_wraps_and_escapes():
    assert ilike_contains("Mazda_3%") == "%Mazda3%"
    with pytest.raises(SanitizeError):
        ilike_contains("%%%")


def test_sanitize_text_rejects_empty_and_too_long():
    with pytest.raises(SanitizeError):
        sanitize_text("   ", field="marca")
    with pytest.raises(SanitizeError):
        sanitize_text("x" * 201, field="marca", max_length=200)


def test_sanitize_identifier_allows_safe_names():
    assert sanitize_identifier("repair_reports") == "repair_reports"
    with pytest.raises(SanitizeError):
        sanitize_identifier("reports; drop table")
    with pytest.raises(SanitizeError):
        sanitize_identifier("../etc/passwd")


def test_sanitize_relative_path_blocks_traversal():
    assert sanitize_relative_path("data/raw") == "data/raw"
    with pytest.raises(SanitizeError):
        sanitize_relative_path("../secrets")
    with pytest.raises(SanitizeError):
        sanitize_relative_path("/etc/passwd")


def test_clamp_limit():
    assert clamp_limit(100) == 20
    assert clamp_limit(0) == 1
    assert clamp_limit("3") == 3
    assert clamp_limit("nope", default=5) == 5


def test_sanitize_cita_fecha():
    assert sanitize_cita_fecha("2026-08-01 09:30") == "2026-08-01 09:30"
    with pytest.raises(SanitizeError):
        sanitize_cita_fecha("mañana a las 10")

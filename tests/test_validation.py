import pytest

from engine import validate_request


def test_minimal_request_defaults_to_full():
    result = validate_request({"style": "pop", "lyrics": "hello"})
    assert result["cot"] == "full"


def test_rejects_abc_in_off_mode():
    with pytest.raises(ValueError, match="abc requires"):
        validate_request({"style": "pop", "lyrics": "hello", "cot": "off", "abc": "X:1"})


def test_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unsupported"):
        validate_request({"style": "pop", "lyrics": "hello", "duration": 120})


def test_style_tags_alias_must_match():
    with pytest.raises(ValueError, match="cannot disagree"):
        validate_request({"style": "pop", "tags": "rock", "lyrics": "hello"})


def test_accepts_sampling_overrides():
    result = validate_request({
        "style": "pop",
        "lyrics": "hello",
        "semantic_sampling": {"min_tokens": 64, "max_tokens": 256},
    })
    assert result["semantic_sampling"]["max_tokens"] == 256


def test_rejects_unknown_sampling_fields():
    with pytest.raises(ValueError, match="unsupported semantic_sampling"):
        validate_request({
            "style": "pop",
            "lyrics": "hello",
            "semantic_sampling": {"duration": 10},
        })

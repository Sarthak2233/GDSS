import pytest

FORBIDDEN_TERMS = [
    "Secret docstring",
    "Feature docstring",
    "Test Author",
    "author@example.com",
    "Detailed message here",
    "Feature commit",
    "function_1():",
    "return 42",
    "return 24",
    'return "new"',
    "def function_2",
]

FORBIDDEN_KEYS = ["body", "docstring", "diff", "patch", "message", "author", "email", "subject"]


def assert_privacy_safe(payload):
    if isinstance(payload, dict):
        for k, v in payload.items():
            for forbidden_key in FORBIDDEN_KEYS:
                assert forbidden_key not in k.lower(), (
                    f"Forbidden key '{forbidden_key}' found in payload: {k}"
                )
            assert_privacy_safe(v)
    elif isinstance(payload, list):
        for item in payload:
            assert_privacy_safe(item)
    elif isinstance(payload, str):
        for term in FORBIDDEN_TERMS:
            # Simple substring check
            assert term not in payload, (
                f"Forbidden term '{term}' found in string payload: {payload}"
            )


def test_assert_privacy_safe_catches_forbidden_key():
    with pytest.raises(AssertionError, match="Forbidden key 'docstring' found"):
        assert_privacy_safe({"docstring": "hello"})


def test_assert_privacy_safe_catches_forbidden_term():
    with pytest.raises(AssertionError, match="Forbidden term 'Secret docstring' found"):
        assert_privacy_safe({"safe_field": "This has a Secret docstring in it"})


def test_assert_privacy_safe_passes():
    assert_privacy_safe({"status": "ok", "data": {"metadata": "yes", "count": 5}})

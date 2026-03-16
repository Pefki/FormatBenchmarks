"""
Test Data Generator
====================
Generates test payloads of different sizes for benchmark comparison.
Each size includes a mix of data types: strings, integers, floats, booleans,
lists, nested objects, and maps.
"""

import random
import string


def _random_string(length: int) -> str:
    """Generate a random string of the specified length."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_test_data(size: str, nesting_depth: int | None = None) -> dict:
    """
    Generate test data for the requested size category.

    Args:
        size: 'small', 'medium', or 'large'
        nesting_depth: Optional target max container depth.

    Returns:
        dict with test data
    """
    # Use a fixed seed for reproducible results
    random.seed(42)

    if nesting_depth is not None:
        return _generate_with_nesting(size, nesting_depth)

    if size == "small":
        return _generate_small()
    elif size == "medium":
        return _generate_medium()
    elif size == "large":
        return _generate_large()
    else:
        raise ValueError(f"Unknown size: {size}. Use 'small', 'medium', or 'large'.")


def _generate_small() -> dict:
    """Small payload ~200-500 bytes."""
    return {
        "id": 1,
        "timestamp": "2026-02-10T12:00:00Z",
        "username": "testuser",
        "email": "test@example.com",
        "content": "Hello, this is a small test message for benchmark purposes.",
        "tags": ["test", "small", "benchmark"],
        "metadata": {"source": "benchmark", "version": "1.0"},
        "score": 95.5,
        "is_active": True,
    }


def _generate_medium() -> dict:
    """Medium payload ~2-5 KB."""
    return {
        "id": 42,
        "timestamp": "2026-02-10T12:00:00Z",
        "username": "benchmark_user_medium",
        "email": "benchmark.medium@example.com",
        "content": _random_string(1000),
        "tags": [_random_string(10) for _ in range(20)],
        "metadata": {_random_string(8): _random_string(20) for _ in range(15)},
        "score": 87.123456,
        "is_active": True,
        "nested_data": {
            "field1": _random_string(100),
            "field2": 12345,
            "values": [random.uniform(0, 100) for _ in range(50)],
        },
        "items": [
            {
                "name": _random_string(20),
                "value": random.uniform(0, 1000),
                "active": random.choice([True, False]),
                "description": "",
                "tags": [],
            }
            for _ in range(10)
        ],
    }


def _generate_large() -> dict:
    """Large payload ~20-50 KB."""
    return {
        "id": 99999,
        "timestamp": "2026-02-10T12:00:00Z",
        "username": "benchmark_user_large_payload_test",
        "email": "benchmark.large.payload@example.com",
        "content": _random_string(10000),
        "tags": [_random_string(15) for _ in range(100)],
        "metadata": {_random_string(12): _random_string(50) for _ in range(50)},
        "score": 99.999999,
        "is_active": True,
        "nested_data": {
            "field1": _random_string(500),
            "field2": 9999999,
            "values": [random.uniform(0, 1000) for _ in range(500)],
        },
        "items": [
            {
                "name": _random_string(30),
                "value": random.uniform(0, 10000),
                "active": random.choice([True, False]),
                "description": _random_string(200),
                "tags": [_random_string(8) for _ in range(5)],
            }
            for _ in range(100)
        ],
    }


def _generate_with_nesting(size: str, nesting_depth: int) -> dict:
    """Generate a website-like payload with a specific max container nesting depth."""
    if size not in {"small", "medium", "large"}:
        raise ValueError(f"Unknown size: {size}. Use 'small', 'medium', or 'large'.")
    if nesting_depth < 1:
        raise ValueError("nesting_depth must be >= 1")

    if size == "small":
        content_length = 180
        extras = 1
    elif size == "medium":
        content_length = 2800
        extras = 8
    else:
        content_length = 50000
        extras = 30

    payload = {
        "id": 1001,
        "timestamp": "2026-02-10T12:00:00Z",
        "username": "site_user",
        "email": "site_user@example.com",
        "title": "A normal website message",
        "content": _random_string(content_length),
        "likes": 17,
        "is_published": True,
        "locale": "en-US",
        "priority": "normal",
    }

    for idx in range(extras):
        payload[f"extra_{idx}"] = _random_string(24)

    if nesting_depth >= 2:
        payload["tags"] = [_random_string(8) for _ in range(min(3 + extras, 40))]
        payload["context"] = _build_nested_context(nesting_depth)

    return payload


def _build_nested_context(target_depth: int) -> dict:
    """Build a nested dict branch so root payload reaches target depth exactly."""
    context = {"value": "leaf"}
    for level in range(3, target_depth + 1):
        context = {f"level_{level - 1}": context}
    return context

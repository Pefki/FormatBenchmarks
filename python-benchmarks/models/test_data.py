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


def generate_test_data(size: str) -> dict:
    """
    Generate test data for the requested size category.

    Args:
        size: 'small', 'medium', or 'large'

    Returns:
        dict with test data
    """
    # Use a fixed seed for reproducible results
    random.seed(42)

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

"""
JSON Benchmark
===============
Benchmark for the standard JSON format (text-based).
Uses Python's built-in json module.
"""

import json
from .base_benchmark import BaseBenchmark


class JsonBenchmark(BaseBenchmark):
    """Benchmark for JSON serialization/deserialization."""

    @property
    def format_name(self) -> str:
        return "JSON"

    def serialize(self, data: dict) -> bytes:
        """Serialize dict to JSON bytes (UTF-8)."""
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def deserialize(self, payload: bytes) -> dict:
        """Deserialize JSON bytes to dict."""
        return json.loads(payload.decode("utf-8"))

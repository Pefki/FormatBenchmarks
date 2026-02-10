"""
JSON Benchmark
===============
Benchmark voor het standaard JSON format (text-based).
Gebruikt de ingebouwde Python json module.
"""

import json
from .base_benchmark import BaseBenchmark


class JsonBenchmark(BaseBenchmark):
    """Benchmark voor JSON serialisatie/deserialisatie."""

    @property
    def format_name(self) -> str:
        return "JSON"

    def serialize(self, data: dict) -> bytes:
        """Serialiseer dict naar JSON bytes (UTF-8)."""
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer JSON bytes naar dict."""
        return json.loads(payload.decode("utf-8"))

"""
BSON Benchmark
===============
Benchmark for the BSON (Binary JSON) format.
Uses the bson module from pymongo.

BSON is the binary format used internally by MongoDB.
It supports additional data types such as datetime, binary, and ObjectId.
"""

import bson
from .base_benchmark import BaseBenchmark


class BsonBenchmark(BaseBenchmark):
    """Benchmark for BSON serialization/deserialization."""

    @property
    def format_name(self) -> str:
        return "BSON"

    def serialize(self, data: dict) -> bytes:
        """Serialize dict to BSON bytes."""
        return bson.encode(data)

    def deserialize(self, payload: bytes) -> dict:
        """Deserialize BSON bytes to dict."""
        return bson.decode(payload)

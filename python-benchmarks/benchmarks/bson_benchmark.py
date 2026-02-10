"""
BSON Benchmark
===============
Benchmark voor het BSON (Binary JSON) format.
Gebruikt de bson module van pymongo.

BSON is het binary format dat MongoDB intern gebruikt.
Het ondersteunt extra datatypes zoals datetime, binary, en ObjectId.
"""

import bson
from .base_benchmark import BaseBenchmark


class BsonBenchmark(BaseBenchmark):
    """Benchmark voor BSON serialisatie/deserialisatie."""

    @property
    def format_name(self) -> str:
        return "BSON"

    def serialize(self, data: dict) -> bytes:
        """Serialiseer dict naar BSON bytes."""
        return bson.encode(data)

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer BSON bytes naar dict."""
        return bson.decode(payload)

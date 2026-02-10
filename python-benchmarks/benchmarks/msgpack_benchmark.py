"""
MessagePack Benchmark
======================
Benchmark voor MessagePack, een efficiënt binary serialisatie format.

MessagePack is "like JSON but fast and small". Het is schema-loos
en kan direct Python dicts serialiseren, vergelijkbaar met JSON
maar in een compact binary formaat.
"""

import msgpack
from .base_benchmark import BaseBenchmark


class MsgpackBenchmark(BaseBenchmark):
    """Benchmark voor MessagePack serialisatie/deserialisatie."""

    @property
    def format_name(self) -> str:
        return "MessagePack"

    def serialize(self, data: dict) -> bytes:
        """Serialiseer dict naar MessagePack bytes."""
        return msgpack.packb(data, use_bin_type=True)

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer MessagePack bytes naar dict."""
        return msgpack.unpackb(payload, raw=False)

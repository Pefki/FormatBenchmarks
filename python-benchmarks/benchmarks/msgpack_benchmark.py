"""
MessagePack Benchmark
======================
Benchmark for MessagePack, an efficient binary serialization format.

MessagePack is "like JSON but fast and small". It is schemaless
and can directly serialize Python dicts, similar to JSON
but in a compact binary format.
"""

import msgpack
from .base_benchmark import BaseBenchmark


class MsgpackBenchmark(BaseBenchmark):
    """Benchmark for MessagePack serialization/deserialization."""

    @property
    def format_name(self) -> str:
        return "MessagePack"

    def serialize(self, data: dict) -> bytes:
        """Serialize dict to MessagePack bytes."""
        return msgpack.packb(data, use_bin_type=True)

    def deserialize(self, payload: bytes) -> dict:
        """Deserialize MessagePack bytes to dict."""
        return msgpack.unpackb(payload, raw=False)

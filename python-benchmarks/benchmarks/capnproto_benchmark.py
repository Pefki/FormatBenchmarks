"""
Cap'n Proto Benchmark
======================
Benchmark voor Cap'n Proto, een zero-copy message format.

Cap'n Proto is uniek omdat het geen serialisatie/deserialisatie stap heeft -
het wire format IS het in-memory format. Dit maakt het extreem snel
voor lees-intensieve workloads.

Vereist:
- capnproto C++ runtime: sudo apt-get install capnproto libcapnp-dev
- pycapnp: pip install pycapnp
"""

import os
import capnp

from .base_benchmark import BaseBenchmark

_SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "schemas", "message.capnp")
)


class CapnProtoBenchmark(BaseBenchmark):
    """Benchmark voor Cap'n Proto serialisatie/deserialisatie."""

    def __init__(self):
        self._module = capnp.load(_SCHEMA_PATH)

    @property
    def format_name(self) -> str:
        return "Cap'n Proto"

    def serialize(self, data: dict) -> bytes:
        """Bouw een Cap'n Proto message en serialiseer naar bytes."""
        msg = self._module.BenchmarkMessage.new_message()
        self._fill_message(msg, data)
        return msg.to_bytes()

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer bytes naar Cap'n Proto message en lees alle velden."""
        with self._module.BenchmarkMessage.from_bytes(
            payload, traversal_limit_in_words=2**64 - 1
        ) as msg:
            return self._to_dict(msg)

    def _fill_message(self, msg, data: dict):
        """Vul een Cap'n Proto message vanuit een Python dict."""
        msg.id = data.get("id", 0)
        msg.timestamp = data.get("timestamp", "")
        msg.username = data.get("username", "")
        msg.email = data.get("email", "")
        msg.content = data.get("content", "")
        msg.score = float(data.get("score", 0.0))
        msg.isActive = data.get("is_active", False)

        # Tags
        tags = data.get("tags", [])
        msg.init("tags", len(tags))
        for i, tag in enumerate(tags):
            msg.tags[i] = tag

        # Metadata (als KeyValue lijst)
        metadata = data.get("metadata", {})
        msg.init("metadata", len(metadata))
        for i, (k, v) in enumerate(metadata.items()):
            msg.metadata[i].key = str(k)
            msg.metadata[i].value = str(v)

        # Nested data
        if "nested_data" in data and data["nested_data"]:
            nd = data["nested_data"]
            msg.nestedData.field1 = nd.get("field1", "")
            msg.nestedData.field2 = nd.get("field2", 0)
            values = nd.get("values", [])
            msg.nestedData.init("values", len(values))
            for i, v in enumerate(values):
                msg.nestedData.values[i] = float(v)

        # Items
        items = data.get("items", [])
        msg.init("items", len(items))
        for i, item in enumerate(items):
            msg.items[i].name = item.get("name", "")
            msg.items[i].value = float(item.get("value", 0.0))
            msg.items[i].active = item.get("active", False)
            msg.items[i].description = item.get("description", "")
            item_tags = item.get("tags", [])
            msg.items[i].init("tags", len(item_tags))
            for j, t in enumerate(item_tags):
                msg.items[i].tags[j] = t

    def _to_dict(self, msg) -> dict:
        """Converteer een Cap'n Proto message naar een Python dict."""
        result = {
            "id": msg.id,
            "timestamp": msg.timestamp,
            "username": msg.username,
            "email": msg.email,
            "content": msg.content,
            "tags": [str(t) for t in msg.tags],
            "metadata": {kv.key: kv.value for kv in msg.metadata},
            "score": msg.score,
            "is_active": msg.isActive,
        }

        # Nested data
        try:
            nd = msg.nestedData
            result["nested_data"] = {
                "field1": nd.field1,
                "field2": nd.field2,
                "values": [float(v) for v in nd.values],
            }
        except Exception:
            pass

        # Items
        result["items"] = [
            {
                "name": item.name,
                "value": item.value,
                "active": item.active,
                "description": item.description,
                "tags": [str(t) for t in item.tags],
            }
            for item in msg.items
        ]

        return result

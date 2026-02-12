"""
Apache Avro Benchmark
======================
Benchmark for Apache Avro, a schema-based binary format.

Avro was developed for Apache Hadoop and is popular in data engineering
and event streaming (Kafka). The schema is stored separately from data
and supports schema evolution.

Uses fastavro for a fast Python implementation.
"""

import io
import json
import os

import fastavro

from .base_benchmark import BaseBenchmark

_SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "schemas", "message.avsc")
)


class AvroBenchmark(BaseBenchmark):
    """Benchmark for Apache Avro serialization/deserialization."""

    def __init__(self):
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_dict = json.load(f)
        self._schema = fastavro.parse_schema(schema_dict)

    @property
    def format_name(self) -> str:
        return "Apache Avro"

    def _prepare_data(self, data: dict) -> dict:
        """
        Prepare data so it fits the Avro schema.
        Avro requires union types to be provided correctly.
        """
        prepared = dict(data)

        # nested_data is a union ["null", NestedData] in the schema
        if "nested_data" not in prepared or prepared["nested_data"] is None:
            prepared["nested_data"] = None

        # items: ensure each item has all fields
        if "items" in prepared:
            for item in prepared["items"]:
                if "description" not in item:
                    item["description"] = None
                if "tags" not in item:
                    item["tags"] = []
        else:
            prepared["items"] = []

        return prepared

    def serialize(self, data: dict) -> bytes:
        """Serialize dict to Avro binary (schemaless writer)."""
        prepared = self._prepare_data(data)
        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, self._schema, prepared)
        return buf.getvalue()

    def deserialize(self, payload: bytes) -> dict:
        """Deserialize Avro binary to dict (schemaless reader)."""
        buf = io.BytesIO(payload)
        return fastavro.schemaless_reader(buf, self._schema)

"""
Apache Avro Benchmark
======================
Benchmark voor Apache Avro, een schema-gebaseerd binary format.

Avro is ontwikkeld voor Apache Hadoop en is populair in data engineering
en event streaming (Kafka). Het schema wordt apart van de data opgeslagen
en ondersteunt schema evolutie.

Gebruikt fastavro voor snelle Python implementatie.
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
    """Benchmark voor Apache Avro serialisatie/deserialisatie."""

    def __init__(self):
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_dict = json.load(f)
        self._schema = fastavro.parse_schema(schema_dict)

    @property
    def format_name(self) -> str:
        return "Apache Avro"

    def _prepare_data(self, data: dict) -> dict:
        """
        Bereid data voor zodat het past bij het Avro schema.
        Avro vereist dat union types correct worden aangeboden.
        """
        prepared = dict(data)

        # nested_data is een union ["null", NestedData] in het schema
        if "nested_data" not in prepared or prepared["nested_data"] is None:
            prepared["nested_data"] = None

        # items: zorg dat elk item alle velden heeft
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
        """Serialiseer dict naar Avro binary (schemaless writer)."""
        prepared = self._prepare_data(data)
        buf = io.BytesIO()
        fastavro.schemaless_writer(buf, self._schema, prepared)
        return buf.getvalue()

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer Avro binary naar dict (schemaless reader)."""
        buf = io.BytesIO(payload)
        return fastavro.schemaless_reader(buf, self._schema)

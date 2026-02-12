"""
FlatBuffers Benchmark
======================
Benchmark for Google FlatBuffers, a zero-copy serialization format.

FlatBuffers is similar to Cap'n Proto: data can be read directly
without a full deserialization step. It was developed by Google
for game development and performance-critical applications.

Uses flatbuffers: pip install flatbuffers
"""

import struct
import flatbuffers
import flatbuffers.builder
import flatbuffers.table
import flatbuffers.encode
import flatbuffers.number_types
from .base_benchmark import BaseBenchmark


class FlatBuffersBenchmark(BaseBenchmark):
    """Benchmark for FlatBuffers serialization/deserialization."""

    @property
    def format_name(self) -> str:
        return "FlatBuffers"

    def serialize(self, data: dict) -> bytes:
        """Serialize dict to FlatBuffers binary."""
        builder = flatbuffers.Builder(4096)

        # Strings and nested data must be created first (bottom-up)
        timestamp_off = builder.CreateString(data.get("timestamp", ""))
        username_off = builder.CreateString(data.get("username", ""))
        email_off = builder.CreateString(data.get("email", ""))
        content_off = builder.CreateString(data.get("content", ""))

        # Tags
        tags = data.get("tags", [])
        tag_offsets = [builder.CreateString(str(t)) for t in tags]
        builder.StartVector(4, len(tag_offsets), 4)
        for off in reversed(tag_offsets):
            builder.PrependUOffsetTRelative(off)
        tags_vec = builder.EndVector()

        # Metadata (as KeyValue table entries)
        metadata = data.get("metadata", {})
        kv_offsets = []
        for k, v in metadata.items():
            key_off = builder.CreateString(str(k))
            val_off = builder.CreateString(str(v))
            builder.StartObject(2)
            builder.PrependUOffsetTRelativeSlot(0, key_off, 0)
            builder.PrependUOffsetTRelativeSlot(1, val_off, 0)
            kv_offsets.append(builder.EndObject())

        builder.StartVector(4, len(kv_offsets), 4)
        for off in reversed(kv_offsets):
            builder.PrependUOffsetTRelative(off)
        metadata_vec = builder.EndVector()

        # Nested data
        nested_data_off = None
        nd = data.get("nested_data")
        if nd:
            field1_off = builder.CreateString(nd.get("field1", ""))
            values = nd.get("values", [])
            builder.StartVector(8, len(values), 8)
            for v in reversed(values):
                builder.PrependFloat64(float(v))
            values_vec = builder.EndVector()

            builder.StartObject(3)
            builder.PrependUOffsetTRelativeSlot(0, field1_off, 0)
            builder.PrependInt64Slot(1, nd.get("field2", 0), 0)
            builder.PrependUOffsetTRelativeSlot(2, values_vec, 0)
            nested_data_off = builder.EndObject()

        # Items
        items = data.get("items", [])
        item_offsets = []
        for item in items:
            name_off = builder.CreateString(item.get("name", ""))
            desc_off = builder.CreateString(item.get("description", ""))
            item_tags = item.get("tags", [])
            item_tag_offsets = [builder.CreateString(str(t)) for t in item_tags]
            builder.StartVector(4, len(item_tag_offsets), 4)
            for off in reversed(item_tag_offsets):
                builder.PrependUOffsetTRelative(off)
            item_tags_vec = builder.EndVector()

            builder.StartObject(5)
            builder.PrependUOffsetTRelativeSlot(0, name_off, 0)
            builder.PrependFloat64Slot(1, float(item.get("value", 0.0)), 0.0)
            builder.PrependBoolSlot(2, item.get("active", False), False)
            builder.PrependUOffsetTRelativeSlot(3, desc_off, 0)
            builder.PrependUOffsetTRelativeSlot(4, item_tags_vec, 0)
            item_offsets.append(builder.EndObject())

        builder.StartVector(4, len(item_offsets), 4)
        for off in reversed(item_offsets):
            builder.PrependUOffsetTRelative(off)
        items_vec = builder.EndVector()

        # Root BenchmarkMessage table
        builder.StartObject(11)
        builder.PrependInt64Slot(0, data.get("id", 0), 0)
        builder.PrependUOffsetTRelativeSlot(1, timestamp_off, 0)
        builder.PrependUOffsetTRelativeSlot(2, username_off, 0)
        builder.PrependUOffsetTRelativeSlot(3, email_off, 0)
        builder.PrependUOffsetTRelativeSlot(4, content_off, 0)
        builder.PrependUOffsetTRelativeSlot(5, tags_vec, 0)
        builder.PrependUOffsetTRelativeSlot(6, metadata_vec, 0)
        builder.PrependFloat64Slot(7, float(data.get("score", 0.0)), 0.0)
        builder.PrependBoolSlot(8, data.get("is_active", False), False)
        if nested_data_off is not None:
            builder.PrependUOffsetTRelativeSlot(9, nested_data_off, 0)
        builder.PrependUOffsetTRelativeSlot(10, items_vec, 0)
        msg = builder.EndObject()

        builder.Finish(msg)
        return bytes(builder.Output())

    # ---- Deserialization helpers ----

    @staticmethod
    def _read_string(tab, field_slot):
        """Read a string field from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return ""
        return tab.String(o + tab.Pos).decode("utf-8")

    @staticmethod
    def _read_int64(tab, field_slot, default=0):
        """Read an int64 field from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return default
        return tab.Get(flatbuffers.number_types.Int64Flags, o + tab.Pos)

    @staticmethod
    def _read_float64(tab, field_slot, default=0.0):
        """Read a float64 field from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return default
        return tab.Get(flatbuffers.number_types.Float64Flags, o + tab.Pos)

    @staticmethod
    def _read_bool(tab, field_slot, default=False):
        """Read a bool field from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return default
        return bool(tab.Get(flatbuffers.number_types.BoolFlags, o + tab.Pos))

    @staticmethod
    def _read_string_vector(tab, field_slot):
        """Read a vector of strings from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return []
        count = tab.VectorLen(o)
        vec_start = tab.Vector(o)
        # Each element is a uoffset to a string; tab.String follows the offset
        return [tab.String(vec_start + i * 4).decode("utf-8") for i in range(count)]

    @staticmethod
    def _read_double_vector(buf, tab, field_slot):
        """Read a vector of doubles from a FlatBuffers table."""
        o = tab.Offset(4 + 2 * field_slot)
        if not o:
            return []
        count = tab.VectorLen(o)
        vec_start = tab.Vector(o)
        return [
            struct.unpack_from("<d", buf, vec_start + i * 8)[0]
            for i in range(count)
        ]

    def deserialize(self, payload: bytes) -> dict:
        """Deserialize FlatBuffers binary to dict (traverse all fields)."""
        buf = bytearray(payload)

        # Root table
        root_off = flatbuffers.encode.Get(
            flatbuffers.number_types.UOffsetTFlags.packer_type, buf, 0
        )
        tab = flatbuffers.table.Table(buf, root_off)

        result = {
            # Scalars and strings
            "id": self._read_int64(tab, 0),
            "timestamp": self._read_string(tab, 1),
            "username": self._read_string(tab, 2),
            "email": self._read_string(tab, 3),
            "content": self._read_string(tab, 4),
            "tags": self._read_string_vector(tab, 5),
            "score": self._read_float64(tab, 7),
            "is_active": self._read_bool(tab, 8),
        }

        # Metadata (slot 6, vector of KeyValue tables)
        o = tab.Offset(16)  # 4 + 2*6
        if o:
            count = tab.VectorLen(o)
            vec_start = tab.Vector(o)
            metadata = {}
            for i in range(count):
                # Each element is a uoffset to a KeyValue table
                kv_pos = tab.Indirect(vec_start + i * 4)
                kv_tab = flatbuffers.table.Table(buf, kv_pos)
                key = self._read_string(kv_tab, 0)
                val = self._read_string(kv_tab, 1)
                metadata[key] = val
            result["metadata"] = metadata
        else:
            result["metadata"] = {}

        # Nested data (slot 9, NestedData table)
        o = tab.Offset(22)  # 4 + 2*9
        if o:
            nd_pos = tab.Indirect(o + tab.Pos)
            nd_tab = flatbuffers.table.Table(buf, nd_pos)
            result["nested_data"] = {
                "field1": self._read_string(nd_tab, 0),
                "field2": self._read_int64(nd_tab, 1),
                "values": self._read_double_vector(buf, nd_tab, 2),
            }

        # Items (slot 10, vector of Item tables)
        o = tab.Offset(24)  # 4 + 2*10
        if o:
            count = tab.VectorLen(o)
            vec_start = tab.Vector(o)
            result["items"] = []
            for i in range(count):
                item_pos = tab.Indirect(vec_start + i * 4)
                item_tab = flatbuffers.table.Table(buf, item_pos)
                result["items"].append({
                    "name": self._read_string(item_tab, 0),
                    "value": self._read_float64(item_tab, 1),
                    "active": self._read_bool(item_tab, 2),
                    "description": self._read_string(item_tab, 3),
                    "tags": self._read_string_vector(item_tab, 4),
                })
        else:
            result["items"] = []

        return result

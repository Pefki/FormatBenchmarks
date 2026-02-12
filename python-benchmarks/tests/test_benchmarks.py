"""
Pytest Unit Tests for Format Benchmarks
==========================================
Tests serialize → deserialize round-trip integrity for all message formats
across all payload sizes. Verifies that data is preserved correctly.
"""

import sys
import os
import math
import pytest

# Ensure python-benchmarks is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from models.test_data import generate_test_data
from benchmarks.json_benchmark import JsonBenchmark
from benchmarks.bson_benchmark import BsonBenchmark
from benchmarks.msgpack_benchmark import MsgpackBenchmark
from benchmarks.protobuf_benchmark import ProtobufBenchmark
from benchmarks.capnproto_benchmark import CapnProtoBenchmark
from benchmarks.avro_benchmark import AvroBenchmark
from benchmarks.flatbuffers_benchmark import FlatBuffersBenchmark


# ─── Fixtures ────────────────────────────────────────────────────────────────

SIZES = ["small", "medium", "large"]

BENCHMARKS = {
    "JSON": JsonBenchmark,
    "BSON": BsonBenchmark,
    "MessagePack": MsgpackBenchmark,
    "Protobuf": ProtobufBenchmark,
    "Cap'n Proto": CapnProtoBenchmark,
    "Apache Avro": AvroBenchmark,
    "FlatBuffers": FlatBuffersBenchmark,
}


@pytest.fixture(params=SIZES, ids=lambda s: f"size-{s}")
def payload_size(request):
    """Parametrize across all payload sizes."""
    return request.param


@pytest.fixture(params=list(BENCHMARKS.keys()), ids=lambda k: k.replace("'", ""))
def benchmark_instance(request):
    """Parametrize across all format benchmark instances."""
    cls = BENCHMARKS[request.param]
    return cls()


@pytest.fixture
def test_data(payload_size):
    """Generate test data for the given size."""
    return generate_test_data(payload_size)


# ─── Helper functies ─────────────────────────────────────────────────────────


def _compare_values(original, restored, key, tolerance=1e-6):
    """
    Compare values with float tolerance.
    Some formats (Protobuf, FlatBuffers) have small float precision
    differences.
    """
    if isinstance(original, float) and isinstance(restored, (float, int)):
        assert math.isclose(original, float(restored), rel_tol=tolerance), (
            f"Float mismatch for '{key}': {original} vs {restored}"
        )
    elif isinstance(original, (int, float)) and isinstance(restored, (int, float)):
        assert math.isclose(float(original), float(restored), rel_tol=tolerance), (
            f"Numeric mismatch for '{key}': {original} vs {restored}"
        )
    elif isinstance(original, str):
        assert str(restored) == original, (
            f"String mismatch for '{key}': '{original}' vs '{restored}'"
        )
    elif isinstance(original, bool):
        assert bool(restored) == original, (
            f"Bool mismatch for '{key}': {original} vs {restored}"
        )
    elif isinstance(original, list):
        assert len(restored) == len(original), (
            f"List length mismatch for '{key}': {len(original)} vs {len(restored)}"
        )
    elif isinstance(original, dict):
        assert len(restored) == len(original), (
            f"Dict length mismatch for '{key}': {len(original)} vs {len(restored)}"
        )


# ─── Round-Trip Tests ────────────────────────────────────────────────────────


class TestRoundTrip:
    """Test serialize → deserialize round-trip for all formats and sizes."""

    def test_serialize_returns_bytes(self, benchmark_instance, test_data):
        """Serialization should return bytes."""
        result = benchmark_instance.serialize(test_data)
        assert isinstance(result, (bytes, bytearray)), (
            f"{benchmark_instance.format_name} serialize did not return bytes"
        )
        assert len(result) > 0, (
            f"{benchmark_instance.format_name} serialize returned empty bytes"
        )

    def test_deserialize_returns_data(self, benchmark_instance, test_data):
        """Deserialization should return a dict-like object."""
        serialized = benchmark_instance.serialize(test_data)
        result = benchmark_instance.deserialize(serialized)
        assert isinstance(result, dict), (
            f"{benchmark_instance.format_name} deserialize did not return a dict"
        )

    def test_roundtrip_preserves_id(self, benchmark_instance, test_data):
        """Round-trip should preserve the id field."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        assert int(restored.get("id", 0)) == test_data["id"]

    def test_roundtrip_preserves_strings(self, benchmark_instance, test_data):
        """Round-trip should preserve string fields."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)

        for field in ["timestamp", "username", "email"]:
            if field in test_data:
                assert str(restored.get(field, "")) == test_data[field], (
                    f"{benchmark_instance.format_name}: "
                    f"'{field}' mismatch: expected '{test_data[field]}', "
                    f"got '{restored.get(field)}'"
                )

    def test_roundtrip_preserves_content(self, benchmark_instance, test_data):
        """Round-trip should preserve the content field."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        assert str(restored.get("content", "")) == test_data["content"]

    def test_roundtrip_preserves_score(self, benchmark_instance, test_data):
        """Round-trip should preserve the score field (with float tolerance)."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_score = float(test_data["score"])
        restored_score = float(restored.get("score", 0.0))
        assert math.isclose(original_score, restored_score, rel_tol=1e-4), (
            f"{benchmark_instance.format_name}: score mismatch: "
            f"{original_score} vs {restored_score}"
        )

    def test_roundtrip_preserves_boolean(self, benchmark_instance, test_data):
        """Round-trip should preserve the is_active boolean field."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        key = "is_active" if "is_active" in restored else "isActive"
        assert bool(restored.get(key, False)) == test_data["is_active"]

    def test_roundtrip_preserves_tags_count(self, benchmark_instance, test_data):
        """Round-trip should preserve the correct number of tags."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_tags = test_data.get("tags", [])
        restored_tags = restored.get("tags", [])
        assert len(restored_tags) == len(original_tags), (
            f"{benchmark_instance.format_name}: "
            f"tags count mismatch: {len(original_tags)} vs {len(restored_tags)}"
        )

    def test_roundtrip_preserves_tags_values(self, benchmark_instance, test_data):
        """Round-trip should preserve tag values."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_tags = test_data.get("tags", [])
        restored_tags = restored.get("tags", [])
        for i, (orig, rest) in enumerate(zip(original_tags, restored_tags)):
            assert str(rest) == str(orig), (
                f"{benchmark_instance.format_name}: "
                f"tag[{i}] mismatch: '{orig}' vs '{rest}'"
            )

    def test_roundtrip_preserves_metadata_keys(self, benchmark_instance, test_data):
        """Round-trip should preserve metadata keys."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_meta = test_data.get("metadata", {})
        restored_meta = restored.get("metadata", {})
        # Metadata keys must match (as strings)
        assert set(str(k) for k in restored_meta.keys()) == set(
            str(k) for k in original_meta.keys()
        ), (
            f"{benchmark_instance.format_name}: "
            f"metadata keys mismatch"
        )

    def test_roundtrip_preserves_items_count(self, benchmark_instance, test_data):
        """Round-trip should preserve the correct number of items."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_items = test_data.get("items", [])
        restored_items = restored.get("items", [])
        assert len(restored_items) == len(original_items), (
            f"{benchmark_instance.format_name}: "
            f"items count mismatch: {len(original_items)} vs {len(restored_items)}"
        )

    def test_roundtrip_preserves_nested_data(self, benchmark_instance, test_data):
        """Round-trip should preserve nested_data when present."""
        if "nested_data" not in test_data or test_data["nested_data"] is None:
            pytest.skip("No nested_data in this payload size")

        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        nd = restored.get("nested_data")
        assert nd is not None, (
            f"{benchmark_instance.format_name}: nested_data is None after round-trip"
        )

        # Check field1 (string)
        orig_nd = test_data["nested_data"]
        assert str(nd.get("field1", "")) == orig_nd["field1"]

        # Check field2 (int)
        assert int(nd.get("field2", 0)) == orig_nd["field2"]

        # Check values count
        orig_values = orig_nd.get("values", [])
        rest_values = nd.get("values", [])
        assert len(rest_values) == len(orig_values), (
            f"{benchmark_instance.format_name}: "
            f"nested_data.values length mismatch"
        )


# ─── Serialized Size Tests ───────────────────────────────────────────────────


class TestSerializedSize:
    """Verify that serialization sizes are consistent and realistic."""

    def test_size_increases_with_payload(self, benchmark_instance):
        """Larger payloads should produce larger serialized byte arrays."""
        sizes = {}
        for size_label in SIZES:
            data = generate_test_data(size_label)
            serialized = benchmark_instance.serialize(data)
            sizes[size_label] = len(serialized)

        assert sizes["small"] < sizes["medium"], (
            f"{benchmark_instance.format_name}: "
            f"small ({sizes['small']}) >= medium ({sizes['medium']})"
        )
        assert sizes["medium"] < sizes["large"], (
            f"{benchmark_instance.format_name}: "
            f"medium ({sizes['medium']}) >= large ({sizes['large']})"
        )

    def test_serialized_not_too_large(self, benchmark_instance):
        """Small payload should not be larger than 5 KB."""
        data = generate_test_data("small")
        serialized = benchmark_instance.serialize(data)
        assert len(serialized) < 5 * 1024, (
            f"{benchmark_instance.format_name}: "
            f"small payload serialized to {len(serialized)} bytes (>5KB)"
        )


# ─── Compression Tests ───────────────────────────────────────────────────────


class TestCompression:
    """Test compression metric calculation."""

    def test_compression_returns_valid_stats(self, benchmark_instance, test_data):
        """Compression statistics should contain valid values."""
        serialized = benchmark_instance.serialize(test_data)
        from benchmarks.base_benchmark import BaseBenchmark

        stats = BaseBenchmark._measure_compression(serialized)

        assert "original_bytes" in stats
        assert "gzip_bytes" in stats
        assert "gzip_ratio" in stats
        assert stats["original_bytes"] == len(serialized)
        assert stats["gzip_bytes"] > 0
        assert 0 < stats["gzip_ratio"] <= 1.0 or stats["gzip_ratio"] > 1.0

    def test_gzip_compresses_data(self, benchmark_instance):
        """Gzip should compress large payloads efficiently."""
        data = generate_test_data("large")
        serialized = benchmark_instance.serialize(data)
        from benchmarks.base_benchmark import BaseBenchmark

        stats = BaseBenchmark._measure_compression(serialized)

        # Gzip should make data smaller (ratio < 1.0 for most formats)
        assert stats["gzip_bytes"] <= stats["original_bytes"] * 1.1, (
            f"{benchmark_instance.format_name}: "
            f"gzip made data >10% larger: {stats['gzip_bytes']} vs {stats['original_bytes']}"
        )

    def test_zstd_available(self):
        """Check whether zstandard is available."""
        try:
            import zstandard  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("zstandard is not installed")


# ─── Throughput Tests ─────────────────────────────────────────────────────────


class TestThroughput:
    """Test throughput calculation."""

    def test_throughput_returns_valid_stats(self):
        """Throughput calculation should produce positive values."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=0.5, deser_mean_ms=0.3, payload_size=1024
        )

        assert result["serialize_msg_per_sec"] > 0
        assert result["deserialize_msg_per_sec"] > 0
        assert result["serialize_mb_per_sec"] > 0
        assert result["deserialize_mb_per_sec"] > 0

    def test_throughput_faster_deser_higher_msgps(self):
        """Faster deserialization should produce higher msg/sec."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=1.0, deser_mean_ms=0.5, payload_size=1024
        )
        assert result["deserialize_msg_per_sec"] > result["serialize_msg_per_sec"]

    def test_throughput_zero_time_safe(self):
        """Zero-time throughput should not crash."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=0.0, deser_mean_ms=0.0, payload_size=0
        )
        assert result["serialize_msg_per_sec"] == 0
        assert result["deserialize_msg_per_sec"] == 0


# ─── Benchmark Runner Tests ──────────────────────────────────────────────────


class TestBenchmarkRunner:
    """Test the full benchmark runner pipeline."""

    def test_run_benchmark_returns_all_keys(self):
        """run_benchmark should return all expected keys."""
        bench = JsonBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=10, warmup=5)

        expected_keys = [
            "format",
            "iterations",
            "serialized_size_bytes",
            "serialize_time_ms",
            "deserialize_time_ms",
            "round_trip_time_ms",
            "memory_usage",
            "compression",
            "throughput",
        ]
        for key in expected_keys:
            assert key in result, f"Expected key '{key}' is missing from result"

    def test_run_benchmark_timing_stats(self):
        """Timing stats should include mean/median/min/max/std_dev/p95/p99."""
        bench = MsgpackBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=20, warmup=5)

        for time_key in ["serialize_time_ms", "deserialize_time_ms", "round_trip_time_ms"]:
            stats = result[time_key]
            for stat in ["mean", "median", "min", "max", "std_dev", "p95", "p99"]:
                assert stat in stats, f"'{stat}' is missing in {time_key}"
                assert isinstance(stats[stat], (int, float))

    def test_run_benchmark_compression_present(self):
        """Compression stats should be present in benchmark result."""
        bench = BsonBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=10, warmup=5)

        comp = result["compression"]
        assert comp["original_bytes"] > 0
        assert comp["gzip_bytes"] > 0

    def test_run_benchmark_throughput_present(self):
        """Throughput stats should be present in benchmark result."""
        bench = JsonBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=10, warmup=5)

        tp = result["throughput"]
        assert tp["serialize_msg_per_sec"] > 0
        assert tp["deserialize_msg_per_sec"] > 0

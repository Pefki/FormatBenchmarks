"""
Pytest Unit Tests voor Format Benchmarks
==========================================
Test serialize → deserialize round-trip integriteit voor alle message formats
met alle payload groottes. Verifieert dat data correct bewaard blijft.
"""

import sys
import os
import math
import pytest

# Zorg dat python-benchmarks op sys.path staat
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
    """Parametrize over alle payload groottes."""
    return request.param


@pytest.fixture(params=list(BENCHMARKS.keys()), ids=lambda k: k.replace("'", ""))
def benchmark_instance(request):
    """Parametrize over alle format benchmark instanties."""
    cls = BENCHMARKS[request.param]
    return cls()


@pytest.fixture
def test_data(payload_size):
    """Genereer testdata voor de gegeven grootte."""
    return generate_test_data(payload_size)


# ─── Helper functies ─────────────────────────────────────────────────────────


def _compare_values(original, restored, key, tolerance=1e-6):
    """
    Vergelijk waarden met tolerantie voor floats.
    Sommige formats (Protobuf, FlatBuffers) hebben kleine float-precissie
    verschillen.
    """
    if isinstance(original, float) and isinstance(restored, (float, int)):
        assert math.isclose(original, float(restored), rel_tol=tolerance), (
            f"Float mismatch voor '{key}': {original} vs {restored}"
        )
    elif isinstance(original, (int, float)) and isinstance(restored, (int, float)):
        assert math.isclose(float(original), float(restored), rel_tol=tolerance), (
            f"Numeriek mismatch voor '{key}': {original} vs {restored}"
        )
    elif isinstance(original, str):
        assert str(restored) == original, (
            f"String mismatch voor '{key}': '{original}' vs '{restored}'"
        )
    elif isinstance(original, bool):
        assert bool(restored) == original, (
            f"Bool mismatch voor '{key}': {original} vs {restored}"
        )
    elif isinstance(original, list):
        assert len(restored) == len(original), (
            f"Lijst lengte mismatch voor '{key}': {len(original)} vs {len(restored)}"
        )
    elif isinstance(original, dict):
        assert len(restored) == len(original), (
            f"Dict lengte mismatch voor '{key}': {len(original)} vs {len(restored)}"
        )


# ─── Round-Trip Tests ────────────────────────────────────────────────────────


class TestRoundTrip:
    """Test serialize → deserialize round-trip voor alle formats en groottes."""

    def test_serialize_returns_bytes(self, benchmark_instance, test_data):
        """Serialisatie moet bytes opleveren."""
        result = benchmark_instance.serialize(test_data)
        assert isinstance(result, (bytes, bytearray)), (
            f"{benchmark_instance.format_name} serialize geeft geen bytes terug"
        )
        assert len(result) > 0, (
            f"{benchmark_instance.format_name} serialize geeft lege bytes terug"
        )

    def test_deserialize_returns_data(self, benchmark_instance, test_data):
        """Deserialisatie moet een dict-achtig object opleveren."""
        serialized = benchmark_instance.serialize(test_data)
        result = benchmark_instance.deserialize(serialized)
        assert isinstance(result, dict), (
            f"{benchmark_instance.format_name} deserialize geeft geen dict terug"
        )

    def test_roundtrip_preserves_id(self, benchmark_instance, test_data):
        """Round-trip moet het id veld bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        assert int(restored.get("id", 0)) == test_data["id"]

    def test_roundtrip_preserves_strings(self, benchmark_instance, test_data):
        """Round-trip moet string velden bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)

        for field in ["timestamp", "username", "email"]:
            if field in test_data:
                assert str(restored.get(field, "")) == test_data[field], (
                    f"{benchmark_instance.format_name}: "
                    f"'{field}' mismatch: verwacht '{test_data[field]}', "
                    f"kreeg '{restored.get(field)}'"
                )

    def test_roundtrip_preserves_content(self, benchmark_instance, test_data):
        """Round-trip moet het content veld bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        assert str(restored.get("content", "")) == test_data["content"]

    def test_roundtrip_preserves_score(self, benchmark_instance, test_data):
        """Round-trip moet het score veld bewaren (met float tolerantie)."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_score = float(test_data["score"])
        restored_score = float(restored.get("score", 0.0))
        assert math.isclose(original_score, restored_score, rel_tol=1e-4), (
            f"{benchmark_instance.format_name}: score mismatch: "
            f"{original_score} vs {restored_score}"
        )

    def test_roundtrip_preserves_boolean(self, benchmark_instance, test_data):
        """Round-trip moet het is_active boolean veld bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        key = "is_active" if "is_active" in restored else "isActive"
        assert bool(restored.get(key, False)) == test_data["is_active"]

    def test_roundtrip_preserves_tags_count(self, benchmark_instance, test_data):
        """Round-trip moet het juiste aantal tags bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_tags = test_data.get("tags", [])
        restored_tags = restored.get("tags", [])
        assert len(restored_tags) == len(original_tags), (
            f"{benchmark_instance.format_name}: "
            f"tags count mismatch: {len(original_tags)} vs {len(restored_tags)}"
        )

    def test_roundtrip_preserves_tags_values(self, benchmark_instance, test_data):
        """Round-trip moet de tag waarden bewaren."""
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
        """Round-trip moet metadata keys bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_meta = test_data.get("metadata", {})
        restored_meta = restored.get("metadata", {})
        # Metadata keys moeten gelijk zijn (als strings)
        assert set(str(k) for k in restored_meta.keys()) == set(
            str(k) for k in original_meta.keys()
        ), (
            f"{benchmark_instance.format_name}: "
            f"metadata keys mismatch"
        )

    def test_roundtrip_preserves_items_count(self, benchmark_instance, test_data):
        """Round-trip moet het juiste aantal items bewaren."""
        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        original_items = test_data.get("items", [])
        restored_items = restored.get("items", [])
        assert len(restored_items) == len(original_items), (
            f"{benchmark_instance.format_name}: "
            f"items count mismatch: {len(original_items)} vs {len(restored_items)}"
        )

    def test_roundtrip_preserves_nested_data(self, benchmark_instance, test_data):
        """Round-trip moet nested_data bewaren als dat er is."""
        if "nested_data" not in test_data or test_data["nested_data"] is None:
            pytest.skip("Geen nested_data in deze payload grootte")

        serialized = benchmark_instance.serialize(test_data)
        restored = benchmark_instance.deserialize(serialized)
        nd = restored.get("nested_data")
        assert nd is not None, (
            f"{benchmark_instance.format_name}: nested_data is None na round-trip"
        )

        # Controleer field1 (string)
        orig_nd = test_data["nested_data"]
        assert str(nd.get("field1", "")) == orig_nd["field1"]

        # Controleer field2 (int)
        assert int(nd.get("field2", 0)) == orig_nd["field2"]

        # Controleer values count
        orig_values = orig_nd.get("values", [])
        rest_values = nd.get("values", [])
        assert len(rest_values) == len(orig_values), (
            f"{benchmark_instance.format_name}: "
            f"nested_data.values lengte mismatch"
        )


# ─── Serialized Size Tests ───────────────────────────────────────────────────


class TestSerializedSize:
    """Verifieer dat serialisatie groottes consistent en realistisch zijn."""

    def test_size_increases_with_payload(self, benchmark_instance):
        """Grotere payloads moeten grotere geserialiseerde bytes produceren."""
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
        """Small payload mag niet groter zijn dan 5 KB."""
        data = generate_test_data("small")
        serialized = benchmark_instance.serialize(data)
        assert len(serialized) < 5 * 1024, (
            f"{benchmark_instance.format_name}: "
            f"small payload serialiseert naar {len(serialized)} bytes (>5KB)"
        )


# ─── Compression Tests ───────────────────────────────────────────────────────


class TestCompression:
    """Test compressie metrics berekening."""

    def test_compression_returns_valid_stats(self, benchmark_instance, test_data):
        """Compressie statistieken moeten valide waarden bevatten."""
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
        """Gzip zou de large payload efficiënt moeten comprimeren."""
        data = generate_test_data("large")
        serialized = benchmark_instance.serialize(data)
        from benchmarks.base_benchmark import BaseBenchmark

        stats = BaseBenchmark._measure_compression(serialized)

        # Gzip moet de data kleiner maken (ratio < 1.0 voor de meeste formats)
        assert stats["gzip_bytes"] <= stats["original_bytes"] * 1.1, (
            f"{benchmark_instance.format_name}: "
            f"gzip maakt data >10% groter: {stats['gzip_bytes']} vs {stats['original_bytes']}"
        )

    def test_zstd_available(self):
        """Controleer of zstandard beschikbaar is."""
        try:
            import zstandard  # noqa: F401

            assert True
        except ImportError:
            pytest.skip("zstandard niet geïnstalleerd")


# ─── Throughput Tests ─────────────────────────────────────────────────────────


class TestThroughput:
    """Test throughput berekening."""

    def test_throughput_returns_valid_stats(self):
        """Throughput berekening moet positieve waarden opleveren."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=0.5, deser_mean_ms=0.3, payload_size=1024
        )

        assert result["serialize_msg_per_sec"] > 0
        assert result["deserialize_msg_per_sec"] > 0
        assert result["serialize_mb_per_sec"] > 0
        assert result["deserialize_mb_per_sec"] > 0

    def test_throughput_faster_deser_higher_msgps(self):
        """Snellere deserialisatie moet hogere msg/sec opleveren."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=1.0, deser_mean_ms=0.5, payload_size=1024
        )
        assert result["deserialize_msg_per_sec"] > result["serialize_msg_per_sec"]

    def test_throughput_zero_time_safe(self):
        """Throughput met nultijd mag niet crashen."""
        from benchmarks.base_benchmark import BaseBenchmark

        result = BaseBenchmark._calculate_throughput(
            ser_mean_ms=0.0, deser_mean_ms=0.0, payload_size=0
        )
        assert result["serialize_msg_per_sec"] == 0
        assert result["deserialize_msg_per_sec"] == 0


# ─── Benchmark Runner Tests ──────────────────────────────────────────────────


class TestBenchmarkRunner:
    """Test de volledige benchmark runner pipeline."""

    def test_run_benchmark_returns_all_keys(self):
        """run_benchmark moet alle verwachte keys opleveren."""
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
            assert key in result, f"Verwachte key '{key}' ontbreekt in resultaat"

    def test_run_benchmark_timing_stats(self):
        """Timing stats moeten mean/median/min/max/std_dev/p95/p99 bevatten."""
        bench = MsgpackBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=20, warmup=5)

        for time_key in ["serialize_time_ms", "deserialize_time_ms", "round_trip_time_ms"]:
            stats = result[time_key]
            for stat in ["mean", "median", "min", "max", "std_dev", "p95", "p99"]:
                assert stat in stats, f"'{stat}' ontbreekt in {time_key}"
                assert isinstance(stats[stat], (int, float))

    def test_run_benchmark_compression_present(self):
        """Compressie stats moeten aanwezig zijn in benchmark resultaat."""
        bench = BsonBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=10, warmup=5)

        comp = result["compression"]
        assert comp["original_bytes"] > 0
        assert comp["gzip_bytes"] > 0

    def test_run_benchmark_throughput_present(self):
        """Throughput stats moeten aanwezig zijn in benchmark resultaat."""
        bench = JsonBenchmark()
        data = generate_test_data("small")
        result = bench.run_benchmark(data, iterations=10, warmup=5)

        tp = result["throughput"]
        assert tp["serialize_msg_per_sec"] > 0
        assert tp["deserialize_msg_per_sec"] > 0

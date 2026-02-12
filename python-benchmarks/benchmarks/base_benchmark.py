"""
Base Benchmark Class
======================
Abstract base class for all message format benchmarks.
Provides default measurement and statistics functionality.
"""

import time
import gzip
import statistics
import tracemalloc
from abc import ABC, abstractmethod
from typing import Any

try:
    import zstandard as zstd
    _HAS_ZSTD = True
except ImportError:
    _HAS_ZSTD = False


class BaseBenchmark(ABC):
    """Abstract base class for message format benchmarks."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Returns the name of the format."""
        pass

    @abstractmethod
    def serialize(self, data: dict) -> bytes:
        """Serialize the data to bytes."""
        pass

    @abstractmethod
    def deserialize(self, payload: bytes) -> Any:
        """Deserialize bytes back to data."""
        pass

    def run_benchmark(self, data: dict, iterations: int, warmup: int = 100) -> dict:
        """
        Run the full benchmark suite for this format.

        Args:
            data: Test data to serialize/deserialize
            iterations: Number of measured iterations
            warmup: Number of warmup iterations (not measured)

        Returns:
            dict with benchmark results and statistics
        """
        # Warmup phase - prime JIT/caches
        for _ in range(warmup):
            serialized = self.serialize(data)
            self.deserialize(serialized)

        # Measure serialization
        serialize_times = []
        serialized = None
        for _ in range(iterations):
            start = time.perf_counter_ns()
            serialized = self.serialize(data)
            end = time.perf_counter_ns()
            serialize_times.append((end - start) / 1_000_000)  # To ms

        # Measure payload size
        payload_size = len(serialized)

        # Measure deserialization
        deserialize_times = []
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.deserialize(serialized)
            end = time.perf_counter_ns()
            deserialize_times.append((end - start) / 1_000_000)  # To ms

        # Compute round-trip times
        round_trip_times = [
            s + d for s, d in zip(serialize_times, deserialize_times)
        ]

        # Measure memory usage
        try:
            memory_stats = self._measure_memory(data, serialized)
        except Exception:
            memory_stats = None

        # Measure compression
        try:
            compression_stats = self._measure_compression(serialized)
        except Exception:
            compression_stats = None

        # Calculate throughput
        try:
            ser_mean_ms = statistics.mean(serialize_times)
            deser_mean_ms = statistics.mean(deserialize_times)
            throughput = self._calculate_throughput(
                ser_mean_ms, deser_mean_ms, payload_size
            )
        except Exception:
            throughput = None

        return {
            "format": self.format_name,
            "iterations": iterations,
            "serialized_size_bytes": payload_size,
            "serialize_time_ms": self._calculate_stats(serialize_times),
            "deserialize_time_ms": self._calculate_stats(deserialize_times),
            "round_trip_time_ms": self._calculate_stats(round_trip_times),
            "memory_usage": memory_stats,
            "compression": compression_stats,
            "throughput": throughput,
        }

    def _measure_memory(self, data: dict, serialized: bytes) -> dict:
        """
        Measure memory usage of serialization and deserialization.
        Uses tracemalloc to measure peak memory allocation.

        Returns:
            dict with serialize_peak_bytes, deserialize_peak_bytes, total_peak_bytes
        """
        # Measure serialization memory
        tracemalloc.start()
        tracemalloc.reset_peak()
        for _ in range(10):
            self.serialize(data)
        _, ser_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Measure deserialization memory
        tracemalloc.start()
        tracemalloc.reset_peak()
        for _ in range(10):
            self.deserialize(serialized)
        _, deser_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Measure round-trip memory
        tracemalloc.start()
        tracemalloc.reset_peak()
        for _ in range(10):
            s = self.serialize(data)
            self.deserialize(s)
        _, total_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "serialize_peak_bytes": ser_peak,
            "deserialize_peak_bytes": deser_peak,
            "total_peak_bytes": total_peak,
        }

    @staticmethod
    def _measure_compression(serialized: bytes) -> dict:
        """
        Measure how well serialized data compresses with gzip and zstd.

        Returns:
            dict with original_bytes, gzip_bytes, gzip_ratio,
            and optionally zstd_bytes, zstd_ratio
        """
        original = len(serialized)

        # Gzip compression (level 6 = default)
        gzip_data = gzip.compress(serialized, compresslevel=6)
        gzip_size = len(gzip_data)
        gzip_ratio = round(gzip_size / original, 4) if original > 0 else 1.0

        result = {
            "original_bytes": original,
            "gzip_bytes": gzip_size,
            "gzip_ratio": gzip_ratio,
        }

        # Zstandard compression (level 3 = default)
        if _HAS_ZSTD:
            cctx = zstd.ZstdCompressor(level=3)
            zstd_data = cctx.compress(serialized)
            zstd_size = len(zstd_data)
            zstd_ratio = round(zstd_size / original, 4) if original > 0 else 1.0
            result["zstd_bytes"] = zstd_size
            result["zstd_ratio"] = zstd_ratio

        return result

    @staticmethod
    def _calculate_throughput(
        ser_mean_ms: float, deser_mean_ms: float, payload_size: int
    ) -> dict:
        """
        Calculate throughput metrics based on mean timings.

        Returns:
            dict with serialize_msg_per_sec, deserialize_msg_per_sec,
            serialize_mb_per_sec, deserialize_mb_per_sec
        """
        # Messages per second
        ser_mps = round(1000.0 / ser_mean_ms, 2) if ser_mean_ms > 0 else 0
        deser_mps = round(1000.0 / deser_mean_ms, 2) if deser_mean_ms > 0 else 0

        # MB per second (payload_size bytes per operation)
        mb = payload_size / (1024 * 1024)
        ser_mbps = round(mb * ser_mps, 4) if ser_mps > 0 else 0
        deser_mbps = round(mb * deser_mps, 4) if deser_mps > 0 else 0

        return {
            "serialize_msg_per_sec": ser_mps,
            "deserialize_msg_per_sec": deser_mps,
            "serialize_mb_per_sec": ser_mbps,
            "deserialize_mb_per_sec": deser_mbps,
        }

    @staticmethod
    def _calculate_stats(times: list) -> dict:
        """
        Calculate statistical metrics for a list of timing measurements.

        Returns:
            dict with mean, median, min, max, std_dev, p95, p99
        """
        sorted_times = sorted(times)
        n = len(sorted_times)

        return {
            "mean": round(statistics.mean(times), 6),
            "median": round(statistics.median(times), 6),
            "min": round(min(times), 6),
            "max": round(max(times), 6),
            "std_dev": round(statistics.stdev(times), 6) if n > 1 else 0.0,
            "p95": round(sorted_times[int(n * 0.95)], 6) if n > 0 else 0.0,
            "p99": round(sorted_times[int(n * 0.99)], 6) if n > 0 else 0.0,
        }

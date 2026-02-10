"""
Base Benchmark Klasse
======================
Abstracte base class voor alle message format benchmarks.
Biedt standaard meet- en statistiek functionaliteit.
"""

import time
import statistics
from abc import ABC, abstractmethod
from typing import Any


class BaseBenchmark(ABC):
    """Abstracte base class voor message format benchmarks."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Geeft de naam van het format terug."""
        pass

    @abstractmethod
    def serialize(self, data: dict) -> bytes:
        """Serialiseer de data naar bytes."""
        pass

    @abstractmethod
    def deserialize(self, payload: bytes) -> Any:
        """Deserialiseer bytes terug naar data."""
        pass

    def run_benchmark(self, data: dict, iterations: int, warmup: int = 100) -> dict:
        """
        Voer de volledige benchmark suite uit voor dit format.

        Args:
            data: De testdata om te serialiseren/deserialiseren
            iterations: Aantal meetiteraties
            warmup: Aantal warmup iteraties (niet gemeten)

        Returns:
            dict met benchmark resultaten en statistieken
        """
        # Warmup fase - breng JIT/caches op temperatuur
        for _ in range(warmup):
            serialized = self.serialize(data)
            self.deserialize(serialized)

        # Meet serialisatie
        serialize_times = []
        serialized = None
        for _ in range(iterations):
            start = time.perf_counter_ns()
            serialized = self.serialize(data)
            end = time.perf_counter_ns()
            serialize_times.append((end - start) / 1_000_000)  # Naar ms

        # Meet payload grootte
        payload_size = len(serialized)

        # Meet deserialisatie
        deserialize_times = []
        for _ in range(iterations):
            start = time.perf_counter_ns()
            self.deserialize(serialized)
            end = time.perf_counter_ns()
            deserialize_times.append((end - start) / 1_000_000)  # Naar ms

        # Bereken round-trip tijden
        round_trip_times = [
            s + d for s, d in zip(serialize_times, deserialize_times)
        ]

        return {
            "format": self.format_name,
            "iterations": iterations,
            "serialized_size_bytes": payload_size,
            "serialize_time_ms": self._calculate_stats(serialize_times),
            "deserialize_time_ms": self._calculate_stats(deserialize_times),
            "round_trip_time_ms": self._calculate_stats(round_trip_times),
        }

    @staticmethod
    def _calculate_stats(times: list) -> dict:
        """
        Bereken statistische metrics voor een lijst van timing metingen.

        Returns:
            dict met mean, median, min, max, std_dev, p95, p99
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

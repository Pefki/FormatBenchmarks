"""
Benchmark Runner
=================
Orchestrates all format benchmarks, collects results and system information.
"""

import os
import platform
from datetime import datetime, timezone


class BenchmarkRunner:
    """Runs benchmarks for all configured message formats."""

    def __init__(self, iterations: int = 1000, warmup: int = 100, formats: list = None):
        self.iterations = iterations
        self.warmup = warmup
        self.requested_formats = formats or [
            "json", "bson", "protobuf", "capnproto", "msgpack", "avro", "flatbuffers"
        ]
        self._benchmarks = self._load_benchmarks()

    def _load_benchmarks(self) -> dict:
        """Load available benchmark implementations."""
        benchmarks = {}

        # JSON is always available (standard library)
        from .json_benchmark import JsonBenchmark
        benchmarks["json"] = JsonBenchmark()

        # BSON (via pymongo)
        try:
            from .bson_benchmark import BsonBenchmark
            benchmarks["bson"] = BsonBenchmark()
        except ImportError:
            print("⚠  BSON not available (install: pip install pymongo)")

        # MessagePack
        try:
            from .msgpack_benchmark import MsgpackBenchmark
            benchmarks["msgpack"] = MsgpackBenchmark()
        except ImportError:
            print("⚠  MessagePack not available (install: pip install msgpack)")

        # Protobuf
        try:
            from .protobuf_benchmark import ProtobufBenchmark
            benchmarks["protobuf"] = ProtobufBenchmark()
        except ImportError as e:
            print(f"⚠  Protobuf not available ({e})")
            print("   Run first: python compile_schemas.py")
        except Exception as e:
            print(f"⚠  Protobuf error: {e}")

        # Cap'n Proto
        try:
            from .capnproto_benchmark import CapnProtoBenchmark
            benchmarks["capnproto"] = CapnProtoBenchmark()
        except ImportError as e:
            print(f"⚠  Cap'n Proto not available ({e})")
            print("   Install: sudo apt-get install capnproto libcapnp-dev && pip install pycapnp")
        except Exception as e:
            print(f"⚠  Cap'n Proto error: {e}")

        # Apache Avro
        try:
            from .avro_benchmark import AvroBenchmark
            benchmarks["avro"] = AvroBenchmark()
        except ImportError as e:
            print(f"⚠  Apache Avro not available ({e})")
            print("   Install: pip install fastavro")
        except Exception as e:
            print(f"⚠  Apache Avro error: {e}")

        # FlatBuffers
        try:
            from .flatbuffers_benchmark import FlatBuffersBenchmark
            benchmarks["flatbuffers"] = FlatBuffersBenchmark()
        except ImportError as e:
            print(f"⚠  FlatBuffers not available ({e})")
            print("   Install: pip install flatbuffers")
        except Exception as e:
            print(f"⚠  FlatBuffers error: {e}")

        return benchmarks

    def run_all(self, test_data: dict) -> dict:
        """
        Run all benchmarks for the provided test data.

        Args:
            test_data: dict with {size_label: data_dict} pairs

        Returns:
            dict with all benchmark results
        """
        results = []
        skipped = []

        for format_key in self.requested_formats:
            if format_key not in self._benchmarks:
                print(f"\n⏭  {format_key} skipped (not available)")
                skipped.append(format_key)
                continue

            benchmark = self._benchmarks[format_key]
            print(f"\n📊 Benchmarking {benchmark.format_name}...")

            for size_label, data in test_data.items():
                print(f"   Payload size: {size_label}...", end=" ", flush=True)
                try:
                    result = benchmark.run_benchmark(
                        data, self.iterations, self.warmup
                    )
                    result["payload_size_label"] = size_label
                    results.append(result)
                    size_bytes = result["serialized_size_bytes"]
                    mean_ms = result["serialize_time_ms"]["mean"]
                    print(f"✓ ({size_bytes} bytes, {mean_ms:.4f} ms avg)")
                except Exception as e:
                    print(f"✗ error: {e}")

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_info": self._get_system_info(),
            "config": {
                "iterations": self.iterations,
                "warmup": self.warmup,
                "formats": self.requested_formats,
                "payload_sizes": list(test_data.keys()),
                "skipped_formats": skipped,
            },
            "results": results,
        }

    @staticmethod
    def _get_system_info() -> dict:
        """Collect system information."""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": BenchmarkRunner._get_cpu_name(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count() or 0,
        }

    @staticmethod
    def _get_cpu_name() -> str:
        """Read CPU name, with fallback for Linux/WSL/Docker."""
        # Try platform.processor() first
        name = platform.processor()
        if name and name != "unknown":
            return name

        # Fallback: read /proc/cpuinfo (Linux)
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except (FileNotFoundError, PermissionError):
            pass

        return "unknown"

#!/usr/bin/env python3
"""
Message Format Benchmark Suite
===============================
Benchmarks different binary message formats for serialization performance,
payload size, and round-trip time.

Supported formats: JSON, BSON, Protobuf, Cap'n Proto, MessagePack, Apache Avro
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmarks.runner import BenchmarkRunner
from models.test_data import generate_test_data


def main():
    parser = argparse.ArgumentParser(
        description="Message Format Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
  python main.py
  python main.py --iterations 5000 --formats json protobuf msgpack
  python main.py --sizes small large --output results/my_test.json
        """
    )
    parser.add_argument(
        "--iterations", type=int, default=1000,
        help="Number of iterations per benchmark (default: 1000)"
    )
    parser.add_argument(
        "--formats", nargs="+",
        default=["json", "bson", "protobuf", "capnproto", "msgpack", "avro", "flatbuffers"],
        help="Formats to benchmark"
    )
    parser.add_argument(
        "--sizes", nargs="+",
        default=["small", "medium", "large"],
        help="Payload sizes to test (small, medium, large)"
    )
    parser.add_argument(
        "--output", type=str, default="results/benchmark_results.json",
        help="Output file path"
    )
    parser.add_argument(
        "--warmup", type=int, default=100,
        help="Number of warmup iterations (default: 100)"
    )
    parser.add_argument(
        "--nesting-depth", type=int, default=None,
        help="Target JSON container nesting depth for generated payloads (Python only)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Message Format Benchmark Suite")
    print("=" * 60)
    print(f"  Iterations: {args.iterations}")
    print(f"  Warmup:     {args.warmup}")
    print(f"  Formats:    {', '.join(args.formats)}")
    print(f"  Sizes:      {', '.join(args.sizes)}")
    if args.nesting_depth is not None:
        if args.nesting_depth < 1:
            raise ValueError("--nesting-depth must be >= 1")
        print(f"  Nesting:    {args.nesting_depth}")
    print(f"  Output:     {args.output}")
    print("=" * 60)

    # Generate test data for each size
    test_data = {}
    for size in args.sizes:
        test_data[size] = generate_test_data(size, nesting_depth=args.nesting_depth)
        print(f"  Generated test data for '{size}'")

    # Run benchmarks
    runner = BenchmarkRunner(
        iterations=args.iterations,
        warmup=args.warmup,
        formats=args.formats
    )

    results = runner.run_all(test_data)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)

    # Write results to file
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  Results written to: {args.output}")
    print(f"  Total benchmarks: {len(results.get('results', []))}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

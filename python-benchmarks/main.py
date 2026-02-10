#!/usr/bin/env python3
"""
Message Format Benchmark Suite
===============================
Benchmarkt verschillende binary message formats op serialisatie performantie,
payload grootte en round-trip tijd.

Ondersteunde formats: JSON, BSON, Protobuf, Cap'n Proto, MessagePack, Apache Avro
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Voeg project root toe aan sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from benchmarks.runner import BenchmarkRunner
from models.test_data import generate_test_data


def main():
    parser = argparse.ArgumentParser(
        description="Message Format Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  python main.py
  python main.py --iterations 5000 --formats json protobuf msgpack
  python main.py --sizes small large --output results/my_test.json
        """
    )
    parser.add_argument(
        "--iterations", type=int, default=1000,
        help="Aantal iteraties per benchmark (standaard: 1000)"
    )
    parser.add_argument(
        "--formats", nargs="+",
        default=["json", "bson", "protobuf", "capnproto", "msgpack", "avro"],
        help="Formats om te benchmarken"
    )
    parser.add_argument(
        "--sizes", nargs="+",
        default=["small", "medium", "large"],
        help="Payload groottes om te testen (small, medium, large)"
    )
    parser.add_argument(
        "--output", type=str, default="results/benchmark_results.json",
        help="Output bestandspad"
    )
    parser.add_argument(
        "--warmup", type=int, default=100,
        help="Aantal warmup iteraties (standaard: 100)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Message Format Benchmark Suite")
    print("=" * 60)
    print(f"  Iteraties:  {args.iterations}")
    print(f"  Warmup:     {args.warmup}")
    print(f"  Formats:    {', '.join(args.formats)}")
    print(f"  Groottes:   {', '.join(args.sizes)}")
    print(f"  Output:     {args.output}")
    print("=" * 60)

    # Genereer testdata voor elke grootte
    test_data = {}
    for size in args.sizes:
        test_data[size] = generate_test_data(size)
        print(f"  Testdata '{size}' gegenereerd")

    # Voer benchmarks uit
    runner = BenchmarkRunner(
        iterations=args.iterations,
        warmup=args.warmup,
        formats=args.formats
    )

    results = runner.run_all(test_data)

    # Zorg dat output directory bestaat
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)

    # Schrijf resultaten naar bestand
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"  Resultaten geschreven naar: {args.output}")
    print(f"  Totaal benchmarks: {len(results.get('results', []))}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

# Test Data: Benchmark CSV Files

This folder contains the exported benchmark result files used in the research comparison across implementations.

## What These CSV Files Represent

Each CSV file captures benchmark output for one language runtime:

- `bench_gcp_100k-it_1k-wit_go_SML.csv`
- `bench_gcp_100k-it_1k-wit_java_SML.csv`
- `bench_gcp_100k-it_1k-wit_python_SML.csv`
- `bench_gcp_100k-it_1k-wit_rust_SML.csv`

The files were used as the normalized input for analysis and side-by-side comparison of message format performance (for example, serialization/deserialization timing, throughput, and payload size metrics produced by the benchmark harness).

## Execution Environment

All benchmark runs were executed on **Google Cloud Run** with the following resource configuration:

- **Memory:** 8 GB
- **CPU:** 8 vCPU

Using the same Cloud Run configuration for all languages ensured fair, consistent resource conditions during data collection.

## Run Configuration

All tests used identical benchmark parameters:

- **Warmup iterations:** 1,000
- **Measured iterations:** 100,000

This means each benchmark first performed 1k warmup iterations to stabilize runtime behavior (for example, JIT/runtime initialization effects), followed by 100k measured iterations used for the final comparison dataset.

## How the CSVs Were Used in the Research

1. Run the benchmark suite for each language with the same workload and Cloud Run resource limits.
2. Export results to the language-specific CSV files in this folder.
3. Aggregate and compare metrics across all CSVs to produce cross-language research conclusions.

Because all CSVs were generated under the same execution and iteration settings, differences in results are attributable to implementation/runtime behavior rather than mismatched test configuration.

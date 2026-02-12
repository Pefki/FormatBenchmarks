# Format Benchmarks

Message Format Benchmarking — KdG The Lab 2025-2026 — Team 41 'netwerkt'

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

A benchmark platform for comparing different (binary) message formats.
The Python benchmark suite thoroughly tests all formats and stores results in a JSON output file.
The C# ASP.NET Core web application provides a UI with charts and data export.

**No database** — everything is stored in-memory and written to file.

### Geteste Formats

| Format | Type | Schema | Library |
|---|---|---|---|
| **JSON** | Text | No | Python `json` (standard) |
| **BSON** | Binary | No | `pymongo` |
| **Protocol Buffers** | Binary | Yes (.proto) | `protobuf` + `grpcio-tools` |
| **Cap'n Proto** | Binary (zero-copy) | Yes (.capnp) | `pycapnp` |
| **MessagePack** | Binary | No | `msgpack` |
| **Apache Avro** | Binary | Yes (.avsc) | `fastavro` |
| **FlatBuffers** | Binary (zero-copy) | Yes (.fbs) | `flatbuffers` |

### Benchmark Metrics

- **Payload size** — serialized data in bytes
- **Serialization time** — dict → bytes (ms)
- **Deserialization time** — bytes → dict (ms)
- **Round-trip time** — serialization + deserialization (ms)
- **Memory usage** — peak memory allocation per operation (bytes, via `tracemalloc`)
- **Statistics** — mean, median, min, max, std dev, P95, P99

### Web App Features

- **Interactive charts** — Chart.js bar charts per metric
- **Run comparison** — compare two benchmark runs side-by-side with delta percentages
- **Memory chart** — visualization of peak memory usage per format
- **Data export** — JSON and CSV export of results

## Project Structuur

```
format-benchmarks/
├── rust-benchmarks/            # Rust benchmark suite
│   ├── src/main.rs             # CLI entry point
│   ├── Cargo.toml
│   ├── build.sh
│   └── results/                # Output directory
├── python-benchmarks/          # Python benchmark suite
│   ├── main.py                 # CLI entry point
│   ├── compile_schemas.py      # Protobuf schema compilation
│   ├── requirements.txt
│   ├── benchmarks/
│   │   ├── base_benchmark.py   # Abstract base class
│   │   ├── json_benchmark.py
│   │   ├── bson_benchmark.py
│   │   ├── protobuf_benchmark.py
│   │   ├── capnproto_benchmark.py
│   │   ├── msgpack_benchmark.py
│   │   ├── avro_benchmark.py
│   │   └── runner.py           # Benchmark orchestrator
│   ├── models/
│   │   └── test_data.py        # Test payload generator
│   ├── schemas/
│   │   ├── message.proto       # Protobuf schema
│   │   ├── message.capnp       # Cap'n Proto schema
│   │   └── message.avsc        # Avro schema
│   └── results/                # Output directory
├── web-app/                    # C# ASP.NET Core web application
│   ├── FormatBenchmarks.sln
│   └── FormatBenchmarks/
│       ├── Program.cs
│       ├── Controllers/
│       │   └── BenchmarkController.cs
│       ├── Models/
│       │   └── BenchmarkResult.cs
│       ├── Services/
│       │   └── BenchmarkService.cs
│       └── wwwroot/            # Frontend (HTML/CSS/JS + Chart.js)
└── (Binary) Message Formats.md # Research document
```

## Requirements

- **Python 3.10+**
- **.NET 8.0 SDK**
- (Optional) Cap'n Proto C++ runtime for `pycapnp`

## Installation & Usage

### 1. Python Dependencies

```bash
cd python-benchmarks
pip install -r requirements.txt
```

### 2. Compile Protobuf Schema

```bash
python compile_schemas.py
```

### 3. (Optional) Cap'n Proto

```bash
sudo apt-get install capnproto libcapnp-dev
pip install pycapnp
```

### 4. Run Python Benchmarks Directly

```bash
cd python-benchmarks
python main.py
python main.py --iterations 5000 --formats json protobuf msgpack
python main.py --sizes small large --output results/my_test.json
```

### 5. Start the Web Application

```bash
cd web-app/FormatBenchmarks
dotnet run
```

Open http://localhost:5000 in your browser. Configure the benchmark parameters and click **Start Benchmark**.

## API Endpoints

| Method | URL | Description |
|---|---|---|
| `POST` | `/api/benchmark/run` | Start a benchmark |
| `GET` | `/api/benchmark/results` | All benchmark runs |
| `GET` | `/api/benchmark/results/{id}` | Specific run |
| `GET` | `/api/benchmark/compare?runA={id}&runB={id}` | Compare two runs |
| `GET` | `/api/benchmark/export/{id}?format=json` | Export as JSON |
| `GET` | `/api/benchmark/export/{id}?format=csv` | Export as CSV |

## Languages & Technologies

- **Python** — Benchmark execution, serialization/deserialization testing
- **Rust** — Benchmark execution, serialization/deserialization testing
- **C#** — ASP.NET Core web API, result management, data export
- **JavaScript** — Frontend UI, Chart.js charts
- **HTML/CSS** — Bootstrap 5 dark theme UI

## License

This project is licensed under the [MIT License](LICENSE).

## Team

**Team 41 'netwerkt'** — KdG The Lab 2025-2026

[GitLab Repository](https://gitlab.com/kdg-ti/the-lab/teams-25-26/41_netwerkt)

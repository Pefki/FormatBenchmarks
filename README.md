# Format Benchmarks

Message Format Benchmarking — KdG The Lab 2025-2026 — Team 41 'netwerkt'

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Live demo / test instance: [https://bench.pefki.xyz](https://bench.pefki.xyz)

## Overview

A benchmark platform for comparing binary and text message formats across multiple runtimes.

The project includes benchmark runners in **Python**, **Go**, **Rust**, and **Java**, plus a **C# ASP.NET Core** web app to run benchmarks and visualize results.

**No database** — everything is stored in-memory and written to file.

### Tested Formats

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
- **Serialization time** — object → bytes (ms)
- **Deserialization time** — bytes → object (ms)
- **Round-trip time** — serialization + deserialization (ms)
- **Memory usage** — allocation-focused memory metric per benchmark run
- **Compression** — compressed size and compression ratio
- **Throughput** — messages/s and MB/s
- **Statistics** — mean, median, min, max, std dev, P95, P99

### Web App Features

- **Interactive charts** — Bar charts per metric
- **Run comparison** — compare two benchmark runs side-by-side with delta percentages
- **Memory chart** — visualization of peak memory usage per format
- **Data export** — JSON and CSV export of results

## Requirements

- **Python 3.10+**
- **.NET 8.0 SDK**
- **Go** (for local Go benchmark builds)
- **Rust toolchain** (for local Rust benchmark builds)
- **Java 17+ + Maven** (for Java benchmark jar)
- Optional native tools for some schema-based formats:
	- `protoc` (Protocol Buffers)
	- `capnproto` / `capnpc`
	- `flatc` (FlatBuffers compiler)

## Quick Start (Web App)

### Option A: Run locally with .NET

Build benchmark backends first:

```bash
cd java-benchmarks
mvn package

cd ../rust-benchmarks
cargo build --release

cd ../go-benchmarks
./build.sh
```

Then start the web app:

```bash
cd web-app/FormatBenchmarks
dotnet run
```

Open http://localhost:5000 and start a benchmark run from the UI.

### Option B: Run with Docker Compose

```bash
docker compose up -d
```

This starts the prebuilt container on port `5000`.

## Deploy Locally

### Deploy from source (local build)

```bash
cd web-app/FormatBenchmarks
dotnet publish -c Release -o ../../out/web
dotnet ../../out/web/FormatBenchmarks.dll
```

This runs the app locally with your own build artifacts.

### Deploy with local Docker image

```bash
docker build -t format-benchmarks:local .
docker run -d --name format-benchmarks-local -p 5000:5000 format-benchmarks:local
```

To stop/remove:

```bash
docker stop format-benchmarks-local
docker rm format-benchmarks-local
```

## CLI Benchmark Usage

All benchmark runners use similar flags:

- `--iterations`
- `--warmup`
- `--formats`
- `--sizes`
- `--output`

### Python

```bash
cd python-benchmarks
pip install -r requirements.txt
python compile_schemas.py
python main.py --iterations 1000 --warmup 100 --formats json protobuf msgpack --sizes small medium large --output results/run_test.json
```

### Go

```bash
cd go-benchmarks
./build.sh
./benchmark -iterations 1000 -warmup 100 -formats json,bson,protobuf,capnproto,msgpack,avro,flatbuffers -sizes small,medium,large -output results/run_test.json
```

### Rust

```bash
cd rust-benchmarks
cargo build --release
./target/release/benchmark --iterations 1000 --warmup 100 --formats json,bson,protobuf,capnproto,msgpack,avro,flatbuffers --sizes small,medium,large --output results/run_test.json
```

### Java

```bash
cd java-benchmarks
mvn package
java -jar target/benchmark.jar --iterations 1000 --warmup 100 --formats json,bson,protobuf,capnproto,msgpack,avro,flatbuffers --sizes small,medium,large --output results/run_test.json
```

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

- **Python** — benchmark runner and reference implementation
- **Go** — benchmark runner with generated schema bindings
- **Rust** — benchmark runner with native-performance focus
- **Java** — benchmark runner packaged as `benchmark.jar`
- **C# / ASP.NET Core** — web API + benchmark orchestration + result management
- **JavaScript + Chart.js** — interactive benchmark visualizations
- **Docker** — containerized deployment/runtime

## Notes

- Output files are stored per language in each `results/` directory.
- The web app stores active run data in memory and can export JSON/CSV.

## License

This project is licensed under the [MIT License](LICENSE).

## Team

**'Netwerkt'** — KdG The Lab 2026 — Sefkan Özmen, Tom Verschuren, Xander Geluykens

[Github Repository](https://github.com/Pefki/FormatBenchmarks)
# Format Benchmarks

Binary Message Format Performantie Vergelijking — KdG The Lab 2025-2026

## Overzicht

Een benchmark platform voor het vergelijken van verschillende (binary) message formats.
De Python benchmark suite test uitgebreid alle formats en verzamelt resultaten in een JSON output file.
De C# ASP.NET Core web applicatie biedt een UI met grafieken en data export.

**Geen database** — alles wordt in-memory opgeslagen en eenmaal naar file geschreven.

### Geteste Formats

| Format | Type | Schema | Bibliotheek |
|---|---|---|---|
| **JSON** | Text | Nee | Python `json` (standaard) |
| **BSON** | Binary | Nee | `pymongo` |
| **Protocol Buffers** | Binary | Ja (.proto) | `protobuf` + `grpcio-tools` |
| **Cap'n Proto** | Binary (zero-copy) | Ja (.capnp) | `pycapnp` |
| **MessagePack** | Binary | Nee | `msgpack` |
| **Apache Avro** | Binary | Ja (.avsc) | `fastavro` |

### Benchmark Metrics

- **Payload grootte** — geserialiseerde data in bytes
- **Serialisatie tijd** — dict → bytes (ms)
- **Deserialisatie tijd** — bytes → dict (ms)
- **Round-trip tijd** — serialisatie + deserialisatie (ms)
- **Statistieken** — mean, median, min, max, std dev, P95, P99

## Project Structuur

```
format-benchmarks/
├── python-benchmarks/          # Python benchmark suite
│   ├── main.py                 # CLI entry point
│   ├── compile_schemas.py      # Protobuf schema compilatie
│   ├── requirements.txt
│   ├── benchmarks/
│   │   ├── base_benchmark.py   # Abstracte base class
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
├── web-app/                    # C# ASP.NET Core web applicatie
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
└── (Binary) Message Formats.md # Onderzoeksdocument
```

## Vereisten

- **Python 3.10+**
- **.NET 8.0 SDK**
- (Optioneel) Cap'n Proto C++ runtime voor `pycapnp`

## Installatie & Gebruik

### 1. Python Dependencies

```bash
cd python-benchmarks
pip install -r requirements.txt
```

### 2. Protobuf Schema Compileren

```bash
python compile_schemas.py
```

### 3. (Optioneel) Cap'n Proto

```bash
sudo apt-get install capnproto libcapnp-dev
pip install pycapnp
```

### 4. Python Benchmarks Direct Uitvoeren

```bash
cd python-benchmarks
python main.py
python main.py --iterations 5000 --formats json protobuf msgpack
python main.py --sizes small large --output results/mijn_test.json
```

### 5. Web Applicatie Starten

```bash
cd web-app/FormatBenchmarks
dotnet run
```

Open http://localhost:5000 in je browser. Configureer de benchmark parameters en klik op **Start Benchmark**.

## API Endpoints

| Methode | URL | Beschrijving |
|---|---|---|
| `POST` | `/api/benchmark/run` | Start een benchmark |
| `GET` | `/api/benchmark/results` | Alle benchmark runs |
| `GET` | `/api/benchmark/results/{id}` | Specifieke run |
| `GET` | `/api/benchmark/export/{id}?format=json` | Export als JSON |
| `GET` | `/api/benchmark/export/{id}?format=csv` | Export als CSV |

## Talen & Technologieën

- **Python** — Benchmark uitvoering, serialisatie/deserialisatie testing
- **C#** — ASP.NET Core web API, resultaat beheer, data export
- **JavaScript** — Frontend UI, Chart.js grafieken
- **HTML/CSS** — Bootstrap 5 dark theme UI

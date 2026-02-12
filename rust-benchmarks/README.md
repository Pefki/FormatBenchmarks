# Rust Benchmarks

Rust benchmark runner for the format-benchmarks suite.

## Supported formats

- `json`
- `bson`
- `protobuf`
- `capnproto`
- `msgpack`
- `avro`
- `flatbuffers`

## Build

```bash
cd rust-benchmarks
cargo build --release
```

Binary output:

- `target/release/benchmark`

Optional convenience script:

```bash
./build.sh
```

## Run

```bash
./target/release/benchmark \
  -iterations 1000 \
  -warmup 100 \
  -formats json,bson,protobuf,msgpack,avro \
  -sizes small,medium,large \
  -output results/run_test.json
```

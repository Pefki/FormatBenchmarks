use std::alloc::{GlobalAlloc, Layout, System};
use std::collections::{BTreeMap, HashMap};
use std::env;
use std::fs;
use std::io::Cursor;
use std::io::{Read, Write};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use anyhow::{anyhow, Context, Result};
use apache_avro::{from_value, to_value, Reader, Schema, Writer};
use capnp::message::{Builder as CapnpBuilder, ReaderOptions};
use flate2::write::GzEncoder;
use flate2::Compression;
use flatbuffers::FlatBufferBuilder;
use prost::Message;
use rand::rngs::StdRng;
use rand::{Rng, SeedableRng};
use serde::{Deserialize, Serialize};

static CURRENT_ALLOCATED: AtomicU64 = AtomicU64::new(0);
static PEAK_ALLOCATED: AtomicU64 = AtomicU64::new(0);

struct TrackingAllocator;

#[global_allocator]
static GLOBAL_ALLOCATOR: TrackingAllocator = TrackingAllocator;

unsafe impl GlobalAlloc for TrackingAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc(layout);
        if !ptr.is_null() {
            track_alloc(layout.size() as u64);
        }
        ptr
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        if !ptr.is_null() {
            track_dealloc(layout.size() as u64);
        }
        System.dealloc(ptr, layout);
    }

    unsafe fn realloc(&self, ptr: *mut u8, old_layout: Layout, new_size: usize) -> *mut u8 {
        let new_ptr = System.realloc(ptr, old_layout, new_size);
        if !new_ptr.is_null() {
            let old_size = old_layout.size() as u64;
            let new_size_u64 = new_size as u64;

            if new_size_u64 >= old_size {
                track_alloc(new_size_u64 - old_size);
            } else {
                track_dealloc(old_size - new_size_u64);
            }
        }
        new_ptr
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc_zeroed(layout);
        if !ptr.is_null() {
            track_alloc(layout.size() as u64);
        }
        ptr
    }
}

fn track_alloc(size: u64) {
    let current = CURRENT_ALLOCATED.fetch_add(size, Ordering::SeqCst) + size;
    let mut peak = PEAK_ALLOCATED.load(Ordering::SeqCst);
    while current > peak {
        match PEAK_ALLOCATED.compare_exchange(peak, current, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(_) => break,
            Err(observed) => peak = observed,
        }
    }
}

fn track_dealloc(size: u64) {
    CURRENT_ALLOCATED.fetch_sub(size, Ordering::SeqCst);
}

fn reset_allocation_tracking() {
    CURRENT_ALLOCATED.store(0, Ordering::SeqCst);
    PEAK_ALLOCATED.store(0, Ordering::SeqCst);
}

fn peak_allocation_bytes() -> u64 {
    PEAK_ALLOCATED.load(Ordering::SeqCst)
}

pub mod message_capnp {
    include!(concat!(env!("OUT_DIR"), "/message_capnp.rs"));
}

#[allow(dead_code, unused_imports)]
pub mod flatbuffers_generated {
    include!(concat!(env!("OUT_DIR"), "/flatbuffers_generated.rs"));
}

const DEFAULT_FORMATS: &str = "json,bson,protobuf,capnproto,msgpack,avro,flatbuffers";
const DEFAULT_SIZES: &str = "small,medium,large";
const DEFAULT_OUTPUT: &str = "results/benchmark_results.json";
const CHARSET: &[u8] = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

const AVRO_SCHEMA: &str = r#"
{
  "type": "record",
  "name": "BenchmarkMessage",
  "namespace": "benchmarks",
  "fields": [
    { "name": "id", "type": "long" },
    { "name": "timestamp", "type": "string" },
    { "name": "username", "type": "string" },
    { "name": "email", "type": "string" },
    { "name": "content", "type": "string" },
    { "name": "tags", "type": { "type": "array", "items": "string" } },
    { "name": "metadata", "type": { "type": "map", "values": "string" } },
    { "name": "score", "type": "double" },
    { "name": "is_active", "type": "boolean" },
    {
      "name": "nested_data",
      "type": [
        "null",
        {
          "type": "record",
          "name": "NestedData",
          "fields": [
            { "name": "field1", "type": "string" },
            { "name": "field2", "type": "long" },
            { "name": "values", "type": { "type": "array", "items": "double" } }
          ]
        }
      ],
      "default": null
    },
    {
      "name": "items",
      "type": {
        "type": "array",
        "items": {
          "type": "record",
          "name": "Item",
          "fields": [
            { "name": "name", "type": "string" },
            { "name": "value", "type": "double" },
            { "name": "active", "type": "boolean" },
            { "name": "description", "type": "string" },
            { "name": "tags", "type": { "type": "array", "items": "string" }, "default": [] }
          ]
        }
      },
      "default": []
    }
  ]
}
"#;

#[derive(Debug)]
struct CliArgs {
    iterations: usize,
    warmup: usize,
    formats: Vec<String>,
    sizes: Vec<String>,
    output: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct BenchmarkMessageData {
    id: i64,
    timestamp: String,
    username: String,
    email: String,
    content: String,
    tags: Vec<String>,
    metadata: HashMap<String, String>,
    score: f64,
    is_active: bool,
    nested_data: Option<NestedData>,
    items: Vec<ItemData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct NestedData {
    field1: String,
    field2: i64,
    values: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ItemData {
    name: String,
    value: f64,
    active: bool,
    description: String,
    tags: Vec<String>,
}

#[derive(Clone, PartialEq, Message)]
struct PbBenchmarkMessage {
    #[prost(int64, tag = "1")]
    id: i64,
    #[prost(string, tag = "2")]
    timestamp: String,
    #[prost(string, tag = "3")]
    username: String,
    #[prost(string, tag = "4")]
    email: String,
    #[prost(string, tag = "5")]
    content: String,
    #[prost(string, repeated, tag = "6")]
    tags: Vec<String>,
    #[prost(map = "string, string", tag = "7")]
    metadata: HashMap<String, String>,
    #[prost(double, tag = "8")]
    score: f64,
    #[prost(bool, tag = "9")]
    is_active: bool,
    #[prost(message, optional, tag = "10")]
    nested_data: Option<PbNestedData>,
    #[prost(message, repeated, tag = "11")]
    items: Vec<PbItem>,
}

#[derive(Clone, PartialEq, Message)]
struct PbNestedData {
    #[prost(string, tag = "1")]
    field1: String,
    #[prost(int64, tag = "2")]
    field2: i64,
    #[prost(double, repeated, tag = "3")]
    values: Vec<f64>,
}

#[derive(Clone, PartialEq, Message)]
struct PbItem {
    #[prost(string, tag = "1")]
    name: String,
    #[prost(double, tag = "2")]
    value: f64,
    #[prost(bool, tag = "3")]
    active: bool,
    #[prost(string, tag = "4")]
    description: String,
    #[prost(string, repeated, tag = "5")]
    tags: Vec<String>,
}

#[derive(Debug, Serialize)]
struct RunResult {
    timestamp: String,
    system_info: SystemInfo,
    config: RunConfig,
    results: Vec<BenchmarkResult>,
}

#[derive(Debug, Serialize)]
struct SystemInfo {
    platform: String,
    rust_version: String,
    processor: String,
    machine: String,
    cpu_count: usize,
    language: String,
}

#[derive(Debug, Serialize)]
struct RunConfig {
    iterations: usize,
    warmup: usize,
    formats: Vec<String>,
    payload_sizes: Vec<String>,
    skipped_formats: Vec<String>,
}

#[derive(Debug, Serialize)]
struct BenchmarkResult {
    format: String,
    iterations: usize,
    serialized_size_bytes: usize,
    serialize_time_ms: TimingStats,
    deserialize_time_ms: TimingStats,
    round_trip_time_ms: TimingStats,
    memory_usage: Option<MemoryUsage>,
    compression: Option<CompressionStats>,
    throughput: Option<ThroughputStats>,
    payload_size_label: String,
}

#[derive(Debug, Serialize)]
struct TimingStats {
    mean: f64,
    median: f64,
    min: f64,
    max: f64,
    std_dev: f64,
    p95: f64,
    p99: f64,
}

#[derive(Debug, Serialize)]
struct MemoryUsage {
    serialize_peak_bytes: u64,
    deserialize_peak_bytes: u64,
    total_peak_bytes: u64,
}

#[derive(Debug, Serialize)]
struct CompressionStats {
    original_bytes: usize,
    gzip_bytes: usize,
    gzip_ratio: f64,
    zstd_bytes: Option<usize>,
    zstd_ratio: Option<f64>,
}

#[derive(Debug, Serialize)]
struct ThroughputStats {
    serialize_msg_per_sec: f64,
    deserialize_msg_per_sec: f64,
    serialize_mb_per_sec: f64,
    deserialize_mb_per_sec: f64,
}

trait FormatBenchmark {
    fn format_name(&self) -> &'static str;
    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>>;
    fn deserialize(&self, payload: &[u8]) -> Result<()>;
}

struct JsonBenchmark;
struct BsonBenchmark;
struct MsgpackBenchmark;
struct ProtobufBenchmark;
struct CapnpBenchmark;
struct FlatbuffersBenchmark;
struct AvroBenchmark {
    schema: Schema,
}

impl FormatBenchmark for JsonBenchmark {
    fn format_name(&self) -> &'static str {
        "JSON"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        Ok(serde_json::to_vec(data)?)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let _: BenchmarkMessageData = serde_json::from_slice(payload)?;
        Ok(())
    }
}

impl FormatBenchmark for BsonBenchmark {
    fn format_name(&self) -> &'static str {
        "BSON"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        Ok(bson::to_vec(data)?)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let _: BenchmarkMessageData = bson::from_slice(payload)?;
        Ok(())
    }
}

impl FormatBenchmark for MsgpackBenchmark {
    fn format_name(&self) -> &'static str {
        "MessagePack"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        Ok(rmp_serde::to_vec(data)?)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let _: BenchmarkMessageData = rmp_serde::from_slice(payload)?;
        Ok(())
    }
}

impl FormatBenchmark for ProtobufBenchmark {
    fn format_name(&self) -> &'static str {
        "Protobuf"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        let mut buf = Vec::new();
        to_pb(data).encode(&mut buf)?;
        Ok(buf)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let _ = PbBenchmarkMessage::decode(payload)?;
        Ok(())
    }
}

impl FormatBenchmark for AvroBenchmark {
    fn format_name(&self) -> &'static str {
        "Apache Avro"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        let mut writer = Writer::new(&self.schema, Vec::new());
        let value = to_value(data)?;
        writer.append(value)?;
        Ok(writer.into_inner()?)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let reader = Reader::new(payload)?;
        for value in reader {
            let v = value?;
            let _: BenchmarkMessageData = from_value(&v)?;
        }
        Ok(())
    }
}

impl FormatBenchmark for CapnpBenchmark {
    fn format_name(&self) -> &'static str {
        "Cap'n Proto"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        let mut message = CapnpBuilder::new_default();
        {
            let mut root = message.init_root::<message_capnp::benchmark_message::Builder>();
            root.set_id(data.id);
            root.set_timestamp(&data.timestamp);
            root.set_username(&data.username);
            root.set_email(&data.email);
            root.set_content(&data.content);
            root.set_score(data.score);
            root.set_is_active(data.is_active);

            let mut tags = root.reborrow().init_tags(data.tags.len() as u32);
            for (index, tag) in data.tags.iter().enumerate() {
                tags.set(index as u32, tag);
            }

            let mut metadata_vec = data.metadata.iter().collect::<Vec<_>>();
            metadata_vec.sort_by(|left, right| left.0.cmp(right.0));
            let mut metadata = root.reborrow().init_metadata(metadata_vec.len() as u32);
            for (index, (key, value)) in metadata_vec.into_iter().enumerate() {
                let mut kv = metadata.reborrow().get(index as u32);
                kv.set_key(key);
                kv.set_value(value);
            }

            if let Some(nested) = &data.nested_data {
                let mut nested_builder = root.reborrow().init_nested_data();
                nested_builder.set_field1(&nested.field1);
                nested_builder.set_field2(nested.field2);
                let mut values = nested_builder.reborrow().init_values(nested.values.len() as u32);
                for (index, value) in nested.values.iter().enumerate() {
                    values.set(index as u32, *value);
                }
            }

            let mut items = root.reborrow().init_items(data.items.len() as u32);
            for (index, item) in data.items.iter().enumerate() {
                let mut item_builder = items.reborrow().get(index as u32);
                item_builder.set_name(&item.name);
                item_builder.set_value(item.value);
                item_builder.set_active(item.active);
                item_builder.set_description(&item.description);

                let mut item_tags = item_builder.reborrow().init_tags(item.tags.len() as u32);
                for (tag_index, tag) in item.tags.iter().enumerate() {
                    item_tags.set(tag_index as u32, tag);
                }
            }
        }

        let mut payload = Vec::new();
        capnp::serialize::write_message(&mut payload, &message)?;
        Ok(payload)
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let mut cursor = Cursor::new(payload);
        let reader = capnp::serialize::read_message(&mut cursor, ReaderOptions::new())?;
        let root = reader.get_root::<message_capnp::benchmark_message::Reader>()?;
        let _ = root.get_id();
        Ok(())
    }
}

impl FormatBenchmark for FlatbuffersBenchmark {
    fn format_name(&self) -> &'static str {
        "FlatBuffers"
    }

    fn serialize(&self, data: &BenchmarkMessageData) -> Result<Vec<u8>> {
        use flatbuffers_generated::benchmarks::{
            BenchmarkMessage, BenchmarkMessageArgs, Item, ItemArgs, KeyValue, KeyValueArgs,
            NestedData, NestedDataArgs,
        };

        let mut builder = FlatBufferBuilder::new();

        let timestamp = builder.create_string(&data.timestamp);
        let username = builder.create_string(&data.username);
        let email = builder.create_string(&data.email);
        let content = builder.create_string(&data.content);

        let tags_offsets = data
            .tags
            .iter()
            .map(|tag| builder.create_string(tag))
            .collect::<Vec<_>>();
        let tags = builder.create_vector(&tags_offsets);

        let mut metadata_vec = data.metadata.iter().collect::<Vec<_>>();
        metadata_vec.sort_by(|left, right| left.0.cmp(right.0));
        let metadata_offsets = metadata_vec
            .iter()
            .map(|(key, value)| {
                let key_offset = builder.create_string(key);
                let value_offset = builder.create_string(value);
                KeyValue::create(
                    &mut builder,
                    &KeyValueArgs {
                        key: Some(key_offset),
                        value: Some(value_offset),
                    },
                )
            })
            .collect::<Vec<_>>();
        let metadata = builder.create_vector(&metadata_offsets);

        let nested_data = data.nested_data.as_ref().map(|nested| {
            let field1 = builder.create_string(&nested.field1);
            let values = builder.create_vector(&nested.values);
            NestedData::create(
                &mut builder,
                &NestedDataArgs {
                    field1: Some(field1),
                    field2: nested.field2,
                    values: Some(values),
                },
            )
        });

        let items_offsets = data
            .items
            .iter()
            .map(|item| {
                let name = builder.create_string(&item.name);
                let description = builder.create_string(&item.description);
                let item_tag_offsets = item
                    .tags
                    .iter()
                    .map(|tag| builder.create_string(tag))
                    .collect::<Vec<_>>();
                let item_tags = builder.create_vector(&item_tag_offsets);

                Item::create(
                    &mut builder,
                    &ItemArgs {
                        name: Some(name),
                        value: item.value,
                        active: item.active,
                        description: Some(description),
                        tags: Some(item_tags),
                    },
                )
            })
            .collect::<Vec<_>>();
        let items = builder.create_vector(&items_offsets);

        let root = BenchmarkMessage::create(
            &mut builder,
            &BenchmarkMessageArgs {
                id: data.id,
                timestamp: Some(timestamp),
                username: Some(username),
                email: Some(email),
                content: Some(content),
                tags: Some(tags),
                metadata: Some(metadata),
                score: data.score,
                is_active: data.is_active,
                nested_data,
                items: Some(items),
            },
        );

        builder.finish(root, None);
        Ok(builder.finished_data().to_vec())
    }

    fn deserialize(&self, payload: &[u8]) -> Result<()> {
        let root = flatbuffers_generated::benchmarks::root_as_benchmark_message(payload)
            .map_err(|error| anyhow!("{error}"))?;
        let _ = root.id();
        Ok(())
    }
}

fn to_pb(data: &BenchmarkMessageData) -> PbBenchmarkMessage {
    PbBenchmarkMessage {
        id: data.id,
        timestamp: data.timestamp.clone(),
        username: data.username.clone(),
        email: data.email.clone(),
        content: data.content.clone(),
        tags: data.tags.clone(),
        metadata: data.metadata.clone(),
        score: data.score,
        is_active: data.is_active,
        nested_data: data.nested_data.as_ref().map(|nested| PbNestedData {
            field1: nested.field1.clone(),
            field2: nested.field2,
            values: nested.values.clone(),
        }),
        items: data
            .items
            .iter()
            .map(|item| PbItem {
                name: item.name.clone(),
                value: item.value,
                active: item.active,
                description: item.description.clone(),
                tags: item.tags.clone(),
            })
            .collect(),
    }
}

fn main() -> Result<()> {
    let args = parse_args()?;

    println!("{}", "=".repeat(60));
    println!("  Message Format Benchmark Suite (Rust)");
    println!("{}", "=".repeat(60));
    println!("  Iterations:  {}", args.iterations);
    println!("  Warmup:      {}", args.warmup);
    println!("  Formats:     {}", args.formats.join(", "));
    println!("  Sizes:       {}", args.sizes.join(", "));
    println!("  Output:      {}", args.output);
    println!("{}", "=".repeat(60));

    let mut test_data = BTreeMap::new();
    for size in &args.sizes {
        test_data.insert(size.clone(), generate_test_data(size));
        println!("  Test data '{}' generated", size);
    }

    let mut available: HashMap<&str, Box<dyn FormatBenchmark>> = HashMap::new();
    available.insert("json", Box::new(JsonBenchmark));
    available.insert("bson", Box::new(BsonBenchmark));
    available.insert("msgpack", Box::new(MsgpackBenchmark));
    available.insert("protobuf", Box::new(ProtobufBenchmark));
    available.insert("capnproto", Box::new(CapnpBenchmark));
    available.insert("flatbuffers", Box::new(FlatbuffersBenchmark));
    available.insert(
        "avro",
        Box::new(AvroBenchmark {
            schema: Schema::parse_str(AVRO_SCHEMA).context("invalid Avro schema")?,
        }),
    );

    let mut results = Vec::new();
    let mut skipped = Vec::new();

    for format in &args.formats {
        let key = format.to_lowercase();
        let Some(bench) = available.get(key.as_str()) else {
            println!("\n⏭  {} skipped (not implemented in Rust yet)", key);
            skipped.push(key);
            continue;
        };

        println!("\n📊 Benchmarking {}...", bench.format_name());

        for (size_label, data) in &test_data {
            print!("   Payload size: {}... ", size_label);
            let result = run_benchmark(bench.as_ref(), data, args.iterations, args.warmup)
                .with_context(|| format!("{} / {} failed", bench.format_name(), size_label))?;

            let mut result = result;
            result.payload_size_label = size_label.clone();
            println!(
                "✓ ({} bytes, {:.6} ms avg)",
                result.serialized_size_bytes, result.serialize_time_ms.mean
            );
            results.push(result);
        }
    }

    let run_result = RunResult {
        timestamp: iso_now(),
        system_info: get_system_info(),
        config: RunConfig {
            iterations: args.iterations,
            warmup: args.warmup,
            formats: args.formats,
            payload_sizes: args.sizes,
            skipped_formats: skipped,
        },
        results,
    };

    if let Some(parent) = Path::new(&args.output).parent() {
        if !parent.as_os_str().is_empty() {
            fs::create_dir_all(parent)
                .with_context(|| format!("failed to create output directory: {}", parent.display()))?;
        }
    }

    let json = serde_json::to_string_pretty(&run_result)?;
    fs::write(&args.output, json)
        .with_context(|| format!("failed to write output: {}", args.output))?;

    println!("\n{}", "=".repeat(60));
    println!("  Results written to: {}", args.output);
    println!("  Total benchmarks: {}", run_result.results.len());
    println!("{}", "=".repeat(60));

    Ok(())
}

fn parse_args() -> Result<CliArgs> {
    let mut iterations = 1000usize;
    let mut warmup = 100usize;
    let mut formats = DEFAULT_FORMATS.split(',').map(str::to_string).collect::<Vec<_>>();
    let mut sizes = DEFAULT_SIZES.split(',').map(str::to_string).collect::<Vec<_>>();
    let mut output = DEFAULT_OUTPUT.to_string();

    let mut i = 1usize;
    let args = env::args().collect::<Vec<_>>();
    while i < args.len() {
        match args[i].as_str() {
            "-iterations" | "--iterations" => {
                i += 1;
                iterations = args
                    .get(i)
                    .ok_or_else(|| anyhow!("missing value for iterations"))?
                    .parse()
                    .context("invalid iterations value")?;
            }
            "-warmup" | "--warmup" => {
                i += 1;
                warmup = args
                    .get(i)
                    .ok_or_else(|| anyhow!("missing value for warmup"))?
                    .parse()
                    .context("invalid warmup value")?;
            }
            "-formats" | "--formats" => {
                i += 1;
                let raw = args.get(i).ok_or_else(|| anyhow!("missing value for formats"))?;
                formats = raw
                    .split(',')
                    .map(|value| value.trim().to_lowercase())
                    .filter(|value| !value.is_empty())
                    .collect();
            }
            "-sizes" | "--sizes" => {
                i += 1;
                let raw = args.get(i).ok_or_else(|| anyhow!("missing value for sizes"))?;
                sizes = raw
                    .split(',')
                    .map(|value| value.trim().to_lowercase())
                    .filter(|value| !value.is_empty())
                    .collect();
            }
            "-output" | "--output" => {
                i += 1;
                output = args
                    .get(i)
                    .ok_or_else(|| anyhow!("missing value for output"))?
                    .to_string();
            }
            "-h" | "--help" => {
                print_help();
                std::process::exit(0);
            }
            unknown => {
                return Err(anyhow!("unknown argument: {unknown}"));
            }
        }
        i += 1;
    }

    Ok(CliArgs {
        iterations,
        warmup,
        formats,
        sizes,
        output,
    })
}

fn print_help() {
    println!("Message Format Benchmark Suite (Rust)");
    println!();
    println!("Usage:");
    println!("  benchmark [-iterations N] [-warmup N] [-formats a,b,c] [-sizes a,b,c] [-output FILE]");
}

fn run_benchmark(
    benchmark: &dyn FormatBenchmark,
    data: &BenchmarkMessageData,
    iterations: usize,
    warmup: usize,
) -> Result<BenchmarkResult> {
    for _ in 0..warmup {
        let serialized = benchmark.serialize(data)?;
        benchmark.deserialize(&serialized)?;
    }

    let mut serialize_times = Vec::with_capacity(iterations);
    let mut serialized = Vec::new();

    for _ in 0..iterations {
        let start = Instant::now();
        let out = benchmark.serialize(data)?;
        let elapsed = start.elapsed();

        serialized = out;
        serialize_times.push(elapsed.as_secs_f64() * 1000.0);
    }

    let payload_size = serialized.len();

    let mut deserialize_times = Vec::with_capacity(iterations);
    for _ in 0..iterations {
        let start = Instant::now();
        benchmark.deserialize(&serialized)?;
        let elapsed = start.elapsed();
        deserialize_times.push(elapsed.as_secs_f64() * 1000.0);
    }

    let round_trip_times = serialize_times
        .iter()
        .zip(deserialize_times.iter())
        .map(|(ser, deser)| ser + deser)
        .collect::<Vec<_>>();

    let ser_mean = mean(&serialize_times);
    let deser_mean = mean(&deserialize_times);

    let throughput = Some(calculate_throughput(ser_mean, deser_mean, payload_size));
    let memory_usage = Some(measure_memory(benchmark, data, &serialized)?);

    Ok(BenchmarkResult {
        format: benchmark.format_name().to_string(),
        iterations,
        serialized_size_bytes: payload_size,
        serialize_time_ms: calculate_stats(&serialize_times),
        deserialize_time_ms: calculate_stats(&deserialize_times),
        round_trip_time_ms: calculate_stats(&round_trip_times),
        memory_usage,
        compression: Some(measure_compression(&serialized)?),
        throughput,
        payload_size_label: String::new(),
    })
}

fn measure_memory(
    benchmark: &dyn FormatBenchmark,
    data: &BenchmarkMessageData,
    serialized: &[u8],
) -> Result<MemoryUsage> {
    let samples = 10;

    let serialize_peak = measure_phase_peak(samples, || {
        let _payload = benchmark.serialize(data)?;
        Ok(())
    })?;

    let deserialize_peak = measure_phase_peak(samples, || {
        benchmark.deserialize(serialized)?;
        Ok(())
    })?;

    let total_peak = measure_phase_peak(samples, || {
        let payload = benchmark.serialize(data)?;
        benchmark.deserialize(&payload)?;
        Ok(())
    })?;

    Ok(MemoryUsage {
        serialize_peak_bytes: serialize_peak,
        deserialize_peak_bytes: deserialize_peak,
        total_peak_bytes: total_peak,
    })
}

fn measure_phase_peak<F>(iterations: usize, mut phase: F) -> Result<u64>
where
    F: FnMut() -> Result<()>,
{
    reset_allocation_tracking();

    for _ in 0..iterations {
        phase()?;
    }

    Ok(peak_allocation_bytes())
}

fn measure_compression(serialized: &[u8]) -> Result<CompressionStats> {
    let original = serialized.len();

    let mut gzip_buf = Vec::new();
    {
        let mut encoder = GzEncoder::new(&mut gzip_buf, Compression::default());
        encoder.write_all(serialized)?;
        encoder.finish()?;
    }

    let gzip_bytes = gzip_buf.len();
    let gzip_ratio = if original == 0 {
        1.0
    } else {
        round4(gzip_bytes as f64 / original as f64)
    };

    let zstd_bytes = zstd::stream::encode_all(serialized, 3).ok().map(|v| v.len());
    let zstd_ratio = zstd_bytes.map(|bytes| {
        if original == 0 {
            1.0
        } else {
            round4(bytes as f64 / original as f64)
        }
    });

    Ok(CompressionStats {
        original_bytes: original,
        gzip_bytes,
        gzip_ratio,
        zstd_bytes,
        zstd_ratio,
    })
}

fn calculate_throughput(ser_mean_ms: f64, deser_mean_ms: f64, payload_size: usize) -> ThroughputStats {
    let serialize_msg_per_sec = if ser_mean_ms > 0.0 {
        round2(1000.0 / ser_mean_ms)
    } else {
        0.0
    };

    let deserialize_msg_per_sec = if deser_mean_ms > 0.0 {
        round2(1000.0 / deser_mean_ms)
    } else {
        0.0
    };

    let mb = payload_size as f64 / (1024.0 * 1024.0);

    let serialize_mb_per_sec = if serialize_msg_per_sec > 0.0 {
        round4(mb * serialize_msg_per_sec)
    } else {
        0.0
    };

    let deserialize_mb_per_sec = if deserialize_msg_per_sec > 0.0 {
        round4(mb * deserialize_msg_per_sec)
    } else {
        0.0
    };

    ThroughputStats {
        serialize_msg_per_sec,
        deserialize_msg_per_sec,
        serialize_mb_per_sec,
        deserialize_mb_per_sec,
    }
}

fn calculate_stats(data: &[f64]) -> TimingStats {
    if data.is_empty() {
        return TimingStats {
            mean: 0.0,
            median: 0.0,
            min: 0.0,
            max: 0.0,
            std_dev: 0.0,
            p95: 0.0,
            p99: 0.0,
        };
    }

    let mut sorted = data.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let n = sorted.len();
    let mean_value = mean(data);
    let median = if n % 2 == 0 {
        (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0
    } else {
        sorted[n / 2]
    };

    let variance = if n <= 1 {
        0.0
    } else {
        let sum = data
            .iter()
            .map(|value| {
                let diff = value - mean_value;
                diff * diff
            })
            .sum::<f64>();
        sum / (n as f64 - 1.0)
    };

    let p95_idx = ((n as f64) * 0.95).floor() as usize;
    let p99_idx = ((n as f64) * 0.99).floor() as usize;

    TimingStats {
        mean: round6(mean_value),
        median: round6(median),
        min: round6(*sorted.first().unwrap_or(&0.0)),
        max: round6(*sorted.last().unwrap_or(&0.0)),
        std_dev: round6(variance.sqrt()),
        p95: round6(sorted[p95_idx.min(n - 1)]),
        p99: round6(sorted[p99_idx.min(n - 1)]),
    }
}

fn mean(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}

fn generate_test_data(size: &str) -> BenchmarkMessageData {
    let mut rng = StdRng::seed_from_u64(42);

    match size {
        "small" => generate_small(),
        "medium" => generate_medium(&mut rng),
        "large" => generate_large(&mut rng),
        _ => generate_small(),
    }
}

fn generate_small() -> BenchmarkMessageData {
    BenchmarkMessageData {
        id: 1,
        timestamp: "2026-02-10T12:00:00Z".to_string(),
        username: "testuser".to_string(),
        email: "test@example.com".to_string(),
        content: "Hello, this is a small test message for benchmark purposes.".to_string(),
        tags: vec!["test".into(), "small".into(), "benchmark".into()],
        metadata: HashMap::from([
            ("source".to_string(), "benchmark".to_string()),
            ("version".to_string(), "1.0".to_string()),
        ]),
        score: 95.5,
        is_active: true,
        nested_data: None,
        items: vec![],
    }
}

fn generate_medium(rng: &mut StdRng) -> BenchmarkMessageData {
    let tags = (0..20).map(|_| random_string(rng, 10)).collect::<Vec<_>>();

    let mut metadata = HashMap::new();
    for _ in 0..15 {
        metadata.insert(random_string(rng, 8), random_string(rng, 20));
    }

    let values = (0..50)
        .map(|_| rng.gen_range(0.0..100.0))
        .collect::<Vec<_>>();

    let items = (0..10)
        .map(|_| ItemData {
            name: random_string(rng, 20),
            value: rng.gen_range(0.0..1000.0),
            active: rng.gen_bool(0.5),
            description: String::new(),
            tags: vec![],
        })
        .collect::<Vec<_>>();

    BenchmarkMessageData {
        id: 42,
        timestamp: "2026-02-10T12:00:00Z".to_string(),
        username: "benchmark_user_medium".to_string(),
        email: "benchmark.medium@example.com".to_string(),
        content: random_string(rng, 1000),
        tags,
        metadata,
        score: 87.123456,
        is_active: true,
        nested_data: Some(NestedData {
            field1: random_string(rng, 100),
            field2: 12345,
            values,
        }),
        items,
    }
}

fn generate_large(rng: &mut StdRng) -> BenchmarkMessageData {
    let tags = (0..100).map(|_| random_string(rng, 15)).collect::<Vec<_>>();

    let mut metadata = HashMap::new();
    for _ in 0..50 {
        metadata.insert(random_string(rng, 12), random_string(rng, 50));
    }

    let values = (0..500)
        .map(|_| rng.gen_range(0.0..1000.0))
        .collect::<Vec<_>>();

    let items = (0..100)
        .map(|_| {
            let item_tags = (0..5).map(|_| random_string(rng, 8)).collect::<Vec<_>>();
            ItemData {
                name: random_string(rng, 30),
                value: rng.gen_range(0.0..10000.0),
                active: rng.gen_bool(0.5),
                description: random_string(rng, 200),
                tags: item_tags,
            }
        })
        .collect::<Vec<_>>();

    BenchmarkMessageData {
        id: 99999,
        timestamp: "2026-02-10T12:00:00Z".to_string(),
        username: "benchmark_user_large_payload_test".to_string(),
        email: "benchmark.large.payload@example.com".to_string(),
        content: random_string(rng, 10000),
        tags,
        metadata,
        score: 99.999999,
        is_active: true,
        nested_data: Some(NestedData {
            field1: random_string(rng, 500),
            field2: 9999999,
            values,
        }),
        items,
    }
}

fn random_string(rng: &mut StdRng, len: usize) -> String {
    (0..len)
        .map(|_| {
            let idx = rng.gen_range(0..CHARSET.len());
            CHARSET[idx] as char
        })
        .collect()
}

fn get_system_info() -> SystemInfo {
    SystemInfo {
        platform: format!("{}/{}", env::consts::OS, env::consts::ARCH),
        rust_version: rust_version(),
        processor: cpu_model_name(),
        machine: env::consts::ARCH.to_string(),
        cpu_count: std::thread::available_parallelism()
            .map(|value| value.get())
            .unwrap_or(1),
        language: "rust".to_string(),
    }
}

fn rust_version() -> String {
    match std::process::Command::new("rustc").arg("--version").output() {
        Ok(output) if output.status.success() => String::from_utf8(output.stdout)
            .map(|value| value.trim().to_string())
            .unwrap_or_else(|_| "unknown".to_string()),
        _ => "unknown".to_string(),
    }
}

fn cpu_model_name() -> String {
    if let Ok(mut file) = fs::File::open("/proc/cpuinfo") {
        let mut content = String::new();
        if file.read_to_string(&mut content).is_ok() {
            for line in content.lines() {
                if let Some(value) = line.strip_prefix("model name") {
                    if let Some((_, name)) = value.split_once(':') {
                        return name.trim().to_string();
                    }
                }
            }
        }
    }

    "unknown".to_string()
}

fn iso_now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

fn round2(value: f64) -> f64 {
    (value * 100.0).round() / 100.0
}

fn round4(value: f64) -> f64 {
    (value * 10000.0).round() / 10000.0
}

fn round6(value: f64) -> f64 {
    (value * 1_000_000.0).round() / 1_000_000.0
}

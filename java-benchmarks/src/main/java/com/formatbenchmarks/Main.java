package com.formatbenchmarks;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.google.flatbuffers.FlatBufferBuilder;
import com.google.protobuf.ListValue;
import com.google.protobuf.NullValue;
import com.google.protobuf.Struct;
import com.google.protobuf.Value;
import org.apache.avro.Schema;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericDatumReader;
import org.apache.avro.generic.GenericDatumWriter;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.io.DecoderFactory;
import org.apache.avro.io.Encoder;
import org.apache.avro.io.EncoderFactory;
import org.bson.BsonBinaryReader;
import org.bson.BsonBinaryWriter;
import org.bson.Document;
import org.bson.codecs.DecoderContext;
import org.bson.codecs.DocumentCodec;
import org.bson.codecs.EncoderContext;
import org.bson.io.BasicOutputBuffer;
import org.msgpack.jackson.dataformat.MessagePackFactory;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.channels.Channels;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.StringJoiner;
import java.util.zip.GZIPOutputStream;

public final class Main {
    private static final ObjectMapper JSON_MAPPER = new ObjectMapper();
    private static final ObjectMapper RESULT_MAPPER = new ObjectMapper()
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .setSerializationInclusion(JsonInclude.Include.NON_NULL);
    private static final ObjectMapper MSGPACK_MAPPER = new ObjectMapper(new MessagePackFactory());
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'")
            .withZone(ZoneOffset.UTC);
    private static final String DEFAULT_FORMATS = "json,bson,protobuf,capnproto,msgpack,avro,flatbuffers";
    private static final String DEFAULT_SIZES = "small,medium,large";
    private static final String DEFAULT_OUTPUT = "results/benchmark_results.json";
    private static final char[] CHARSET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".toCharArray();

    private static final String AVRO_SCHEMA = """
            {
              \"type\": \"record\",
              \"name\": \"BenchmarkMessage\",
              \"namespace\": \"benchmarks\",
              \"fields\": [
                { \"name\": \"id\", \"type\": \"long\" },
                { \"name\": \"timestamp\", \"type\": \"string\" },
                { \"name\": \"username\", \"type\": \"string\" },
                { \"name\": \"email\", \"type\": \"string\" },
                { \"name\": \"content\", \"type\": \"string\" },
                { \"name\": \"tags\", \"type\": { \"type\": \"array\", \"items\": \"string\" } },
                { \"name\": \"metadata\", \"type\": { \"type\": \"map\", \"values\": \"string\" } },
                { \"name\": \"score\", \"type\": \"double\" },
                { \"name\": \"is_active\", \"type\": \"boolean\" },
                {
                  \"name\": \"nested_data\",
                  \"type\": [
                    \"null\",
                    {
                      \"type\": \"record\",
                      \"name\": \"NestedData\",
                      \"fields\": [
                        { \"name\": \"field1\", \"type\": \"string\" },
                        { \"name\": \"field2\", \"type\": \"long\" },
                        { \"name\": \"values\", \"type\": { \"type\": \"array\", \"items\": \"double\" } }
                      ]
                    }
                  ],
                  \"default\": null
                },
                {
                  \"name\": \"items\",
                  \"type\": {
                    \"type\": \"array\",
                    \"items\": {
                      \"type\": \"record\",
                      \"name\": \"Item\",
                      \"fields\": [
                        { \"name\": \"name\", \"type\": \"string\" },
                        { \"name\": \"value\", \"type\": \"double\" },
                        { \"name\": \"active\", \"type\": \"boolean\" },
                        { \"name\": \"description\", \"type\": \"string\" },
                        { \"name\": \"tags\", \"type\": { \"type\": \"array\", \"items\": \"string\" }, \"default\": [] }
                      ]
                    }
                  },
                  \"default\": []
                }
              ]
            }
            """;

    public static void main(String[] args) {
        try {
            CliArgs cli = parseArgs(args);

            System.out.println("=".repeat(60));
            System.out.println("  Message Format Benchmark Suite (Java)");
            System.out.println("=".repeat(60));
            System.out.println("  Iterations:  " + cli.iterations);
            System.out.println("  Warmup:      " + cli.warmup);
            System.out.println("  Formats:     " + String.join(", ", cli.formats));
            System.out.println("  Sizes:       " + String.join(", ", cli.sizes));
            if (cli.nestingDepth != null) {
                System.out.println("  Nesting:     " + cli.nestingDepth);
            }
            System.out.println("  Output:      " + cli.output);
            System.out.println("=".repeat(60));

            Map<String, Map<String, Object>> testData = new LinkedHashMap<>();
            for (String size : cli.sizes) {
                testData.put(size, generateTestData(size, cli.nestingDepth));
                System.out.println("  Test data '" + size + "' generated");
            }

            Map<String, FormatBenchmark> available = new HashMap<>();
            available.put("json", new JsonBenchmark());
            available.put("bson", new BsonBenchmark());
            available.put("msgpack", new MsgpackBenchmark());
            available.put("avro", new AvroBenchmark());
            available.put("protobuf", new ProtobufBenchmark());
            available.put("capnproto", new CapnpBenchmark());
            available.put("flatbuffers", new FlatbuffersBenchmark());

            List<BenchmarkResult> results = new ArrayList<>();
            List<String> skipped = new ArrayList<>();

            for (String format : cli.formats) {
                FormatBenchmark benchmark = available.get(format);
                if (benchmark == null) {
                    System.out.println("\n⏭  " + format + " skipped (not implemented in Java yet)");
                    skipped.add(format);
                    continue;
                }

                System.out.println("\n📊 Benchmarking " + benchmark.formatName() + "...");
                for (Map.Entry<String, Map<String, Object>> entry : testData.entrySet()) {
                    String sizeLabel = entry.getKey();
                    Map<String, Object> data = entry.getValue();
                    System.out.print("   Payload size: " + sizeLabel + "... ");

                    BenchmarkResult result = runBenchmark(benchmark, data, cli.iterations, cli.warmup);
                    result.payloadSizeLabel = sizeLabel;
                    results.add(result);

                    System.out.printf(Locale.US, "✓ (%d bytes, %.6f ms avg)%n",
                            result.serializedSizeBytes,
                            result.serializeTimeMs.mean);
                }
            }

            RunResult run = new RunResult();
            run.timestamp = TS.format(Instant.now());
            run.systemInfo = getSystemInfo();
            run.config = new RunConfig(cli.iterations, cli.warmup, cli.formats, cli.sizes, skipped, cli.nestingDepth);
            run.results = results;

            Path output = Path.of(cli.output);
            Path parent = output.getParent();
            if (parent != null) {
                Files.createDirectories(parent);
            }
            RESULT_MAPPER.writerWithDefaultPrettyPrinter().writeValue(output.toFile(), run);

            System.out.println("\n" + "=".repeat(60));
            System.out.println("  Results written to: " + output);
            System.out.println("  Total benchmarks: " + results.size());
            System.out.println("=".repeat(60));
        } catch (Exception ex) {
            System.err.println("Benchmark failed: " + ex.getMessage());
            ex.printStackTrace(System.err);
            System.exit(1);
        }
    }

    private static BenchmarkResult runBenchmark(
            FormatBenchmark benchmark,
            Map<String, Object> data,
            int iterations,
            int warmup) throws Exception {

        for (int i = 0; i < warmup; i++) {
            byte[] serialized = benchmark.serialize(data);
            benchmark.deserialize(serialized);
        }

        List<Double> serializeTimes = new ArrayList<>(iterations);
        byte[] serialized = new byte[0];
        for (int i = 0; i < iterations; i++) {
            long start = System.nanoTime();
            serialized = benchmark.serialize(data);
            long elapsed = System.nanoTime() - start;
            serializeTimes.add(elapsed / 1_000_000.0);
        }

        int payloadSize = serialized.length;

        List<Double> deserializeTimes = new ArrayList<>(iterations);
        for (int i = 0; i < iterations; i++) {
            long start = System.nanoTime();
            benchmark.deserialize(serialized);
            long elapsed = System.nanoTime() - start;
            deserializeTimes.add(elapsed / 1_000_000.0);
        }

        List<Double> roundTrip = new ArrayList<>(iterations);
        for (int i = 0; i < iterations; i++) {
            roundTrip.add(serializeTimes.get(i) + deserializeTimes.get(i));
        }

        MemoryUsage memoryUsage = measureMemory(benchmark, data, serialized);
        CompressionInfo compression = measureCompression(serialized);
        ThroughputInfo throughput = calculateThroughput(mean(serializeTimes), mean(deserializeTimes), payloadSize);

        BenchmarkResult result = new BenchmarkResult();
        result.format = benchmark.formatName();
        result.iterations = iterations;
        result.serializedSizeBytes = payloadSize;
        result.payloadNestingDepth = calculateNestingDepth(data);
        result.serializeTimeMs = calculateStats(serializeTimes);
        result.deserializeTimeMs = calculateStats(deserializeTimes);
        result.roundTripTimeMs = calculateStats(roundTrip);
        result.memoryUsage = memoryUsage;
        result.compression = compression;
        result.throughput = throughput;
        return result;
    }

    // Scalars have depth 0. Containers (map/list) add one level plus deepest child.
    private static int calculateNestingDepth(Object value) {
        if (value instanceof Map<?, ?> map) {
            int maxChild = 0;
            for (Object child : map.values()) {
                maxChild = Math.max(maxChild, calculateNestingDepth(child));
            }
            return 1 + maxChild;
        }

        if (value instanceof List<?> list) {
            int maxChild = 0;
            for (Object child : list) {
                maxChild = Math.max(maxChild, calculateNestingDepth(child));
            }
            return 1 + maxChild;
        }

        return 0;
    }

    private static MemoryUsage measureMemory(FormatBenchmark benchmark, Map<String, Object> data, byte[] serialized) {
        long serPeak = phaseMemory(() -> {
            benchmark.serialize(data);
            return null;
        });
        long deserPeak = phaseMemory(() -> {
            benchmark.deserialize(serialized);
            return null;
        });
        long totalPeak = phaseMemory(() -> {
            byte[] payload = benchmark.serialize(data);
            benchmark.deserialize(payload);
            return null;
        });

        MemoryUsage memoryUsage = new MemoryUsage();
        memoryUsage.serializePeakBytes = serPeak;
        memoryUsage.deserializePeakBytes = deserPeak;
        memoryUsage.totalPeakBytes = totalPeak;
        return memoryUsage;
    }

    private static long phaseMemory(UnsafeRunnable action) {
        Runtime runtime = Runtime.getRuntime();
        System.gc();
        long before = usedMemory(runtime);
        for (int i = 0; i < 10; i++) {
            try {
                action.run();
            } catch (Exception ignored) {
                return 0;
            }
        }
        long after = usedMemory(runtime);
        return Math.max(0, after - before);
    }

    private static long usedMemory(Runtime runtime) {
        return runtime.totalMemory() - runtime.freeMemory();
    }

    private static CompressionInfo measureCompression(byte[] serialized) {
        CompressionInfo info = new CompressionInfo();
        info.originalBytes = serialized.length;

        try {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            try (GZIPOutputStream gzip = new GZIPOutputStream(output)) {
                gzip.write(serialized);
            }
            info.gzipBytes = output.size();
            info.gzipRatio = info.originalBytes == 0
                    ? 1.0
                    : round4((double) info.gzipBytes / info.originalBytes);
        } catch (IOException ex) {
            info.gzipBytes = 0;
            info.gzipRatio = 0.0;
        }

        return info;
    }

    private static ThroughputInfo calculateThroughput(double serMeanMs, double deserMeanMs, int payloadSize) {
        ThroughputInfo throughput = new ThroughputInfo();
        throughput.serializeMsgPerSec = serMeanMs > 0 ? round2(1000.0 / serMeanMs) : 0.0;
        throughput.deserializeMsgPerSec = deserMeanMs > 0 ? round2(1000.0 / deserMeanMs) : 0.0;
        double mb = payloadSize / (1024.0 * 1024.0);
        throughput.serializeMbPerSec = throughput.serializeMsgPerSec > 0 ? round4(mb * throughput.serializeMsgPerSec) : 0.0;
        throughput.deserializeMbPerSec = throughput.deserializeMsgPerSec > 0 ? round4(mb * throughput.deserializeMsgPerSec) : 0.0;
        return throughput;
    }

    private static TimingStats calculateStats(List<Double> values) {
        List<Double> sorted = new ArrayList<>(values);
        Collections.sort(sorted);
        int n = sorted.size();

        TimingStats stats = new TimingStats();
        if (n == 0) {
            return stats;
        }

        stats.mean = round6(mean(values));
        stats.median = round6(n % 2 == 0
                ? (sorted.get((n / 2) - 1) + sorted.get(n / 2)) / 2.0
                : sorted.get(n / 2));
        stats.min = round6(sorted.get(0));
        stats.max = round6(sorted.get(n - 1));
        stats.stdDev = round6(stdDev(values, stats.mean));
        stats.p95 = round6(sorted.get(Math.min((int) Math.floor(n * 0.95), n - 1)));
        stats.p99 = round6(sorted.get(Math.min((int) Math.floor(n * 0.99), n - 1)));
        return stats;
    }

    private static double mean(List<Double> values) {
        if (values.isEmpty()) {
            return 0.0;
        }
        double sum = 0.0;
        for (double value : values) {
            sum += value;
        }
        return sum / values.size();
    }

    private static double stdDev(List<Double> values, double mean) {
        if (values.size() <= 1) {
            return 0.0;
        }
        double sum = 0.0;
        for (double value : values) {
            double diff = value - mean;
            sum += diff * diff;
        }
        return Math.sqrt(sum / (values.size() - 1.0));
    }

    private static double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }

    private static double round4(double value) {
        return Math.round(value * 10_000.0) / 10_000.0;
    }

    private static double round6(double value) {
        return Math.round(value * 1_000_000.0) / 1_000_000.0;
    }

    private static SystemInfo getSystemInfo() {
        SystemInfo info = new SystemInfo();
        info.platform = System.getProperty("os.name") + "/" + System.getProperty("os.arch");
        info.javaVersion = System.getProperty("java.version", "unknown");
        info.processor = cpuModelName();
        info.machine = System.getProperty("os.arch", "unknown");
        info.cpuCount = Runtime.getRuntime().availableProcessors();
        info.language = "java";
        return info;
    }

    private static String cpuModelName() {
        try {
            Path cpuInfo = Path.of("/proc/cpuinfo");
            if (Files.exists(cpuInfo)) {
                for (String line : Files.readAllLines(cpuInfo)) {
                    if (line.startsWith("model name")) {
                        int idx = line.indexOf(':');
                        if (idx > 0) {
                            return line.substring(idx + 1).trim();
                        }
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return "unknown";
    }

    private static CliArgs parseArgs(String[] args) {
        int iterations = 1000;
        int warmup = 100;
        List<String> formats = splitCsv(DEFAULT_FORMATS);
        List<String> sizes = splitCsv(DEFAULT_SIZES);
        Integer nestingDepth = null;
        String output = DEFAULT_OUTPUT;

        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            switch (arg) {
                case "-iterations", "--iterations" -> {
                    i++;
                    iterations = Integer.parseInt(requireValue(arg, args, i));
                }
                case "-warmup", "--warmup" -> {
                    i++;
                    warmup = Integer.parseInt(requireValue(arg, args, i));
                }
                case "-formats", "--formats" -> {
                    i++;
                    formats = splitCsv(requireValue(arg, args, i));
                }
                case "-sizes", "--sizes" -> {
                    i++;
                    sizes = splitCsv(requireValue(arg, args, i));
                }
                case "-output", "--output" -> {
                    i++;
                    output = requireValue(arg, args, i);
                }
                case "-nesting-depth", "--nesting-depth" -> {
                    i++;
                    nestingDepth = Integer.parseInt(requireValue(arg, args, i));
                    if (nestingDepth < 1) {
                        throw new IllegalArgumentException("nesting-depth must be >= 1");
                    }
                }
                case "-h", "--help" -> {
                    printHelp();
                    System.exit(0);
                }
                default -> throw new IllegalArgumentException("Unknown argument: " + arg);
            }
        }

        return new CliArgs(iterations, warmup, formats, sizes, nestingDepth, output);
    }

    private static String requireValue(String option, String[] args, int index) {
        if (index >= args.length) {
            throw new IllegalArgumentException("Missing value for " + option);
        }
        return args[index];
    }

    private static List<String> splitCsv(String value) {
        List<String> values = new ArrayList<>();
        for (String part : value.split(",")) {
            String normalized = part.trim().toLowerCase(Locale.ROOT);
            if (!normalized.isEmpty()) {
                values.add(normalized);
            }
        }
        return values;
    }

    private static void printHelp() {
        System.out.println("Message Format Benchmark Suite (Java)");
        System.out.println();
        System.out.println("Usage:");
        System.out.println("  java -jar benchmark.jar --iterations N --warmup N --formats a,b,c --sizes a,b,c --nesting-depth N --output FILE");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> generateTestData(String size, Integer nestingDepth) {
        Random random = new Random(42);
        Map<String, Object> data = switch (size.toLowerCase(Locale.ROOT)) {
            case "small" -> generateSmall();
            case "medium" -> generateMedium(random);
            case "large" -> generateLarge(random);
            default -> generateSmall();
        };

        if (nestingDepth != null) {
            applyNestingDepth(data, nestingDepth);
        }

        return data;
    }

    @SuppressWarnings("unchecked")
    private static void applyNestingDepth(Map<String, Object> data, int requestedDepth) {
        int depth = Math.max(1, Math.min(4, requestedDepth));

        switch (depth) {
            case 1 -> {
                data.put("tags", List.of());
                data.put("metadata", Map.of());
                data.put("nested_data", null);
                data.put("items", List.of());
            }
            case 2 -> {
                if (!(data.get("tags") instanceof List<?> tags) || tags.isEmpty()) {
                    data.put("tags", List.of("tag"));
                }
                if (!(data.get("metadata") instanceof Map<?, ?> meta) || meta.isEmpty()) {
                    data.put("metadata", Map.of("source", "benchmark"));
                }
                data.put("nested_data", null);
                data.put("items", List.of());
            }
            case 3 -> {
                Object nestedObj = data.get("nested_data");
                Map<String, Object> nested;
                if (nestedObj instanceof Map<?, ?> existing) {
                    nested = (Map<String, Object>) existing;
                } else {
                    nested = new LinkedHashMap<>();
                    nested.put("field1", "leaf");
                    nested.put("field2", 1L);
                    nested.put("values", new ArrayList<>(List.of(1.0)));
                }
                if (!(nested.get("values") instanceof List<?> values) || values.isEmpty()) {
                    nested.put("values", new ArrayList<>(List.of(1.0)));
                }
                data.put("nested_data", nested);
                data.put("items", List.of());
            }
            default -> {
                Object nestedObj = data.get("nested_data");
                if (!(nestedObj instanceof Map<?, ?>)) {
                    Map<String, Object> nested = new LinkedHashMap<>();
                    nested.put("field1", "leaf");
                    nested.put("field2", 1L);
                    nested.put("values", new ArrayList<>(List.of(1.0)));
                    data.put("nested_data", nested);
                }

                Object itemsObj = data.get("items");
                if (!(itemsObj instanceof List<?> items) || items.isEmpty()) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("name", "item");
                    item.put("value", 1.0);
                    item.put("active", true);
                    item.put("description", "");
                    item.put("tags", new ArrayList<>(List.of("t")));
                    data.put("items", new ArrayList<>(List.of(item)));
                } else {
                    Object first = items.get(0);
                    if (first instanceof Map<?, ?> firstMap) {
                        Map<String, Object> typed = (Map<String, Object>) firstMap;
                        Object tagsObj = typed.get("tags");
                        if (!(tagsObj instanceof List<?> tags) || tags.isEmpty()) {
                            typed.put("tags", new ArrayList<>(List.of("t")));
                        }
                    }
                }
            }
        }
    }

    private static Map<String, Object> generateSmall() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", 1L);
        data.put("timestamp", "2026-02-10T12:00:00Z");
        data.put("username", "testuser");
        data.put("email", "test@example.com");
        data.put("content", "Hello, this is a small test message for benchmark purposes.");
        data.put("tags", List.of("test", "small", "benchmark"));
        data.put("metadata", Map.of("source", "benchmark", "version", "1.0"));
        data.put("score", 95.5);
        data.put("is_active", true);
        data.put("nested_data", null);
        data.put("items", List.of());
        return data;
    }

    private static Map<String, Object> generateMedium(Random random) {
        List<String> tags = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            tags.add(randomString(random, 10));
        }

        Map<String, String> metadata = new LinkedHashMap<>();
        for (int i = 0; i < 15; i++) {
            metadata.put(randomString(random, 8), randomString(random, 20));
        }

        List<Double> values = new ArrayList<>();
        for (int i = 0; i < 50; i++) {
            values.add(random.nextDouble() * 100.0);
        }

        List<Map<String, Object>> items = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("name", randomString(random, 20));
            item.put("value", random.nextDouble() * 1000.0);
            item.put("active", random.nextBoolean());
            item.put("description", "");
            item.put("tags", List.of());
            items.add(item);
        }

        Map<String, Object> nested = new LinkedHashMap<>();
        nested.put("field1", randomString(random, 100));
        nested.put("field2", 12345L);
        nested.put("values", values);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", 42L);
        data.put("timestamp", "2026-02-10T12:00:00Z");
        data.put("username", "benchmark_user_medium");
        data.put("email", "benchmark.medium@example.com");
        data.put("content", randomString(random, 1000));
        data.put("tags", tags);
        data.put("metadata", metadata);
        data.put("score", 87.123456);
        data.put("is_active", true);
        data.put("nested_data", nested);
        data.put("items", items);
        return data;
    }

    private static Map<String, Object> generateLarge(Random random) {
        List<String> tags = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            tags.add(randomString(random, 15));
        }

        Map<String, String> metadata = new LinkedHashMap<>();
        for (int i = 0; i < 50; i++) {
            metadata.put(randomString(random, 12), randomString(random, 50));
        }

        List<Double> values = new ArrayList<>();
        for (int i = 0; i < 500; i++) {
            values.add(random.nextDouble() * 1000.0);
        }

        List<Map<String, Object>> items = new ArrayList<>();
        for (int i = 0; i < 100; i++) {
            List<String> itemTags = new ArrayList<>();
            for (int j = 0; j < 5; j++) {
                itemTags.add(randomString(random, 8));
            }

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("name", randomString(random, 30));
            item.put("value", random.nextDouble() * 10_000.0);
            item.put("active", random.nextBoolean());
            item.put("description", randomString(random, 200));
            item.put("tags", itemTags);
            items.add(item);
        }

        Map<String, Object> nested = new LinkedHashMap<>();
        nested.put("field1", randomString(random, 500));
        nested.put("field2", 9_999_999L);
        nested.put("values", values);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", 99_999L);
        data.put("timestamp", "2026-02-10T12:00:00Z");
        data.put("username", "benchmark_user_large_payload_test");
        data.put("email", "benchmark.large.payload@example.com");
        data.put("content", randomString(random, 10_000));
        data.put("tags", tags);
        data.put("metadata", metadata);
        data.put("score", 99.999999);
        data.put("is_active", true);
        data.put("nested_data", nested);
        data.put("items", items);
        return data;
    }

    private static String randomString(Random random, int length) {
        StringBuilder sb = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            sb.append(CHARSET[random.nextInt(CHARSET.length)]);
        }
        return sb.toString();
    }

    private interface UnsafeRunnable {
        Void run() throws Exception;
    }

    private interface FormatBenchmark {
        String formatName();
        byte[] serialize(Map<String, Object> data) throws Exception;
        void deserialize(byte[] payload) throws Exception;
    }

    private static Value toProtoValue(Object value) {
        if (value == null) {
            return Value.newBuilder().setNullValue(NullValue.NULL_VALUE).build();
        }
        if (value instanceof String text) {
            return Value.newBuilder().setStringValue(text).build();
        }
        if (value instanceof Number number) {
            return Value.newBuilder().setNumberValue(number.doubleValue()).build();
        }
        if (value instanceof Boolean bool) {
            return Value.newBuilder().setBoolValue(bool).build();
        }
        if (value instanceof Map<?, ?> map) {
            Struct.Builder struct = Struct.newBuilder();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                struct.putFields(String.valueOf(entry.getKey()), toProtoValue(entry.getValue()));
            }
            return Value.newBuilder().setStructValue(struct.build()).build();
        }
        if (value instanceof List<?> list) {
            ListValue.Builder listValue = ListValue.newBuilder();
            for (Object item : list) {
                listValue.addValues(toProtoValue(item));
            }
            return Value.newBuilder().setListValue(listValue.build()).build();
        }
        return Value.newBuilder().setStringValue(String.valueOf(value)).build();
    }

    private static Map<String, Object> fromProtoStruct(Struct struct) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (Map.Entry<String, Value> entry : struct.getFieldsMap().entrySet()) {
            map.put(entry.getKey(), fromProtoValue(entry.getValue()));
        }
        return map;
    }

    private static Object fromProtoValue(Value value) {
        return switch (value.getKindCase()) {
            case NULL_VALUE -> null;
            case STRING_VALUE -> value.getStringValue();
            case NUMBER_VALUE -> value.getNumberValue();
            case BOOL_VALUE -> value.getBoolValue();
            case STRUCT_VALUE -> fromProtoStruct(value.getStructValue());
            case LIST_VALUE -> {
                List<Object> list = new ArrayList<>();
                for (Value item : value.getListValue().getValuesList()) {
                    list.add(fromProtoValue(item));
                }
                yield list;
            }
            case KIND_NOT_SET -> null;
        };
    }

    private static final class JsonBenchmark implements FormatBenchmark {
        @Override
        public String formatName() {
            return "JSON";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            return JSON_MAPPER.writeValueAsBytes(data);
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            JSON_MAPPER.readValue(payload, new TypeReference<Map<String, Object>>() { });
        }
    }

    private static final class BsonBenchmark implements FormatBenchmark {
        private final DocumentCodec codec = new DocumentCodec();

        @Override
        public String formatName() {
            return "BSON";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            String json = JSON_MAPPER.writeValueAsString(data);
            Document document = Document.parse(json);
            BasicOutputBuffer buffer = new BasicOutputBuffer();
            try (BsonBinaryWriter writer = new BsonBinaryWriter(buffer)) {
                codec.encode(writer, document, EncoderContext.builder().build());
            }
            return buffer.toByteArray();
        }

        @Override
        public void deserialize(byte[] payload) {
            BsonBinaryReader reader = new BsonBinaryReader(java.nio.ByteBuffer.wrap(payload));
            codec.decode(reader, DecoderContext.builder().build());
            reader.close();
        }
    }

    private static final class MsgpackBenchmark implements FormatBenchmark {
        @Override
        public String formatName() {
            return "MessagePack";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            return MSGPACK_MAPPER.writeValueAsBytes(data);
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            MSGPACK_MAPPER.readValue(payload, new TypeReference<Map<String, Object>>() { });
        }
    }

    private static final class ProtobufBenchmark implements FormatBenchmark {
        @Override
        public String formatName() {
            return "Protobuf";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) {
            Struct.Builder builder = Struct.newBuilder();
            for (Map.Entry<String, Object> entry : data.entrySet()) {
                builder.putFields(entry.getKey(), toProtoValue(entry.getValue()));
            }
            return builder.build().toByteArray();
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            Struct parsed = Struct.parseFrom(payload);
            fromProtoStruct(parsed);
        }
    }

    private static final class CapnpBenchmark implements FormatBenchmark {
        @Override
        public String formatName() {
            return "Cap'n Proto";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            byte[] json = JSON_MAPPER.writeValueAsBytes(data);
            org.capnproto.MessageBuilder message = new org.capnproto.MessageBuilder();
            org.capnproto.AnyPointer.Builder rootPointer = message.initRoot(org.capnproto.AnyPointer.factory);
            org.capnproto.Data.Builder root = rootPointer.initAs(org.capnproto.Data.factory, json.length);
            root.asByteBuffer().put(json);

            ByteArrayOutputStream output = new ByteArrayOutputStream();
            org.capnproto.SerializePacked.writeToUnbuffered(Channels.newChannel(output), message);
            return output.toByteArray();
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            ByteArrayInputStream input = new ByteArrayInputStream(payload);
            org.capnproto.MessageReader message = org.capnproto.SerializePacked.readFromUnbuffered(Channels.newChannel(input));
            org.capnproto.Data.Reader root = message.getRoot(org.capnproto.Data.factory);
            JSON_MAPPER.readValue(root.toArray(), new TypeReference<Map<String, Object>>() { });
        }
    }

    private static final class FlatbuffersBenchmark implements FormatBenchmark {
        @Override
        public String formatName() {
            return "FlatBuffers";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            byte[] json = JSON_MAPPER.writeValueAsBytes(data);
            FlatBufferBuilder builder = new FlatBufferBuilder(json.length + 64);
            int payloadVector = builder.createByteVector(json);

            builder.startTable(1);
            builder.addOffset(0, payloadVector, 0);
            int rootTable = builder.endTable();
            builder.finish(rootTable);
            return builder.sizedByteArray();
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            ByteBuffer bb = ByteBuffer.wrap(payload).order(ByteOrder.LITTLE_ENDIAN);

            int messageOffset = bb.position();
            int rootTable = messageOffset + bb.getInt(messageOffset);
            int vtable = rootTable - bb.getInt(rootTable);

            if (vtable < 0 || vtable + 6 > bb.limit()) {
                throw new IllegalArgumentException("Invalid FlatBuffers payload (vtable)");
            }

            short dataFieldOffset = bb.getShort(vtable + 4);
            if (dataFieldOffset == 0) {
                throw new IllegalArgumentException("Invalid FlatBuffers payload (missing data field)");
            }

            int vectorRef = rootTable + dataFieldOffset;
            int vectorStart = vectorRef + bb.getInt(vectorRef);
            int length = bb.getInt(vectorStart);

            if (length < 0 || vectorStart + 4 + length > bb.limit()) {
                throw new IllegalArgumentException("Invalid FlatBuffers payload (vector bounds)");
            }

            byte[] json = new byte[length];
            int prevPos = bb.position();
            bb.position(vectorStart + 4);
            bb.get(json);
            bb.position(prevPos);

            JSON_MAPPER.readValue(json, new TypeReference<Map<String, Object>>() { });
        }
    }

    private static final class AvroBenchmark implements FormatBenchmark {
        private final Schema schema;

        private AvroBenchmark() {
            this.schema = new Schema.Parser().parse(AVRO_SCHEMA);
        }

        @Override
        public String formatName() {
            return "Apache Avro";
        }

        @Override
        public byte[] serialize(Map<String, Object> data) throws Exception {
            GenericRecord record = toRecord(data);
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            GenericDatumWriter<GenericRecord> writer = new GenericDatumWriter<>(schema);
            Encoder encoder = EncoderFactory.get().binaryEncoder(output, null);
            writer.write(record, encoder);
            encoder.flush();
            return output.toByteArray();
        }

        @Override
        public void deserialize(byte[] payload) throws Exception {
            GenericDatumReader<GenericRecord> reader = new GenericDatumReader<>(schema);
            reader.read(null, DecoderFactory.get().binaryDecoder(payload, null));
        }

        @SuppressWarnings("unchecked")
        private GenericRecord toRecord(Map<String, Object> data) {
            GenericRecord record = new GenericData.Record(schema);
            record.put("id", ((Number) data.get("id")).longValue());
            record.put("timestamp", Objects.toString(data.get("timestamp"), ""));
            record.put("username", Objects.toString(data.get("username"), ""));
            record.put("email", Objects.toString(data.get("email"), ""));
            record.put("content", Objects.toString(data.get("content"), ""));
            record.put("tags", data.getOrDefault("tags", List.of()));

            Map<String, String> metadata = new LinkedHashMap<>();
            Object rawMeta = data.get("metadata");
            if (rawMeta instanceof Map<?, ?> rawMap) {
                for (Map.Entry<?, ?> entry : rawMap.entrySet()) {
                    metadata.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()));
                }
            }
            record.put("metadata", metadata);
            record.put("score", ((Number) data.getOrDefault("score", 0.0)).doubleValue());
            record.put("is_active", Boolean.TRUE.equals(data.get("is_active")));

            Object nestedObj = data.get("nested_data");
            if (nestedObj instanceof Map<?, ?> nestedMap) {
                Schema nestedSchema = schema.getField("nested_data").schema().getTypes().stream()
                        .filter(s -> s.getType() == Schema.Type.RECORD)
                        .findFirst()
                        .orElseThrow();
                GenericRecord nested = new GenericData.Record(nestedSchema);
                nested.put("field1", Objects.toString(nestedMap.get("field1"), ""));
                Object nestedField2 = nestedMap.containsKey("field2") ? nestedMap.get("field2") : 0L;
                nested.put("field2", nestedField2 instanceof Number number ? number.longValue() : 0L);
                Object nestedValues = nestedMap.containsKey("values") ? nestedMap.get("values") : List.of();
                nested.put("values", nestedValues instanceof List<?> listValues ? listValues : List.of());
                record.put("nested_data", nested);
            } else {
                record.put("nested_data", null);
            }

            List<GenericRecord> items = new ArrayList<>();
            Object rawItems = data.get("items");
            if (rawItems instanceof List<?> list) {
                Schema itemSchema = schema.getField("items").schema().getElementType();
                for (Object itemObj : list) {
                    if (!(itemObj instanceof Map<?, ?> itemMap)) {
                        continue;
                    }
                    GenericRecord item = new GenericData.Record(itemSchema);
                    item.put("name", Objects.toString(itemMap.get("name"), ""));
                    Object itemValue = itemMap.containsKey("value") ? itemMap.get("value") : 0.0;
                    item.put("value", itemValue instanceof Number number ? number.doubleValue() : 0.0);
                    item.put("active", Boolean.TRUE.equals(itemMap.get("active")));
                    item.put("description", Objects.toString(itemMap.get("description"), ""));
                    Object itemTags = itemMap.containsKey("tags") ? itemMap.get("tags") : List.of();
                    item.put("tags", itemTags instanceof List<?> listTags ? listTags : List.of());
                    items.add(item);
                }
            }
            record.put("items", items);
            return record;
        }
    }

    private record CliArgs(int iterations, int warmup, List<String> formats, List<String> sizes, Integer nestingDepth, String output) {}

    private static final class RunResult {
        public String timestamp;
        public SystemInfo systemInfo;
        public RunConfig config;
        public List<BenchmarkResult> results;
    }

    private static final class SystemInfo {
        public String platform;
        public String javaVersion;
        public String processor;
        public String machine;
        public int cpuCount;
        public String language;
    }

    private static final class RunConfig {
        public int iterations;
        public int warmup;
        public List<String> formats;
        public List<String> payloadSizes;
        public List<String> skippedFormats;
        public Integer nestingDepth;

        public RunConfig(int iterations, int warmup, List<String> formats, List<String> payloadSizes, List<String> skippedFormats, Integer nestingDepth) {
            this.iterations = iterations;
            this.warmup = warmup;
            this.formats = formats;
            this.payloadSizes = payloadSizes;
            this.skippedFormats = skippedFormats;
            this.nestingDepth = nestingDepth;
        }
    }

    private static final class BenchmarkResult {
        public String format;
        public int iterations;
        public int serializedSizeBytes;
        public int payloadNestingDepth;
        public TimingStats serializeTimeMs;
        public TimingStats deserializeTimeMs;
        public TimingStats roundTripTimeMs;
        public MemoryUsage memoryUsage;
        public CompressionInfo compression;
        public ThroughputInfo throughput;
        public String payloadSizeLabel;
    }

    private static final class TimingStats {
        public double mean;
        public double median;
        public double min;
        public double max;
        public double stdDev;
        public double p95;
        public double p99;
    }

    private static final class MemoryUsage {
        public long serializePeakBytes;
        public long deserializePeakBytes;
        public long totalPeakBytes;
    }

    private static final class CompressionInfo {
        public int originalBytes;
        public int gzipBytes;
        public double gzipRatio;
    }

    private static final class ThroughputInfo {
        public double serializeMsgPerSec;
        public double deserializeMsgPerSec;
        public double serializeMbPerSec;
        public double deserializeMbPerSec;
    }
}

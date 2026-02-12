namespace FormatBenchmarks.Models;

/// <summary>
/// Representeert een volledige benchmark uitvoering met alle resultaten.
/// Wordt in-memory opgeslagen (geen database).
/// </summary>
public class BenchmarkRun
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public SystemInfo SystemInfo { get; set; } = new();
    public BenchmarkConfig Config { get; set; } = new();
    public List<BenchmarkResult> Results { get; set; } = new();
    public string Status { get; set; } = "pending"; // pending, running, completed, failed
    public string? ErrorMessage { get; set; }
}

/// <summary>
/// Systeeminformatie van de machine waarop de benchmark draaide.
/// </summary>
public class SystemInfo
{
    public string Platform { get; set; } = "";
    public string PythonVersion { get; set; } = "";
    public string GoVersion { get; set; } = "";
    public string Language { get; set; } = "";
    public string Processor { get; set; } = "";
    public string Machine { get; set; } = "";
    public int CpuCount { get; set; }
}

/// <summary>
/// Configuratie waarmee de benchmark is uitgevoerd.
/// </summary>
public class BenchmarkConfig
{
    public int Iterations { get; set; } = 1000;
    public int Warmup { get; set; } = 100;
    public List<string> Formats { get; set; } = new();
    public List<string> PayloadSizes { get; set; } = new();
    public List<string> SkippedFormats { get; set; } = new();
}

/// <summary>
/// Resultaat van één benchmark (één format + één payload grootte).
/// </summary>
public class BenchmarkResult
{
    public string Format { get; set; } = "";
    public string PayloadSizeLabel { get; set; } = "";
    public int Iterations { get; set; }
    public int SerializedSizeBytes { get; set; }
    public TimingStats SerializeTimeMs { get; set; } = new();
    public TimingStats DeserializeTimeMs { get; set; } = new();
    public TimingStats RoundTripTimeMs { get; set; } = new();
    public MemoryUsage? MemoryUsage { get; set; }
    public CompressionInfo? Compression { get; set; }
    public ThroughputInfo? Throughput { get; set; }
}

/// <summary>
/// Geheugenverbruik metrics voor een benchmark.
/// </summary>
public class MemoryUsage
{
    public long SerializePeakBytes { get; set; }
    public long DeserializePeakBytes { get; set; }
    public long TotalPeakBytes { get; set; }
}

/// <summary>
/// Compressie vergelijking voor geserialiseerde data.
/// </summary>
public class CompressionInfo
{
    public int OriginalBytes { get; set; }
    public int GzipBytes { get; set; }
    public double GzipRatio { get; set; }
    public int? ZstdBytes { get; set; }
    public double? ZstdRatio { get; set; }
}

/// <summary>
/// Doorvoer metrics afgeleid van timing data.
/// </summary>
public class ThroughputInfo
{
    public double SerializeMsgPerSec { get; set; }
    public double DeserializeMsgPerSec { get; set; }
    public double SerializeMbPerSec { get; set; }
    public double DeserializeMbPerSec { get; set; }
}

/// <summary>
/// Statistische metrics voor timing metingen.
/// </summary>
public class TimingStats
{
    public double Mean { get; set; }
    public double Median { get; set; }
    public double Min { get; set; }
    public double Max { get; set; }
    public double StdDev { get; set; }
    public double P95 { get; set; }
    public double P99 { get; set; }
}

/// <summary>
/// Request model voor het starten van een benchmark.
/// </summary>
public class RunBenchmarkRequest
{
    public int Iterations { get; set; } = 1000;
    public int Warmup { get; set; } = 100;
    public List<string> Formats { get; set; } = new() { "json", "bson", "protobuf", "capnproto", "msgpack", "avro", "flatbuffers" };
    public List<string> Sizes { get; set; } = new() { "small", "medium", "large" };
    public string Language { get; set; } = "python";
}

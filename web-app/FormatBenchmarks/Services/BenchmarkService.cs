using System.Diagnostics;
using System.Text;
using System.Text.Json;
using FormatBenchmarks.Models;

namespace FormatBenchmarks.Services;

/// <summary>
/// Service for running benchmarks via Python/Go and managing results.
/// All results are stored in-memory (no database).
/// </summary>
public class BenchmarkService
{
    private readonly List<BenchmarkRun> _runs = new();
    private readonly object _lock = new();
    private readonly ILogger<BenchmarkService> _logger;
    private readonly string _pythonPath;
    private readonly string _scriptPath;
    private readonly string _goPath;

    public BenchmarkService(
        ILogger<BenchmarkService> logger,
        IConfiguration configuration,
        IWebHostEnvironment env)
    {
        _logger = logger;

        var configuredPath = configuration.GetValue<string>("Python:ScriptPath");
        if (string.IsNullOrEmpty(configuredPath))
        {
            // Default: relative path from the project to python-benchmarks
            _scriptPath = Path.GetFullPath(
                Path.Combine(env.ContentRootPath, "..", "..", "python-benchmarks"));
        }
        else
        {
            _scriptPath = Path.GetFullPath(configuredPath);
        }

        // Use venv Python if available; otherwise use configured or system Python
        var configuredPython = configuration.GetValue<string>("Python:Path");
        if (!string.IsNullOrEmpty(configuredPython))
        {
            _pythonPath = configuredPython;
        }
        else
        {
            var venvPython = Path.Combine(_scriptPath, ".venv", "bin", "python");
            _pythonPath = File.Exists(venvPython) ? venvPython : "python3";
        }

        // Configure Go binary path
        var configuredGoPath = configuration.GetValue<string>("Go:BinaryPath");
        if (!string.IsNullOrEmpty(configuredGoPath))
        {
            _goPath = configuredGoPath;
        }
        else
        {
            _goPath = Path.GetFullPath(
                Path.Combine(env.ContentRootPath, "..", "..", "go-benchmarks", "benchmark"));
        }

        _logger.LogInformation("Python path: {PythonPath}", _pythonPath);
        _logger.LogInformation("Script path: {ScriptPath}", _scriptPath);
        _logger.LogInformation("Go binary path: {GoPath}", _goPath);
    }

    /// <summary>
    /// Run a benchmark by launching the Python or Go executable.
    /// </summary>
    public async Task<BenchmarkRun> RunBenchmarkAsync(RunBenchmarkRequest request)
    {
        var language = (request.Language ?? "python").ToLowerInvariant();

        var run = new BenchmarkRun
        {
            Config = new BenchmarkConfig
            {
                Iterations = request.Iterations,
                Warmup = request.Warmup,
                Formats = request.Formats,
                PayloadSizes = request.Sizes,
            },
            Status = "running"
        };

        lock (_lock)
        {
            _runs.Add(run);
        }

        try
        {
            if (language == "go")
            {
                await RunGoBenchmarkAsync(run, request);
            }
            else
            {
                await RunPythonBenchmarkAsync(run, request);
            }

            run.SystemInfo.Language = language;
            run.Status = "completed";
            _logger.LogInformation("Benchmark completed: {Id} ({Count} results, language: {Language})",
                run.Id, run.Results.Count, language);
        }
        catch (Exception ex)
        {
            run.Status = "failed";
            run.ErrorMessage = ex.Message;
            _logger.LogError(ex, "Benchmark error");
        }

        return run;
    }

    /// <summary>
    /// Run benchmark via Python.
    /// </summary>
    private async Task RunPythonBenchmarkAsync(BenchmarkRun run, RunBenchmarkRequest request)
    {
        // Output file for this run
        var resultsDir = Path.Combine(_scriptPath, "results");
        Directory.CreateDirectory(resultsDir);
        var outputPath = Path.Combine(resultsDir, $"run_{run.Id}.json");

        // Build argument list
        var args = new List<string>
        {
            Path.Combine(_scriptPath, "main.py"),
            "--iterations", request.Iterations.ToString(),
            "--warmup", request.Warmup.ToString(),
            "--output", outputPath,
            "--formats"
        };
        args.AddRange(request.Formats);
        args.Add("--sizes");
        args.AddRange(request.Sizes);

        _logger.LogInformation("Start Python benchmark: {Id}", run.Id);
        _logger.LogInformation("Command: {Python} {Args}",
            _pythonPath, string.Join(" ", args));

        // Start Python process
        var psi = new ProcessStartInfo
        {
            FileName = _pythonPath,
            WorkingDirectory = _scriptPath,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        foreach (var arg in args)
            psi.ArgumentList.Add(arg);

        // Set PWD so the Cap'n Proto kj library does not warn
        psi.Environment["PWD"] = _scriptPath;

        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException("Could not start Python process");

        var stdout = await process.StandardOutput.ReadToEndAsync();
        var stderr = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();

        _logger.LogInformation("Python stdout:\n{Output}", stdout);
        if (!string.IsNullOrEmpty(stderr))
            _logger.LogWarning("Python stderr:\n{Error}", stderr);

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"Python exit code: {process.ExitCode}\n{stderr}");
        }

        // Read and parse results
        if (File.Exists(outputPath))
        {
            var json = await File.ReadAllTextAsync(outputPath);
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            };

            var resultData = JsonSerializer.Deserialize<PythonOutput>(json, options);

            if (resultData != null)
            {
                run.SystemInfo = resultData.SystemInfo ?? new SystemInfo();
                run.Config = resultData.Config ?? run.Config;
                run.Results = resultData.Results ?? new List<BenchmarkResult>();
                run.Timestamp = DateTime.TryParse(resultData.Timestamp, out var ts)
                    ? ts : DateTime.UtcNow;
            }
        }
        else
        {
            throw new InvalidOperationException($"Output file not found: {outputPath}");
        }
    }

    /// <summary>
    /// Run benchmark via Go binary.
    /// </summary>
    private async Task RunGoBenchmarkAsync(BenchmarkRun run, RunBenchmarkRequest request)
    {
        // Check if Go binary exists
        if (!File.Exists(_goPath))
        {
            throw new InvalidOperationException(
                $"Go benchmark binary not found: {_goPath}. Build it first with 'go build'.");
        }

        var goDir = Path.GetDirectoryName(_goPath) ?? _goPath;
        var resultsDir = Path.Combine(goDir, "results");
        Directory.CreateDirectory(resultsDir);
        var outputPath = Path.Combine(resultsDir, $"run_{run.Id}.json");

        _logger.LogInformation("Start Go benchmark: {Id}", run.Id);

        var psi = new ProcessStartInfo
        {
            FileName = _goPath,
            WorkingDirectory = goDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        psi.ArgumentList.Add("-iterations");
        psi.ArgumentList.Add(request.Iterations.ToString());
        psi.ArgumentList.Add("-warmup");
        psi.ArgumentList.Add(request.Warmup.ToString());
        psi.ArgumentList.Add("-formats");
        psi.ArgumentList.Add(string.Join(",", request.Formats));
        psi.ArgumentList.Add("-sizes");
        psi.ArgumentList.Add(string.Join(",", request.Sizes));
        psi.ArgumentList.Add("-output");
        psi.ArgumentList.Add(outputPath);

        _logger.LogInformation("Command: {Go} {Args}",
            _goPath, string.Join(" ", psi.ArgumentList));

        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException("Could not start Go process");

        var stdout = await process.StandardOutput.ReadToEndAsync();
        var stderr = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();

        _logger.LogInformation("Go stdout:\n{Output}", stdout);
        if (!string.IsNullOrEmpty(stderr))
            _logger.LogWarning("Go stderr:\n{Error}", stderr);

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"Go exit code: {process.ExitCode}\n{stderr}");
        }

        // Read and parse Go results (same JSON structure as Python)
        if (File.Exists(outputPath))
        {
            var json = await File.ReadAllTextAsync(outputPath);
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            };

            var resultData = JsonSerializer.Deserialize<PythonOutput>(json, options);

            if (resultData != null)
            {
                run.SystemInfo = resultData.SystemInfo ?? new SystemInfo();
                run.Config = resultData.Config ?? run.Config;
                run.Results = resultData.Results ?? new List<BenchmarkResult>();
                run.Timestamp = DateTime.TryParse(resultData.Timestamp, out var ts)
                    ? ts : DateTime.UtcNow;
            }
        }
        else
        {
            throw new InvalidOperationException($"Go output file not found: {outputPath}");
        }
    }

    /// <summary>
    /// Get all benchmark runs.
    /// </summary>
    public List<BenchmarkRun> GetAllRuns()
    {
        lock (_lock)
        {
            return _runs.ToList();
        }
    }

    /// <summary>
    /// Get a specific benchmark run.
    /// </summary>
    public BenchmarkRun? GetRun(Guid id)
    {
        lock (_lock)
        {
            return _runs.FirstOrDefault(r => r.Id == id);
        }
    }

    /// <summary>
    /// Export benchmark results to CSV format.
    /// </summary>
    public string ExportToCsv(BenchmarkRun run)
    {
        var sb = new StringBuilder();

        // Header
        sb.AppendLine(string.Join(",",
            "Format", "PayloadSize", "Iterations", "SerializedSizeBytes",
            "SerializeMeanMs", "SerializeMedianMs", "SerializeMinMs", "SerializeMaxMs",
            "SerializeStdDevMs", "SerializeP95Ms", "SerializeP99Ms",
            "DeserializeMeanMs", "DeserializeMedianMs", "DeserializeMinMs", "DeserializeMaxMs",
            "DeserializeStdDevMs", "DeserializeP95Ms", "DeserializeP99Ms",
            "RoundTripMeanMs", "RoundTripMedianMs", "RoundTripMinMs", "RoundTripMaxMs",
            "RoundTripStdDevMs", "RoundTripP95Ms", "RoundTripP99Ms",
            "MemSerializePeakBytes", "MemDeserializePeakBytes", "MemTotalPeakBytes",
            "GzipBytes", "GzipRatio", "ZstdBytes", "ZstdRatio",
            "SerMsgPerSec", "DeserMsgPerSec", "SerMbPerSec", "DeserMbPerSec"
        ));

        // Data rows
        foreach (var r in run.Results)
        {
            var s = r.SerializeTimeMs;
            var d = r.DeserializeTimeMs;
            var rt = r.RoundTripTimeMs;
            var m = r.MemoryUsage;
            var c = r.Compression;
            var t = r.Throughput;

            sb.AppendLine(string.Join(",",
                r.Format, r.PayloadSizeLabel, r.Iterations, r.SerializedSizeBytes,
                s.Mean, s.Median, s.Min, s.Max, s.StdDev, s.P95, s.P99,
                d.Mean, d.Median, d.Min, d.Max, d.StdDev, d.P95, d.P99,
                rt.Mean, rt.Median, rt.Min, rt.Max, rt.StdDev, rt.P95, rt.P99,
                m?.SerializePeakBytes ?? 0, m?.DeserializePeakBytes ?? 0, m?.TotalPeakBytes ?? 0,
                c?.GzipBytes ?? 0, c?.GzipRatio ?? 0, c?.ZstdBytes ?? 0, c?.ZstdRatio ?? 0,
                t?.SerializeMsgPerSec ?? 0, t?.DeserializeMsgPerSec ?? 0,
                t?.SerializeMbPerSec ?? 0, t?.DeserializeMbPerSec ?? 0
            ));
        }

        return sb.ToString();
    }

    /// <summary>
    /// Helper class for deserializing Python output.
    /// </summary>
    private class PythonOutput
    {
        public string? Timestamp { get; set; }
        public SystemInfo? SystemInfo { get; set; }
        public BenchmarkConfig? Config { get; set; }
        public List<BenchmarkResult>? Results { get; set; }
    }
}

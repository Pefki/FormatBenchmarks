using System.Diagnostics;
using System.Text;
using System.Text.Json;
using FormatBenchmarks.Models;

namespace FormatBenchmarks.Services;

/// <summary>
/// Service voor het uitvoeren van benchmarks via Python en het beheren van resultaten.
/// Alle resultaten worden in-memory opgeslagen (geen database).
/// </summary>
public class BenchmarkService
{
    private readonly List<BenchmarkRun> _runs = new();
    private readonly object _lock = new();
    private readonly ILogger<BenchmarkService> _logger;
    private readonly string _pythonPath;
    private readonly string _scriptPath;

    public BenchmarkService(
        ILogger<BenchmarkService> logger,
        IConfiguration configuration,
        IWebHostEnvironment env)
    {
        _logger = logger;

        var configuredPath = configuration.GetValue<string>("Python:ScriptPath");
        if (string.IsNullOrEmpty(configuredPath))
        {
            // Standaard: relatief pad vanuit het project naar python-benchmarks
            _scriptPath = Path.GetFullPath(
                Path.Combine(env.ContentRootPath, "..", "..", "python-benchmarks"));
        }
        else
        {
            _scriptPath = Path.GetFullPath(configuredPath);
        }

        // Gebruik de venv Python als die bestaat, anders de geconfigureerde of systeem Python
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

        _logger.LogInformation("Python pad: {PythonPath}", _pythonPath);
        _logger.LogInformation("Script pad: {ScriptPath}", _scriptPath);
    }

    /// <summary>
    /// Voer een benchmark uit door het Python script te starten.
    /// </summary>
    public async Task<BenchmarkRun> RunBenchmarkAsync(RunBenchmarkRequest request)
    {
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
            // Output bestand voor deze run
            var resultsDir = Path.Combine(_scriptPath, "results");
            Directory.CreateDirectory(resultsDir);
            var outputPath = Path.Combine(resultsDir, $"run_{run.Id}.json");

            // Bouw argumenten lijst
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

            _logger.LogInformation("Start benchmark: {Id}", run.Id);
            _logger.LogInformation("Commando: {Python} {Args}",
                _pythonPath, string.Join(" ", args));

            // Start Python proces
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

            using var process = Process.Start(psi)
                ?? throw new InvalidOperationException("Kon Python proces niet starten");

            var stdout = await process.StandardOutput.ReadToEndAsync();
            var stderr = await process.StandardError.ReadToEndAsync();
            await process.WaitForExitAsync();

            _logger.LogInformation("Python stdout:\n{Output}", stdout);
            if (!string.IsNullOrEmpty(stderr))
                _logger.LogWarning("Python stderr:\n{Error}", stderr);

            if (process.ExitCode != 0)
            {
                run.Status = "failed";
                run.ErrorMessage = $"Python exit code: {process.ExitCode}\n{stderr}";
                _logger.LogError("Benchmark mislukt: {Error}", stderr);
                return run;
            }

            // Lees en parse resultaten
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
                run.Status = "failed";
                run.ErrorMessage = $"Output bestand niet gevonden: {outputPath}";
                return run;
            }

            run.Status = "completed";
            _logger.LogInformation("Benchmark voltooid: {Id} ({Count} resultaten)",
                run.Id, run.Results.Count);
        }
        catch (Exception ex)
        {
            run.Status = "failed";
            run.ErrorMessage = ex.Message;
            _logger.LogError(ex, "Benchmark fout");
        }

        return run;
    }

    /// <summary>
    /// Haal alle benchmark runs op.
    /// </summary>
    public List<BenchmarkRun> GetAllRuns()
    {
        lock (_lock)
        {
            return _runs.ToList();
        }
    }

    /// <summary>
    /// Haal een specifieke benchmark run op.
    /// </summary>
    public BenchmarkRun? GetRun(Guid id)
    {
        lock (_lock)
        {
            return _runs.FirstOrDefault(r => r.Id == id);
        }
    }

    /// <summary>
    /// Exporteer benchmark resultaten naar CSV formaat.
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
            "RoundTripStdDevMs", "RoundTripP95Ms", "RoundTripP99Ms"
        ));

        // Data rijen
        foreach (var r in run.Results)
        {
            var s = r.SerializeTimeMs;
            var d = r.DeserializeTimeMs;
            var rt = r.RoundTripTimeMs;

            sb.AppendLine(string.Join(",",
                r.Format, r.PayloadSizeLabel, r.Iterations, r.SerializedSizeBytes,
                s.Mean, s.Median, s.Min, s.Max, s.StdDev, s.P95, s.P99,
                d.Mean, d.Median, d.Min, d.Max, d.StdDev, d.P95, d.P99,
                rt.Mean, rt.Median, rt.Min, rt.Max, rt.StdDev, rt.P95, rt.P99
            ));
        }

        return sb.ToString();
    }

    /// <summary>
    /// Helper klasse voor het deserialiseren van Python output.
    /// </summary>
    private class PythonOutput
    {
        public string? Timestamp { get; set; }
        public SystemInfo? SystemInfo { get; set; }
        public BenchmarkConfig? Config { get; set; }
        public List<BenchmarkResult>? Results { get; set; }
    }
}

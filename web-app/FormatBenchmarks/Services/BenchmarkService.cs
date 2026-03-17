using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
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
    private readonly string _rustPath;
    private readonly string _javaPath;
    private readonly string _javaJarPath;

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

        // Configure Rust binary path
        var configuredRustPath = configuration.GetValue<string>("Rust:BinaryPath");
        if (!string.IsNullOrEmpty(configuredRustPath))
        {
            _rustPath = configuredRustPath;
        }
        else
        {
            _rustPath = Path.GetFullPath(
                Path.Combine(env.ContentRootPath, "..", "..", "rust-benchmarks", "target", "release", "benchmark"));
        }

        var configuredJavaPath = configuration.GetValue<string>("Java:Path");
        _javaPath = !string.IsNullOrWhiteSpace(configuredJavaPath) ? configuredJavaPath : "java";

        var configuredJavaJarPath = configuration.GetValue<string>("Java:JarPath");
        if (!string.IsNullOrWhiteSpace(configuredJavaJarPath))
        {
            _javaJarPath = Path.GetFullPath(configuredJavaJarPath);
        }
        else
        {
            var javaJarCandidates = new[]
            {
                Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "..", "java-benchmarks", "target", "benchmark.jar")),
                Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "java-benchmarks", "benchmark.jar")),
                "/app/java-benchmarks/benchmark.jar",
            };

            _javaJarPath = javaJarCandidates.FirstOrDefault(File.Exists)
                ?? javaJarCandidates[0];
        }

        _logger.LogInformation("Python path: {PythonPath}", _pythonPath);
        _logger.LogInformation("Script path: {ScriptPath}", _scriptPath);
        _logger.LogInformation("Go binary path: {GoPath}", _goPath);
        _logger.LogInformation("Rust binary path: {RustPath}", _rustPath);
        _logger.LogInformation("Java path: {JavaPath}", _javaPath);
        _logger.LogInformation("Java jar path: {JavaJarPath}", _javaJarPath);
    }

    /// <summary>
    /// Run a benchmark by launching the Python or Go executable.
    /// </summary>
    public async Task<BenchmarkRun> RunBenchmarkAsync(RunBenchmarkRequest request)
    {
        var language = (request.Language ?? "python").Trim().ToLowerInvariant();
        int? normalizedNestingDepth = request.NestingDepth.HasValue
            ? Math.Clamp(request.NestingDepth.Value, 1, 8)
            : null;
        request.NestingDepth = normalizedNestingDepth;

        var run = new BenchmarkRun
        {
            Config = new BenchmarkConfig
            {
                Iterations = request.Iterations,
                Warmup = request.Warmup,
                NestingDepth = normalizedNestingDepth,
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
            else if (language == "rust")
            {
                await RunRustBenchmarkAsync(run, request);
            }
            else if (language == "java")
            {
                await RunJavaBenchmarkAsync(run, request);
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
    /// Run benchmark via Java jar.
    /// </summary>
    private async Task RunJavaBenchmarkAsync(BenchmarkRun run, RunBenchmarkRequest request)
    {
        if (!File.Exists(_javaJarPath))
        {
            throw new InvalidOperationException(
                $"Java benchmark jar not found: {_javaJarPath}. " +
                "For local runs, build it with 'mvn -f java-benchmarks/pom.xml package'. " +
                "For container runs, rebuild the image so /app/java-benchmarks/benchmark.jar is included.");
        }

        var javaDir = Path.GetDirectoryName(_javaJarPath) ?? _javaJarPath;
        var resultsDir = Path.Combine(javaDir, "results");
        Directory.CreateDirectory(resultsDir);
        var outputPath = Path.Combine(resultsDir, $"run_{run.Id}.json");

        _logger.LogInformation("Start Java benchmark: {Id}", run.Id);

        ProcessStartInfo BuildPsi(bool includeNestingDepth)
        {
            var psi = new ProcessStartInfo
            {
                FileName = _javaPath,
                WorkingDirectory = javaDir,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            psi.ArgumentList.Add("-jar");
            psi.ArgumentList.Add(_javaJarPath);
            psi.ArgumentList.Add("--iterations");
            psi.ArgumentList.Add(request.Iterations.ToString());
            psi.ArgumentList.Add("--warmup");
            psi.ArgumentList.Add(request.Warmup.ToString());
            psi.ArgumentList.Add("--formats");
            psi.ArgumentList.Add(string.Join(",", request.Formats));
            psi.ArgumentList.Add("--sizes");
            psi.ArgumentList.Add(string.Join(",", request.Sizes));
            if (includeNestingDepth && request.NestingDepth is int javaDepth)
            {
                psi.ArgumentList.Add("--nesting-depth");
                psi.ArgumentList.Add(javaDepth.ToString());
            }
            psi.ArgumentList.Add("--output");
            psi.ArgumentList.Add(outputPath);
            return psi;
        }

        var psi = BuildPsi(includeNestingDepth: true);
        _logger.LogInformation("Command: {Java} {Args}",
            _javaPath, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);

        if (exitCode != 0
            && request.NestingDepth.HasValue
            && IsUnknownNestingDepthFlagError(stdout, stderr))
        {
            _logger.LogWarning(
                "Java artifact does not support nesting-depth yet. Rebuilding and retrying with --nesting-depth.");
            await RebuildJavaBenchmarkAsync();
            psi = BuildPsi(includeNestingDepth: true);
            _logger.LogInformation("Retry command after rebuild: {Java} {Args}",
                _javaPath, string.Join(" ", psi.ArgumentList));
            (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        }

        _logger.LogInformation("Java stdout:\n{Output}", stdout);
        if (!string.IsNullOrEmpty(stderr))
            _logger.LogWarning("Java stderr:\n{Error}", stderr);

        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Java exit code: {exitCode}\n{stderr}");
        }

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
            throw new InvalidOperationException($"Java output file not found: {outputPath}");
        }
    }

    /// <summary>
    /// Run benchmark via Rust binary.
    /// </summary>
    private async Task RunRustBenchmarkAsync(BenchmarkRun run, RunBenchmarkRequest request)
    {
        if (!File.Exists(_rustPath))
        {
            throw new InvalidOperationException(
                $"Rust benchmark binary not found: {_rustPath}. Build it first with 'cargo build --release'.");
        }

        var rustDir = Path.GetDirectoryName(_rustPath) ?? _rustPath;
        var resultsDir = Path.Combine(rustDir, "results");
        Directory.CreateDirectory(resultsDir);
        var outputPath = Path.Combine(resultsDir, $"run_{run.Id}.json");
        var processStartTime = DateTime.UtcNow;

        _logger.LogInformation("Start Rust benchmark: {Id}", run.Id);

        ProcessStartInfo BuildPsi(bool includeNestingDepth)
        {
            var psi = new ProcessStartInfo
            {
                FileName = _rustPath,
                WorkingDirectory = rustDir,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
            };

            psi.ArgumentList.Add("--iterations");
            psi.ArgumentList.Add(request.Iterations.ToString());
            psi.ArgumentList.Add("--warmup");
            psi.ArgumentList.Add(request.Warmup.ToString());
            psi.ArgumentList.Add("--formats");
            psi.ArgumentList.Add(string.Join(",", request.Formats));
            psi.ArgumentList.Add("--sizes");
            psi.ArgumentList.Add(string.Join(",", request.Sizes));
            if (includeNestingDepth && request.NestingDepth is int rustDepth)
            {
                psi.ArgumentList.Add("--nesting-depth");
                psi.ArgumentList.Add(rustDepth.ToString());
            }
            psi.ArgumentList.Add("--output");
            psi.ArgumentList.Add(outputPath);
            return psi;
        }

        var psi = BuildPsi(includeNestingDepth: true);
        _logger.LogInformation("Command: {Rust} {Args}",
            _rustPath, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);

        if (exitCode != 0
            && request.NestingDepth.HasValue
            && IsUnknownNestingDepthFlagError(stdout, stderr))
        {
            _logger.LogWarning(
                "Rust binary does not support nesting-depth yet. Rebuilding and retrying with --nesting-depth.");
            await RebuildRustBenchmarkAsync();
            psi = BuildPsi(includeNestingDepth: true);
            _logger.LogInformation("Retry command after rebuild: {Rust} {Args}",
                _rustPath, string.Join(" ", psi.ArgumentList));
            (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        }

        _logger.LogInformation("Rust stdout:\n{Output}", stdout);
        if (!string.IsNullOrEmpty(stderr))
            _logger.LogWarning("Rust stderr:\n{Error}", stderr);

        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Rust exit code: {exitCode}\n{stderr}");
        }

        var resolvedOutputPath = ResolveRustOutputPath(
            expectedOutputPath: outputPath,
            rustDir: rustDir,
            stdout: stdout,
            processStartTime: processStartTime);

        if (resolvedOutputPath != null)
        {
            if (!string.Equals(resolvedOutputPath, outputPath, StringComparison.Ordinal))
            {
                _logger.LogWarning(
                    "Rust run {RunId}: expected output at {ExpectedPath} but found output at {ResolvedPath}",
                    run.Id,
                    outputPath,
                    resolvedOutputPath);
            }

            var json = await File.ReadAllTextAsync(resolvedOutputPath);
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
                var missingMemory = 0;
                foreach (var benchmark in run.Results)
                {
                    if (benchmark.MemoryUsage == null)
                    {
                        benchmark.MemoryUsage = new MemoryUsage
                        {
                            SerializePeakBytes = 0,
                            DeserializePeakBytes = 0,
                            TotalPeakBytes = 0,
                        };
                        missingMemory++;
                    }
                }

                if (missingMemory > 0)
                {
                    _logger.LogWarning(
                        "Rust run {RunId}: {Count} results had no memory_usage in output. Falling back to zero values.",
                        run.Id,
                        missingMemory);
                }

                run.Timestamp = DateTime.TryParse(resultData.Timestamp, out var ts)
                    ? ts : DateTime.UtcNow;
            }
        }
        else
        {
            throw new InvalidOperationException(
                $"Rust output file not found. Expected path: {outputPath}. " +
                $"Checked fallback paths under {Path.Combine(rustDir, "results")} and Rust stdout hints. " +
                $"Rust stdout tail: {TailForLog(stdout)} | Rust stderr tail: {TailForLog(stderr)}");
        }
    }

    private static string? ResolveRustOutputPath(
        string expectedOutputPath,
        string rustDir,
        string stdout,
        DateTime processStartTime)
    {
        if (File.Exists(expectedOutputPath))
        {
            return expectedOutputPath;
        }

        var stdoutPath = TryExtractRustOutputPathFromStdout(stdout, rustDir);
        if (stdoutPath != null && File.Exists(stdoutPath))
        {
            return stdoutPath;
        }

        var candidates = new[]
        {
            Path.Combine(rustDir, "results", "benchmark_results.json"),
            Path.Combine(rustDir, "benchmark_results.json"),
            Path.Combine(rustDir, "results", $"run_{Path.GetFileNameWithoutExtension(expectedOutputPath).Replace("run_", string.Empty)}.json"),
        };

        foreach (var candidate in candidates.Distinct(StringComparer.Ordinal))
        {
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        var resultsDir = Path.Combine(rustDir, "results");
        if (!Directory.Exists(resultsDir))
        {
            return null;
        }

        var mostRecent = new DirectoryInfo(resultsDir)
            .EnumerateFiles("*.json", SearchOption.TopDirectoryOnly)
            .Where(file => file.LastWriteTimeUtc >= processStartTime.AddSeconds(-2))
            .OrderByDescending(file => file.LastWriteTimeUtc)
            .FirstOrDefault();

        return mostRecent?.FullName;
    }

    private static string? TryExtractRustOutputPathFromStdout(string stdout, string rustDir)
    {
        if (string.IsNullOrWhiteSpace(stdout))
        {
            return null;
        }

        var match = Regex.Match(
            stdout,
            @"Results written to:\s*(.+)",
            RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);

        if (!match.Success)
        {
            return null;
        }

        var rawPath = match.Groups[1].Value.Trim();
        if (string.IsNullOrEmpty(rawPath))
        {
            return null;
        }

        return Path.IsPathRooted(rawPath)
            ? rawPath
            : Path.GetFullPath(Path.Combine(rustDir, rawPath));
    }

    private static string TailForLog(string value, int maxChars = 600)
    {
        if (string.IsNullOrEmpty(value))
        {
            return "<empty>";
        }

        return value.Length <= maxChars
            ? value
            : value[^maxChars..];
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
        if (request.NestingDepth is int depth)
        {
            args.Add("--nesting-depth");
            args.Add(depth.ToString());
        }

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

        ProcessStartInfo BuildPsi(bool includeNestingDepth)
        {
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
            if (includeNestingDepth && request.NestingDepth is int goDepth)
            {
                psi.ArgumentList.Add("-nesting-depth");
                psi.ArgumentList.Add(goDepth.ToString());
            }
            psi.ArgumentList.Add("-output");
            psi.ArgumentList.Add(outputPath);
            return psi;
        }

        var psi = BuildPsi(includeNestingDepth: true);
        _logger.LogInformation("Command: {Go} {Args}",
            _goPath, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);

        if (exitCode != 0
            && request.NestingDepth.HasValue
            && IsUnknownNestingDepthFlagError(stdout, stderr))
        {
            _logger.LogWarning(
                "Go binary does not support nesting-depth yet. Rebuilding and retrying with -nesting-depth.");
            await RebuildGoBenchmarkAsync();
            psi = BuildPsi(includeNestingDepth: true);
            _logger.LogInformation("Retry command after rebuild: {Go} {Args}",
                _goPath, string.Join(" ", psi.ArgumentList));
            (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        }

        _logger.LogInformation("Go stdout:\n{Output}", stdout);
        if (!string.IsNullOrEmpty(stderr))
            _logger.LogWarning("Go stderr:\n{Error}", stderr);

        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Go exit code: {exitCode}\n{stderr}");
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

    private static bool IsUnknownNestingDepthFlagError(string stdout, string stderr)
    {
        var combined = $"{stdout}\n{stderr}".ToLowerInvariant();
        return combined.Contains("nesting-depth")
            && (combined.Contains("unknown argument")
                || combined.Contains("flag provided but not defined"));
    }

    private async Task RebuildGoBenchmarkAsync()
    {
        var startDir = Path.GetDirectoryName(_goPath) ?? _goPath;
        var projectDir = FindDirectoryContaining(startDir, "go.mod")
            ?? throw new InvalidOperationException($"Could not find go.mod starting from {startDir}");

        var psi = new ProcessStartInfo
        {
            FileName = "go",
            WorkingDirectory = projectDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("build");
        psi.ArgumentList.Add("-o");
        psi.ArgumentList.Add(_goPath);
        psi.ArgumentList.Add(".");

        _logger.LogInformation("Rebuilding Go benchmark binary: {Command} {Args}",
            psi.FileName, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Go rebuild failed (exit {exitCode})\n{stderr}\n{stdout}");
        }
    }

    private async Task RebuildRustBenchmarkAsync()
    {
        var startDir = Path.GetDirectoryName(_rustPath) ?? _rustPath;
        var projectDir = FindDirectoryContaining(startDir, "Cargo.toml")
            ?? throw new InvalidOperationException($"Could not find Cargo.toml starting from {startDir}");

        var psi = new ProcessStartInfo
        {
            FileName = "cargo",
            WorkingDirectory = projectDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("build");
        psi.ArgumentList.Add("--release");

        _logger.LogInformation("Rebuilding Rust benchmark binary: {Command} {Args}",
            psi.FileName, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Rust rebuild failed (exit {exitCode})\n{stderr}\n{stdout}");
        }
    }

    private async Task RebuildJavaBenchmarkAsync()
    {
        var startDir = Path.GetDirectoryName(_javaJarPath) ?? _javaJarPath;
        var projectDir = FindDirectoryContaining(startDir, "pom.xml")
            ?? throw new InvalidOperationException($"Could not find pom.xml starting from {startDir}");

        var psi = new ProcessStartInfo
        {
            FileName = "mvn",
            WorkingDirectory = projectDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add("-DskipTests");
        psi.ArgumentList.Add("package");

        _logger.LogInformation("Rebuilding Java benchmark artifact: {Command} {Args}",
            psi.FileName, string.Join(" ", psi.ArgumentList));

        var (exitCode, stdout, stderr) = await RunProcessAsync(psi);
        if (exitCode != 0)
        {
            throw new InvalidOperationException($"Java rebuild failed (exit {exitCode})\n{stderr}\n{stdout}");
        }
    }

    private static string? FindDirectoryContaining(string startPath, string markerFileName)
    {
        var current = new DirectoryInfo(startPath);
        if (!current.Exists && current.Parent != null)
        {
            current = current.Parent;
        }

        while (current != null)
        {
            var marker = Path.Combine(current.FullName, markerFileName);
            if (File.Exists(marker))
            {
                return current.FullName;
            }
            current = current.Parent;
        }

        return null;
    }

    private static async Task<(int ExitCode, string Stdout, string Stderr)> RunProcessAsync(ProcessStartInfo psi)
    {
        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException($"Could not start process: {psi.FileName}");

        var stdout = await process.StandardOutput.ReadToEndAsync();
        var stderr = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();

        return (process.ExitCode, stdout, stderr);
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
            "PayloadNestingDepth",
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
                r.Format, r.PayloadSizeLabel, r.Iterations, r.SerializedSizeBytes, r.PayloadNestingDepth,
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

using System.Text;
using System.Text.Json;
using FormatBenchmarks.Models;
using FormatBenchmarks.Services;
using Microsoft.AspNetCore.Mvc;

namespace FormatBenchmarks.Controllers;

/// <summary>
/// API controller for benchmark operations.
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class BenchmarkController : ControllerBase
{
    private readonly BenchmarkService _service;
    private readonly ILogger<BenchmarkController> _logger;

    public BenchmarkController(BenchmarkService service, ILogger<BenchmarkController> logger)
    {
        _service = service;
        _logger = logger;
    }

    /// <summary>
    /// Start a new benchmark run.
    /// POST /api/benchmark/run
    /// </summary>
    [HttpPost("run")]
    public async Task<ActionResult<BenchmarkRun>> Run([FromBody] RunBenchmarkRequest request)
    {
        _logger.LogInformation(
            "Benchmark started: {Formats} formats, {Sizes} sizes, {Iterations} iterations",
            request.Formats.Count, request.Sizes.Count, request.Iterations);

        var result = await _service.RunBenchmarkAsync(request);

        if (result.Status == "failed")
        {
            _logger.LogWarning("Benchmark failed: {Error}", result.ErrorMessage);
        }

        return Ok(result);
    }

    /// <summary>
    /// Get all benchmark results.
    /// GET /api/benchmark/results
    /// </summary>
    [HttpGet("results")]
    public ActionResult<List<BenchmarkRun>> GetAll()
    {
        return Ok(_service.GetAllRuns());
    }

    /// <summary>
    /// Compare two benchmark runs.
    /// GET /api/benchmark/compare?runA={id}&runB={id}
    /// </summary>
    [HttpGet("compare")]
    public ActionResult Compare([FromQuery] Guid runA, [FromQuery] Guid runB)
    {
        var a = _service.GetRun(runA);
        var b = _service.GetRun(runB);

        if (a == null)
            return NotFound(new { message = $"Benchmark run {runA} not found" });
        if (b == null)
            return NotFound(new { message = $"Benchmark run {runB} not found" });

        return Ok(new { runA = a, runB = b });
    }

    /// <summary>
    /// Get a specific benchmark run.
    /// GET /api/benchmark/results/{id}
    /// </summary>
    [HttpGet("results/{id:guid}")]
    public ActionResult<BenchmarkRun> Get(Guid id)
    {
        var run = _service.GetRun(id);
        if (run == null)
            return NotFound(new { message = $"Benchmark run {id} not found" });

        return Ok(run);
    }

    /// <summary>
    /// Export benchmark results as JSON or CSV.
    /// GET /api/benchmark/export/{id}?format=json|csv
    /// </summary>
    [HttpGet("export/{id:guid}")]
    public ActionResult Export(Guid id, [FromQuery] string format = "json")
    {
        var run = _service.GetRun(id);
        if (run == null)
            return NotFound(new { message = $"Benchmark run {id} not found" });

        if (format.Equals("csv", StringComparison.OrdinalIgnoreCase))
        {
            var csv = _service.ExportToCsv(run);
            return File(
                Encoding.UTF8.GetBytes(csv),
                "text/csv",
                $"benchmark_{id}.csv");
        }

        // Default: JSON export
        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        };
        var json = JsonSerializer.Serialize(run, jsonOptions);
        return File(
            Encoding.UTF8.GetBytes(json),
            "application/json",
            $"benchmark_{id}.json");
    }
}

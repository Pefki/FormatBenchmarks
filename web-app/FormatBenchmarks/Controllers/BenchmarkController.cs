using System.Text;
using System.Text.Json;
using FormatBenchmarks.Models;
using FormatBenchmarks.Services;
using Microsoft.AspNetCore.Mvc;

namespace FormatBenchmarks.Controllers;

/// <summary>
/// API Controller voor benchmark operaties.
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
    /// Start een nieuwe benchmark uitvoering.
    /// POST /api/benchmark/run
    /// </summary>
    [HttpPost("run")]
    public async Task<ActionResult<BenchmarkRun>> Run([FromBody] RunBenchmarkRequest request)
    {
        _logger.LogInformation(
            "Benchmark gestart: {Formats} formats, {Sizes} groottes, {Iterations} iteraties",
            request.Formats.Count, request.Sizes.Count, request.Iterations);

        var result = await _service.RunBenchmarkAsync(request);

        if (result.Status == "failed")
        {
            _logger.LogWarning("Benchmark mislukt: {Error}", result.ErrorMessage);
        }

        return Ok(result);
    }

    /// <summary>
    /// Haal alle benchmark resultaten op.
    /// GET /api/benchmark/results
    /// </summary>
    [HttpGet("results")]
    public ActionResult<List<BenchmarkRun>> GetAll()
    {
        return Ok(_service.GetAllRuns());
    }

    /// <summary>
    /// Haal een specifieke benchmark run op.
    /// GET /api/benchmark/results/{id}
    /// </summary>
    [HttpGet("results/{id:guid}")]
    public ActionResult<BenchmarkRun> Get(Guid id)
    {
        var run = _service.GetRun(id);
        if (run == null)
            return NotFound(new { message = $"Benchmark run {id} niet gevonden" });

        return Ok(run);
    }

    /// <summary>
    /// Exporteer benchmark resultaten als JSON of CSV.
    /// GET /api/benchmark/export/{id}?format=json|csv
    /// </summary>
    [HttpGet("export/{id:guid}")]
    public ActionResult Export(Guid id, [FromQuery] string format = "json")
    {
        var run = _service.GetRun(id);
        if (run == null)
            return NotFound(new { message = $"Benchmark run {id} niet gevonden" });

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

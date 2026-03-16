using FormatBenchmarks.Services;

var builder = WebApplication.CreateBuilder(args);

// Cloud Run sets PORT (often 8080). Fall back to 5000 for local runs.
var port = Environment.GetEnvironmentVariable("PORT") ?? "5000";
builder.WebHost.UseUrls($"http://0.0.0.0:{port}");

// Register services
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        // CamelCase for JSON responses to the frontend
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
        options.JsonSerializerOptions.WriteIndented = false;
    });

// BenchmarkService as singleton (in-memory storage)
builder.Services.AddSingleton<BenchmarkService>();

var app = builder.Build();

// Serve static files (wwwroot)
app.UseStaticFiles();

// API controllers
app.MapControllers();

// Fallback to index.html for SPA-like navigation
app.MapFallbackToFile("index.html");

// Startup message
app.Logger.LogInformation("Format Benchmarks web application started");
app.Logger.LogInformation("Listening on http://0.0.0.0:{Port}", port);

app.Run();

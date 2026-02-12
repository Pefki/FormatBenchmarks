using FormatBenchmarks.Services;

var builder = WebApplication.CreateBuilder(args);

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
app.Logger.LogInformation("Open http://localhost:5000 in your browser");

app.Run();

using FormatBenchmarks.Services;

var builder = WebApplication.CreateBuilder(args);

// Services registreren
builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        // CamelCase voor JSON responses naar de frontend
        options.JsonSerializerOptions.PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.CamelCase;
        options.JsonSerializerOptions.WriteIndented = false;
    });

// BenchmarkService als singleton (in-memory opslag)
builder.Services.AddSingleton<BenchmarkService>();

var app = builder.Build();

// Static files serveren (wwwroot)
app.UseStaticFiles();

// API controllers
app.MapControllers();

// Fallback naar index.html voor SPA-achtige navigatie
app.MapFallbackToFile("index.html");

// Startup bericht
app.Logger.LogInformation("Format Benchmarks web applicatie gestart");
app.Logger.LogInformation("Open http://localhost:5000 in je browser");

app.Run();

# ---- Stage 1: Build .NET app ----
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Kopieer csproj en restore dependencies
COPY web-app/FormatBenchmarks/FormatBenchmarks.csproj ./web-app/FormatBenchmarks/
RUN dotnet restore web-app/FormatBenchmarks/FormatBenchmarks.csproj

# Kopieer rest van de web-app code en publiceer
COPY web-app/ ./web-app/
RUN dotnet publish web-app/FormatBenchmarks/FormatBenchmarks.csproj \
    -c Release -o /app/publish --no-restore

# ---- Stage 2: Runtime image ----
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

# Python installeren voor benchmark uitvoering
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Python benchmarks kopiëren en venv opzetten
COPY python-benchmarks/ /app/python-benchmarks/
RUN python3 -m venv /app/python-benchmarks/.venv && \
    /app/python-benchmarks/.venv/bin/pip install --no-cache-dir \
        -r /app/python-benchmarks/requirements.txt

# Compileer protobuf schema
RUN /app/python-benchmarks/.venv/bin/python /app/python-benchmarks/compile_schemas.py

# Gepubliceerde .NET app kopiëren
COPY --from=build /app/publish .

# Configuratie: verwijs Python naar de venv in de container
ENV ASPNETCORE_URLS=http://+:5000
ENV Python__Path=/app/python-benchmarks/.venv/bin/python
ENV Python__ScriptPath=/app/python-benchmarks

EXPOSE 5000

ENTRYPOINT ["dotnet", "FormatBenchmarks.dll"]

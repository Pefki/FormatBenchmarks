# ---- Stage 1: Build .NET app ----
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build-dotnet
WORKDIR /src

# Copy csproj and restore dependencies
COPY web-app/FormatBenchmarks/FormatBenchmarks.csproj ./web-app/FormatBenchmarks/
RUN dotnet restore web-app/FormatBenchmarks/FormatBenchmarks.csproj

# Copy the rest of the web app code and publish
COPY web-app/ ./web-app/
RUN dotnet publish web-app/FormatBenchmarks/FormatBenchmarks.csproj \
    -c Release -o /app/publish --no-restore

# ---- Stage 2: Build Go benchmarks ----
FROM golang:1.26.0 AS build-go
WORKDIR /src

# Install schema compilers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        protobuf-compiler \
        capnproto \
        libcapnp-dev \
        flatbuffers-compiler && \
    rm -rf /var/lib/apt/lists/*

# Install Go code generation plugins
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install zombiezen.com/go/capnproto2/capnpc-go@latest

# Copy Go module files and download dependencies
COPY go-benchmarks/go.mod go-benchmarks/go.sum ./go-benchmarks/
WORKDIR /src/go-benchmarks
RUN go mod download

# Copy the rest of the Go code
COPY go-benchmarks/ ./

# Compile schemas
RUN mkdir -p schemas/protobuf schemas/capnp schemas/flatbuf && \
    protoc --proto_path=schemas --go_out=schemas/protobuf \
        --go_opt=paths=source_relative schemas/message.proto && \
    CAPNP_STD=$(find $(go env GOMODCACHE) -path '*/zombiezen.com/go/capnproto2@*/std' -type d | head -1) && \
    capnpc -I"$CAPNP_STD" -ogo:schemas/capnp schemas/message.capnp && \
    if [ -f schemas/capnp/schemas/message.capnp.go ]; then \
        mv schemas/capnp/schemas/message.capnp.go schemas/capnp/; \
        rm -rf schemas/capnp/schemas; \
    fi && \
    flatc --go -o schemas/ schemas/message.fbs && \
    if [ -d schemas/benchmarks ]; then \
        mv schemas/benchmarks/*.go schemas/flatbuf/ 2>/dev/null || true; \
        rmdir schemas/benchmarks 2>/dev/null || true; \
    fi && \
    for f in schemas/flatbuf/*.go; do \
        [ -f "$f" ] && sed -i 's/^package benchmarks$/package flatbuf/' "$f"; \
    done

# Build Go binary
RUN CGO_ENABLED=0 go build -o /app/benchmark .

# ---- Stage 3: Runtime image ----
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

# Install Python for benchmark execution
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        python3-venv \
        python3-pip \
        capnproto \
        libcapnp-dev \
        g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy Python benchmarks and set up venv
COPY python-benchmarks/ /app/python-benchmarks/
RUN mkdir -p /app/python-benchmarks/results && \
    python3 -m venv /app/python-benchmarks/.venv && \
    /app/python-benchmarks/.venv/bin/pip install --no-cache-dir \
        -r /app/python-benchmarks/requirements.txt && \
    /app/python-benchmarks/.venv/bin/python -c "import zstandard; print('zstandard OK')" && \
    /app/python-benchmarks/.venv/bin/python -c "import tracemalloc; print('tracemalloc OK')"

# Compile protobuf schema
RUN /app/python-benchmarks/.venv/bin/python /app/python-benchmarks/compile_schemas.py

# Copy Go benchmark binary and schema
COPY --from=build-go /app/benchmark /app/go-benchmarks/benchmark
COPY go-benchmarks/schemas/message.avsc /app/go-benchmarks/schemas/message.avsc
RUN mkdir -p /app/go-benchmarks/results

# Copy published .NET app
COPY --from=build-dotnet /app/publish .

# Configuration
ENV ASPNETCORE_URLS=http://+:5000
ENV Python__Path=/app/python-benchmarks/.venv/bin/python
ENV Python__ScriptPath=/app/python-benchmarks
ENV Go__BinaryPath=/app/go-benchmarks/benchmark

EXPOSE 5000

ENTRYPOINT ["dotnet", "FormatBenchmarks.dll"]

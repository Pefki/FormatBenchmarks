#!/bin/bash
set -e

#check if run as root and exit if not
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Install latest Go if not present or outdated
GO_VERSION="1.26.0"
if ! /usr/local/go/bin/go version 2>/dev/null | grep -q "go${GO_VERSION}"; then
    echo "Installing Go ${GO_VERSION}..."
    cd /tmp
    curl -sLO "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
    sudo rm -rf /usr/local/go
    sudo tar -C /usr/local -xzf "go${GO_VERSION}.linux-amd64.tar.gz"
fi

export PATH=/usr/local/go/bin:$HOME/go/bin:$PATH
export GOPATH=$HOME/go

echo "Go version: $(go version)"

# Install code gen plugins
echo "Installing protoc-gen-go..."
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
echo "  ✓ protoc-gen-go installed"
echo "Installing capnpc-go..."
go install zombiezen.com/go/capnproto2/capnpc-go@latest
echo "  ✓ capnpc-go installed"

echo "=== Go tools installed ==="


# Now compile schemas
cd /home/pefki/THLB/format-benchmarks/go-benchmarks

# Protobuf
echo ""
echo "Compiling Protobuf schema..."
mkdir -p schemas/protobuf
protoc \
    --proto_path=schemas \
    --go_out=schemas/protobuf \
    --go_opt=paths=source_relative \
    schemas/message.proto
echo "  ✓ Protobuf done"

# Cap'n Proto
echo "Compiling Cap'n Proto schema..."
mkdir -p schemas/capnp
# Find go.capnp in the Go module cache (it ships with capnproto2 under std/)
CAPNP_STD=$(find $(go env GOMODCACHE) -path '*/zombiezen.com/go/capnproto2@*/std' -type d 2>/dev/null | head -1)
if [ -z "$CAPNP_STD" ]; then
    echo "  ⚠ go.capnp not found in module cache. Run: go install zombiezen.com/go/capnproto2/capnpc-go@latest"
    exit 1
fi
echo "  Using capnp std imports from: $CAPNP_STD"
capnpc -I"$CAPNP_STD" -ogo:schemas/capnp schemas/message.capnp
# capnpc nests output under the schema's directory; move it up
if [ -f schemas/capnp/schemas/message.capnp.go ]; then
    mv schemas/capnp/schemas/message.capnp.go schemas/capnp/
    rm -rf schemas/capnp/schemas
fi
echo "  ✓ Cap'n Proto done"

# FlatBuffers
echo "Compiling FlatBuffers schema..."
mkdir -p schemas/flatbuf
flatc --go -o schemas/ schemas/message.fbs
# Move generated files from namespace dir to flatbuf
if [ -d schemas/benchmarks ]; then
    mv schemas/benchmarks/*.go schemas/flatbuf/ 2>/dev/null || true
    rmdir schemas/benchmarks 2>/dev/null || true
fi
# Fix package name
for f in schemas/flatbuf/*.go; do
    if [ -f "$f" ]; then
        sed -i 's/^package benchmarks$/package flatbuf/' "$f"
    fi
done
echo "  ✓ FlatBuffers done"

# Resolve dependencies
echo ""
echo "Running go mod tidy..."
go mod tidy
echo "  ✓ Dependencies resolved"

# Build Go binary
echo ""
echo "Building Go benchmark binary..."
go build -o benchmark .
echo "  ✓ Binary built: $(pwd)/benchmark"

echo ""
echo "=== All schemas compiled ==="
ls -la schemas/protobuf/ schemas/capnp/ schemas/flatbuf/

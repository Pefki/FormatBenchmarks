package benchmarks

import (
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"

	"example.com/benchmarks/models"
)

// RunResult holds the complete result set from a benchmark run.
type RunResult struct {
	Timestamp  string        `json:"timestamp"`
	SystemInfo GoSystemInfo  `json:"system_info"`
	Config     RunConfig     `json:"config"`
	Results    []BenchmarkResult `json:"results"`
}

// GoSystemInfo holds system information with correct JSON types.
type GoSystemInfo struct {
	Platform      string `json:"platform"`
	GoVersion     string `json:"go_version"`
	PythonVersion string `json:"python_version,omitempty"`
	Processor     string `json:"processor"`
	Machine       string `json:"machine"`
	CpuCount      int    `json:"cpu_count"`
	Language      string `json:"language"`
}

// RunConfig holds the configuration used for this benchmark run.
type RunConfig struct {
	Iterations     int      `json:"iterations"`
	Warmup         int      `json:"warmup"`
	Formats        []string `json:"formats"`
	PayloadSizes   []string `json:"payload_sizes"`
	SkippedFormats []string `json:"skipped_formats"`
}

// Runner orchestrates all format benchmarks.
type Runner struct {
	Iterations int
	Warmup     int
	Formats    []string
	benchmarks map[string]FormatBenchmark
}

// NewRunner creates a new benchmark runner with the given configuration.
func NewRunner(iterations, warmup int, formats []string) *Runner {
	r := &Runner{
		Iterations: iterations,
		Warmup:     warmup,
		Formats:    formats,
		benchmarks: make(map[string]FormatBenchmark),
	}
	r.loadBenchmarks()
	return r
}

func (r *Runner) loadBenchmarks() {
	// JSON - always available (stdlib)
	r.benchmarks["json"] = &JSONBenchmark{}

	// BSON
	r.benchmarks["bson"] = &BSONBenchmark{}

	// MessagePack
	r.benchmarks["msgpack"] = &MsgpackBenchmark{}

	// Protobuf
	r.benchmarks["protobuf"] = &ProtobufBenchmark{}

	// Cap'n Proto
	r.benchmarks["capnproto"] = &CapnProtoBenchmark{}

	// Apache Avro
	avro, err := NewAvroBenchmark()
	if err != nil {
		fmt.Fprintf(os.Stderr, "⚠  Avro not available: %v\n", err)
	} else {
		r.benchmarks["avro"] = avro
	}

	// FlatBuffers
	r.benchmarks["flatbuffers"] = &FlatBuffersBenchmark{}
}

// dataToMap converts a BenchmarkMessage struct to map[string]interface{} for generic benchmark use.
func dataToMap(msg models.BenchmarkMessage) map[string]interface{} {
	m := map[string]interface{}{
		"id":        msg.ID,
		"timestamp": msg.Timestamp,
		"username":  msg.Username,
		"email":     msg.Email,
		"content":   msg.Content,
		"tags":      msg.Tags,
		"metadata":  msg.Metadata,
		"score":     msg.Score,
		"is_active": msg.IsActive,
		"items":     itemsToSlice(msg.Items),
	}
	if msg.NestedData != nil {
		m["nested_data"] = map[string]interface{}{
			"field1": msg.NestedData.Field1,
			"field2": msg.NestedData.Field2,
			"values": msg.NestedData.Values,
		}
	}
	return m
}

func itemsToSlice(items []models.Item) []interface{} {
	result := make([]interface{}, len(items))
	for i, item := range items {
		result[i] = map[string]interface{}{
			"name":        item.Name,
			"value":       item.Value,
			"active":      item.Active,
			"description": item.Description,
			"tags":        item.Tags,
		}
	}
	return result
}

// RunAll executes all benchmarks for the given test data.
func (r *Runner) RunAll(testData map[string]models.BenchmarkMessage) *RunResult {
	var results []BenchmarkResult
	var skipped []string

	for _, formatKey := range r.Formats {
		bench, ok := r.benchmarks[formatKey]
		if !ok {
			fmt.Printf("\n⏭  %s skipped (not available)\n", formatKey)
			skipped = append(skipped, formatKey)
			continue
		}

		fmt.Printf("\n📊 Benchmarking %s...\n", bench.FormatName())

		for sizeLabel, data := range testData {
			fmt.Printf("   Payload size: %s... ", sizeLabel)
			dataMap := dataToMap(data)

			result, err := RunBenchmark(bench, dataMap, r.Iterations, r.Warmup)
			if err != nil {
				fmt.Printf("✗ error: %v\n", err)
				continue
			}
			result.PayloadSizeLabel = sizeLabel
			results = append(results, *result)
			fmt.Printf("✓ (%d bytes, %.4f ms avg)\n",
				result.SerializedSize, result.SerializeTime.Mean)
		}
	}

	sizes := make([]string, 0, len(testData))
	for k := range testData {
		sizes = append(sizes, k)
	}

	return &RunResult{
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
		SystemInfo: getSystemInfo(),
		Config: RunConfig{
			Iterations:     r.Iterations,
			Warmup:         r.Warmup,
			Formats:        r.Formats,
			PayloadSizes:   sizes,
			SkippedFormats: skipped,
		},
		Results: results,
	}
}

func getSystemInfo() GoSystemInfo {
	info := GoSystemInfo{
		Platform:  runtime.GOOS + "/" + runtime.GOARCH,
		GoVersion: runtime.Version(),
		Machine:   runtime.GOARCH,
		CpuCount:  runtime.NumCPU(),
		Language:  "go",
		Processor: "unknown",
	}

	// Try to read CPU name from /proc/cpuinfo (Linux/WSL)
	data, err := os.ReadFile("/proc/cpuinfo")
	if err == nil {
		for _, line := range strings.Split(string(data), "\n") {
			if strings.HasPrefix(line, "model name") {
				parts := strings.SplitN(line, ":", 2)
				if len(parts) == 2 {
					info.Processor = strings.TrimSpace(parts[1])
					break
				}
			}
		}
	}

	return info
}

// Message Format Benchmark Suite (Go)
// ====================================
// Benchmarks different binary message formats on serialization performance,
// payload size, and round-trip time.
//
// Supported formats: JSON, BSON, Protobuf, Cap'n Proto, MessagePack, Apache Avro, FlatBuffers
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"example.com/benchmarks/benchmarks"
	"example.com/benchmarks/models"
)

func main() {
	iterations := flag.Int("iterations", 1000, "Number of iterations per benchmark (default: 1000)")
	warmup := flag.Int("warmup", 100, "Number of warmup iterations (default: 100)")
	formatsStr := flag.String("formats", "json,bson,protobuf,capnproto,msgpack,avro,flatbuffers",
		"Comma-separated list of formats to benchmark")
	sizesStr := flag.String("sizes", "small,medium,large",
		"Comma-separated payload sizes to test (small, medium, large)")
	output := flag.String("output", "results/benchmark_results.json",
		"Output file path")
	nestingDepth := flag.Int("nesting-depth", 0,
		"Target payload nesting depth (applies to generated test data)")

	flag.Parse()

	formats := strings.Split(*formatsStr, ",")
	sizes := strings.Split(*sizesStr, ",")

	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("  Message Format Benchmark Suite (Go)")
	fmt.Println(strings.Repeat("=", 60))
	fmt.Printf("  Iterations:  %d\n", *iterations)
	fmt.Printf("  Warmup:      %d\n", *warmup)
	fmt.Printf("  Formats:     %s\n", strings.Join(formats, ", "))
	fmt.Printf("  Sizes:       %s\n", strings.Join(sizes, ", "))
	if *nestingDepth > 0 {
		fmt.Printf("  Nesting:     %d\n", *nestingDepth)
	}
	fmt.Printf("  Output:      %s\n", *output)
	fmt.Println(strings.Repeat("=", 60))

	// Generate test data for each size
	testData := make(map[string]models.BenchmarkMessage)
	for _, size := range sizes {
		testData[size] = models.GenerateTestDataWithNesting(size, *nestingDepth)
		fmt.Printf("  Test data '%s' generated\n", size)
	}

	// Run benchmarks
	runner := benchmarks.NewRunner(*iterations, *warmup, *nestingDepth, formats)
	results := runner.RunAll(testData)

	// Ensure output directory exists
	if dir := filepath.Dir(*output); dir != "" {
		os.MkdirAll(dir, 0755)
	}

	// Write results to file
	jsonData, err := json.MarshalIndent(results, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling results: %v\n", err)
		os.Exit(1)
	}

	if err := os.WriteFile(*output, jsonData, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing results: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("\n%s\n", strings.Repeat("=", 60))
	fmt.Printf("  Results written to: %s\n", *output)
	fmt.Printf("  Total benchmarks: %d\n", len(results.Results))
	fmt.Printf("%s\n", strings.Repeat("=", 60))
}

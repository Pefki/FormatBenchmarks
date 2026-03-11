// Package benchmarks provides the benchmark interface and runner
// for comparing message format serialization performance.
package benchmarks

import (
	"compress/gzip"
	"bytes"
	"math"
	"runtime"
	"sort"
	"time"
)

// FormatBenchmark is the interface that all message format benchmarks must implement.
type FormatBenchmark interface {
	// FormatName returns the human-readable name of the format.
	FormatName() string
	// Serialize converts a data map to bytes.
	Serialize(data map[string]interface{}) ([]byte, error)
	// Deserialize converts bytes back to a data map.
	Deserialize(payload []byte) (map[string]interface{}, error)
}

// TimingStats holds statistical metrics for a series of timing measurements.
type TimingStats struct {
	Mean   float64 `json:"mean"`
	Median float64 `json:"median"`
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
	StdDev float64 `json:"std_dev"`
	P95    float64 `json:"p95"`
	P99    float64 `json:"p99"`
}

// MemoryUsage holds memory usage statistics.
type MemoryUsage struct {
	SerializePeakBytes   uint64 `json:"serialize_peak_bytes"`
	DeserializePeakBytes uint64 `json:"deserialize_peak_bytes"`
	TotalPeakBytes       uint64 `json:"total_peak_bytes"`
}

// CompressionStats holds compression ratio measurements.
type CompressionStats struct {
	OriginalBytes int     `json:"original_bytes"`
	GzipBytes     int     `json:"gzip_bytes"`
	GzipRatio     float64 `json:"gzip_ratio"`
}

// ThroughputStats holds throughput metrics.
type ThroughputStats struct {
	SerializeMsgPerSec   float64 `json:"serialize_msg_per_sec"`
	DeserializeMsgPerSec float64 `json:"deserialize_msg_per_sec"`
	SerializeMBPerSec    float64 `json:"serialize_mb_per_sec"`
	DeserializeMBPerSec  float64 `json:"deserialize_mb_per_sec"`
}

// BenchmarkResult holds the full result of a single format+size benchmark run.
type BenchmarkResult struct {
	Format            string            `json:"format"`
	Iterations        int               `json:"iterations"`
	SerializedSize    int               `json:"serialized_size_bytes"`
	PayloadNestingDepth int             `json:"payload_nesting_depth"`
	SerializeTime     TimingStats       `json:"serialize_time_ms"`
	DeserializeTime   TimingStats       `json:"deserialize_time_ms"`
	RoundTripTime     TimingStats       `json:"round_trip_time_ms"`
	MemoryUsage       *MemoryUsage      `json:"memory_usage,omitempty"`
	Compression       *CompressionStats `json:"compression,omitempty"`
	Throughput        *ThroughputStats  `json:"throughput,omitempty"`
	PayloadSizeLabel  string            `json:"payload_size_label"`
}

// RunBenchmark executes the full benchmark suite for a single format.
func RunBenchmark(b FormatBenchmark, data map[string]interface{}, iterations, warmup int) (*BenchmarkResult, error) {
	// Warmup phase
	for i := 0; i < warmup; i++ {
		serialized, err := b.Serialize(data)
		if err != nil {
			return nil, err
		}
		_, err = b.Deserialize(serialized)
		if err != nil {
			return nil, err
		}
	}

	// Measure serialization
	serializeTimes := make([]float64, iterations)
	var serialized []byte
	for i := 0; i < iterations; i++ {
		start := time.Now()
		s, err := b.Serialize(data)
		elapsed := time.Since(start)
		if err != nil {
			return nil, err
		}
		serialized = s
		serializeTimes[i] = float64(elapsed.Nanoseconds()) / 1_000_000 // to ms
	}

	payloadSize := len(serialized)

	// Measure deserialization
	deserializeTimes := make([]float64, iterations)
	for i := 0; i < iterations; i++ {
		start := time.Now()
		_, err := b.Deserialize(serialized)
		elapsed := time.Since(start)
		if err != nil {
			return nil, err
		}
		deserializeTimes[i] = float64(elapsed.Nanoseconds()) / 1_000_000
	}

	// Calculate round-trip times
	roundTripTimes := make([]float64, iterations)
	for i := range roundTripTimes {
		roundTripTimes[i] = serializeTimes[i] + deserializeTimes[i]
	}

	// Memory usage
	memUsage := measureMemory(b, data, serialized)

	// Compression
	compression := measureCompression(serialized)

	// Throughput
	serMean := mean(serializeTimes)
	deserMean := mean(deserializeTimes)
	throughput := calculateThroughput(serMean, deserMean, payloadSize)

	return &BenchmarkResult{
		Format:          b.FormatName(),
		Iterations:      iterations,
		SerializedSize:  payloadSize,
		PayloadNestingDepth: calculateNestingDepth(data),
		SerializeTime:   calculateStats(serializeTimes),
		DeserializeTime: calculateStats(deserializeTimes),
		RoundTripTime:   calculateStats(roundTripTimes),
		MemoryUsage:     memUsage,
		Compression:     compression,
		Throughput:      throughput,
	}, nil
}

// calculateNestingDepth returns the maximum container nesting depth for a value.
// Scalars have depth 0, while maps/slices add one level plus the deepest child.
func calculateNestingDepth(value interface{}) int {
	switch v := value.(type) {
	case map[string]interface{}:
		maxChild := 0
		for _, child := range v {
			depth := calculateNestingDepth(child)
			if depth > maxChild {
				maxChild = depth
			}
		}
		return 1 + maxChild
	case []interface{}:
		maxChild := 0
		for _, child := range v {
			depth := calculateNestingDepth(child)
			if depth > maxChild {
				maxChild = depth
			}
		}
		return 1 + maxChild
	default:
		return 0
	}
}

// measureMemory measures peak memory allocation during serialization/deserialization.
func measureMemory(b FormatBenchmark, data map[string]interface{}, serialized []byte) *MemoryUsage {
	runtime.GC()

	var m1, m2 runtime.MemStats

	// Measure serialization memory
	runtime.GC()
	runtime.ReadMemStats(&m1)
	for i := 0; i < 10; i++ {
		b.Serialize(data)
	}
	runtime.ReadMemStats(&m2)
	serPeak := m2.TotalAlloc - m1.TotalAlloc

	// Measure deserialization memory
	runtime.GC()
	runtime.ReadMemStats(&m1)
	for i := 0; i < 10; i++ {
		b.Deserialize(serialized)
	}
	runtime.ReadMemStats(&m2)
	deserPeak := m2.TotalAlloc - m1.TotalAlloc

	// Measure round-trip memory
	runtime.GC()
	runtime.ReadMemStats(&m1)
	for i := 0; i < 10; i++ {
		s, _ := b.Serialize(data)
		b.Deserialize(s)
	}
	runtime.ReadMemStats(&m2)
	totalPeak := m2.TotalAlloc - m1.TotalAlloc

	return &MemoryUsage{
		SerializePeakBytes:   serPeak,
		DeserializePeakBytes: deserPeak,
		TotalPeakBytes:       totalPeak,
	}
}

// measureCompression measures gzip compression ratio.
func measureCompression(serialized []byte) *CompressionStats {
	original := len(serialized)

	var buf bytes.Buffer
	w, _ := gzip.NewWriterLevel(&buf, gzip.DefaultCompression)
	w.Write(serialized)
	w.Close()
	gzipSize := buf.Len()

	ratio := float64(gzipSize) / float64(original)
	if original == 0 {
		ratio = 1.0
	}

	return &CompressionStats{
		OriginalBytes: original,
		GzipBytes:     gzipSize,
		GzipRatio:     math.Round(ratio*10000) / 10000,
	}
}

// calculateThroughput computes messages/sec and MB/sec metrics.
func calculateThroughput(serMeanMs, deserMeanMs float64, payloadSize int) *ThroughputStats {
	var serMPS, deserMPS float64
	if serMeanMs > 0 {
		serMPS = math.Round(1000.0/serMeanMs*100) / 100
	}
	if deserMeanMs > 0 {
		deserMPS = math.Round(1000.0/deserMeanMs*100) / 100
	}

	mb := float64(payloadSize) / (1024 * 1024)
	var serMBPS, deserMBPS float64
	if serMPS > 0 {
		serMBPS = math.Round(mb*serMPS*10000) / 10000
	}
	if deserMPS > 0 {
		deserMBPS = math.Round(mb*deserMPS*10000) / 10000
	}

	return &ThroughputStats{
		SerializeMsgPerSec:   serMPS,
		DeserializeMsgPerSec: deserMPS,
		SerializeMBPerSec:    serMBPS,
		DeserializeMBPerSec:  deserMBPS,
	}
}

// calculateStats computes statistical metrics for a list of timing measurements.
func calculateStats(times []float64) TimingStats {
	n := len(times)
	if n == 0 {
		return TimingStats{}
	}

	sorted := make([]float64, n)
	copy(sorted, times)
	sort.Float64s(sorted)

	m := mean(times)
	med := median(sorted)
	mn := sorted[0]
	mx := sorted[n-1]
	sd := stddev(times, m)

	p95Idx := int(float64(n) * 0.95)
	p99Idx := int(float64(n) * 0.99)
	if p95Idx >= n {
		p95Idx = n - 1
	}
	if p99Idx >= n {
		p99Idx = n - 1
	}

	return TimingStats{
		Mean:   round6(m),
		Median: round6(med),
		Min:    round6(mn),
		Max:    round6(mx),
		StdDev: round6(sd),
		P95:    round6(sorted[p95Idx]),
		P99:    round6(sorted[p99Idx]),
	}
}

func mean(data []float64) float64 {
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func median(sorted []float64) float64 {
	n := len(sorted)
	if n%2 == 0 {
		return (sorted[n/2-1] + sorted[n/2]) / 2
	}
	return sorted[n/2]
}

func stddev(data []float64, m float64) float64 {
	if len(data) <= 1 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		d := v - m
		sum += d * d
	}
	return math.Sqrt(sum / float64(len(data)-1))
}

func round6(v float64) float64 {
	return math.Round(v*1_000_000) / 1_000_000
}

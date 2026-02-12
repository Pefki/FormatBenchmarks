// Package models provides test data generation for benchmarking.
package models

import (
	"math/rand"
)

const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

// randomString generates a random string of the given length using a fixed seed RNG.
func randomString(rng *rand.Rand, length int) string {
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[rng.Intn(len(charset))]
	}
	return string(b)
}

// GenerateTestData generates test data for the given size category.
// Sizes: "small", "medium", "large".
// Uses a fixed seed (42) for reproducible results matching the Python suite.
func GenerateTestData(size string) BenchmarkMessage {
	rng := rand.New(rand.NewSource(42))

	switch size {
	case "small":
		return generateSmall()
	case "medium":
		return generateMedium(rng)
	case "large":
		return generateLarge(rng)
	default:
		panic("unknown size: " + size + " (use small, medium, large)")
	}
}

// generateSmall creates a small payload (~200-500 bytes).
func generateSmall() BenchmarkMessage {
	return BenchmarkMessage{
		ID:        1,
		Timestamp: "2026-02-10T12:00:00Z",
		Username:  "testuser",
		Email:     "test@example.com",
		Content:   "Hello, this is a small test message for benchmark purposes.",
		Tags:      []string{"test", "small", "benchmark"},
		Metadata:  map[string]string{"source": "benchmark", "version": "1.0"},
		Score:     95.5,
		IsActive:  true,
		Items:     []Item{},
	}
}

// generateMedium creates a medium payload (~2-5 KB).
func generateMedium(rng *rand.Rand) BenchmarkMessage {
	tags := make([]string, 20)
	for i := range tags {
		tags[i] = randomString(rng, 10)
	}

	metadata := make(map[string]string, 15)
	for i := 0; i < 15; i++ {
		metadata[randomString(rng, 8)] = randomString(rng, 20)
	}

	values := make([]float64, 50)
	for i := range values {
		values[i] = rng.Float64() * 100
	}

	items := make([]Item, 10)
	for i := range items {
		items[i] = Item{
			Name:        randomString(rng, 20),
			Value:       rng.Float64() * 1000,
			Active:      rng.Intn(2) == 1,
			Description: "",
			Tags:        []string{},
		}
	}

	return BenchmarkMessage{
		ID:        42,
		Timestamp: "2026-02-10T12:00:00Z",
		Username:  "benchmark_user_medium",
		Email:     "benchmark.medium@example.com",
		Content:   randomString(rng, 1000),
		Tags:      tags,
		Metadata:  metadata,
		Score:     87.123456,
		IsActive:  true,
		NestedData: &NestedData{
			Field1: randomString(rng, 100),
			Field2: 12345,
			Values: values,
		},
		Items: items,
	}
}

// generateLarge creates a large payload (~20-50 KB).
func generateLarge(rng *rand.Rand) BenchmarkMessage {
	tags := make([]string, 100)
	for i := range tags {
		tags[i] = randomString(rng, 15)
	}

	metadata := make(map[string]string, 50)
	for i := 0; i < 50; i++ {
		metadata[randomString(rng, 12)] = randomString(rng, 50)
	}

	values := make([]float64, 500)
	for i := range values {
		values[i] = rng.Float64() * 1000
	}

	items := make([]Item, 100)
	for i := range items {
		itemTags := make([]string, 5)
		for j := range itemTags {
			itemTags[j] = randomString(rng, 8)
		}
		items[i] = Item{
			Name:        randomString(rng, 30),
			Value:       rng.Float64() * 10000,
			Active:      rng.Intn(2) == 1,
			Description: randomString(rng, 200),
			Tags:        itemTags,
		}
	}

	return BenchmarkMessage{
		ID:        99999,
		Timestamp: "2026-02-10T12:00:00Z",
		Username:  "benchmark_user_large_payload_test",
		Email:     "benchmark.large.payload@example.com",
		Content:   randomString(rng, 10000),
		Tags:      tags,
		Metadata:  metadata,
		Score:     99.999999,
		IsActive:  true,
		NestedData: &NestedData{
			Field1: randomString(rng, 500),
			Field2: 9999999,
			Values: values,
		},
		Items: items,
	}
}

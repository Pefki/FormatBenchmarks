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
	return GenerateTestDataWithNesting(size, 0)
}

// GenerateTestDataWithNesting generates test data and applies a target nesting depth when provided.
// Depths above 4 are clamped because the Go message schema has a maximum structural depth of 4.
func GenerateTestDataWithNesting(size string, nestingDepth int) BenchmarkMessage {
	rng := rand.New(rand.NewSource(42))

	var msg BenchmarkMessage
	switch size {
	case "small":
		msg = generateSmall()
	case "medium":
		msg = generateMedium(rng)
	case "large":
		msg = generateLarge(rng)
	default:
		panic("unknown size: " + size + " (use small, medium, large)")
	}

	if nestingDepth <= 0 {
		return msg
	}

	return applyNestingDepth(msg, nestingDepth)
}

func applyNestingDepth(msg BenchmarkMessage, nestingDepth int) BenchmarkMessage {
	if nestingDepth < 1 {
		nestingDepth = 1
	}
	if nestingDepth > 4 {
		nestingDepth = 4
	}

	switch nestingDepth {
	case 1:
		msg.Tags = nil
		msg.Metadata = nil
		msg.NestedData = nil
		msg.Items = nil
	case 2:
		if len(msg.Tags) == 0 {
			msg.Tags = []string{"tag"}
		}
		if len(msg.Metadata) == 0 {
			msg.Metadata = map[string]string{"source": "benchmark"}
		}
		msg.NestedData = nil
		msg.Items = nil
	case 3:
		if msg.NestedData == nil {
			msg.NestedData = &NestedData{Field1: "leaf", Field2: 1, Values: []float64{1.0}}
		}
		if len(msg.NestedData.Values) == 0 {
			msg.NestedData.Values = []float64{1.0}
		}
		msg.Items = nil
	default:
		if msg.NestedData == nil {
			msg.NestedData = &NestedData{Field1: "leaf", Field2: 1, Values: []float64{1.0}}
		}
		if len(msg.Items) == 0 {
			msg.Items = []Item{{Name: "item", Value: 1.0, Active: true, Description: "", Tags: []string{"t"}}}
		}
		if len(msg.Items[0].Tags) == 0 {
			msg.Items[0].Tags = []string{"t"}
		}
	}

	return msg
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

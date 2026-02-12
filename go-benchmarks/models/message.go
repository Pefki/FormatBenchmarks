// Package models defines the data structures used for benchmarking
// message format serialization/deserialization.
package models

// BenchmarkMessage is the main benchmark message structure containing
// diverse data types for testing serialization performance.
type BenchmarkMessage struct {
	ID         int64             `json:"id" bson:"id" msgpack:"id" avro:"id"`
	Timestamp  string            `json:"timestamp" bson:"timestamp" msgpack:"timestamp" avro:"timestamp"`
	Username   string            `json:"username" bson:"username" msgpack:"username" avro:"username"`
	Email      string            `json:"email" bson:"email" msgpack:"email" avro:"email"`
	Content    string            `json:"content" bson:"content" msgpack:"content" avro:"content"`
	Tags       []string          `json:"tags" bson:"tags" msgpack:"tags" avro:"tags"`
	Metadata   map[string]string `json:"metadata" bson:"metadata" msgpack:"metadata" avro:"metadata"`
	Score      float64           `json:"score" bson:"score" msgpack:"score" avro:"score"`
	IsActive   bool              `json:"is_active" bson:"is_active" msgpack:"is_active" avro:"is_active"`
	NestedData *NestedData       `json:"nested_data,omitempty" bson:"nested_data,omitempty" msgpack:"nested_data,omitempty" avro:"nested_data"`
	Items      []Item            `json:"items" bson:"items" msgpack:"items" avro:"items"`
}

// NestedData is a nested data object with mixed types.
type NestedData struct {
	Field1 string    `json:"field1" bson:"field1" msgpack:"field1" avro:"field1"`
	Field2 int64     `json:"field2" bson:"field2" msgpack:"field2" avro:"field2"`
	Values []float64 `json:"values" bson:"values" msgpack:"values" avro:"values"`
}

// Item represents an element in a list with multiple fields.
type Item struct {
	Name        string   `json:"name" bson:"name" msgpack:"name" avro:"name"`
	Value       float64  `json:"value" bson:"value" msgpack:"value" avro:"value"`
	Active      bool     `json:"active" bson:"active" msgpack:"active" avro:"active"`
	Description string   `json:"description" bson:"description" msgpack:"description" avro:"description"`
	Tags        []string `json:"tags" bson:"tags" msgpack:"tags" avro:"tags"`
}

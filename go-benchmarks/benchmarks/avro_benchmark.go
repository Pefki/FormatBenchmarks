package benchmarks

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"

	"github.com/hamba/avro/v2"
)

// AvroBenchmark benchmarks Apache Avro, a schema-based binary format.
// Avro is popular in data engineering and event streaming (Kafka).
type AvroBenchmark struct {
	schema avro.Schema
}

// NewAvroBenchmark creates a new Avro benchmark by loading the .avsc schema.
func NewAvroBenchmark() (*AvroBenchmark, error) {
	// Try to find schema: first relative to working directory, then relative to source file
	candidates := []string{
		filepath.Join("schemas", "message.avsc"),
	}
	_, filename, _, ok := runtime.Caller(0)
	if ok {
		candidates = append(candidates,
			filepath.Join(filepath.Dir(filename), "..", "schemas", "message.avsc"))
	}

	var data []byte
	var readErr error
	for _, path := range candidates {
		data, readErr = os.ReadFile(path)
		if readErr == nil {
			break
		}
	}
	if readErr != nil {
		return nil, fmt.Errorf("could not read Avro schema: %w", readErr)
	}

	// Parse the JSON schema string
	var schemaJSON interface{}
	if err := json.Unmarshal(data, &schemaJSON); err != nil {
		return nil, fmt.Errorf("invalid Avro schema JSON: %w", err)
	}

	schema, err := avro.Parse(string(data))
	if err != nil {
		return nil, fmt.Errorf("could not parse Avro schema: %w", err)
	}

	return &AvroBenchmark{schema: schema}, nil
}

func (b *AvroBenchmark) FormatName() string {
	return "Apache Avro"
}

// avroMessage is a struct matching the Avro schema for efficient serialization.
type avroMessage struct {
	ID         int64             `avro:"id"`
	Timestamp  string            `avro:"timestamp"`
	Username   string            `avro:"username"`
	Email      string            `avro:"email"`
	Content    string            `avro:"content"`
	Tags       []string          `avro:"tags"`
	Metadata   map[string]string `avro:"metadata"`
	Score      float64           `avro:"score"`
	IsActive   bool              `avro:"is_active"`
	NestedData *avroNestedData   `avro:"nested_data"`
	Items      []avroItem        `avro:"items"`
}

type avroNestedData struct {
	Field1 string    `avro:"field1"`
	Field2 int64     `avro:"field2"`
	Values []float64 `avro:"values"`
}

type avroItem struct {
	Name        string   `avro:"name"`
	Value       float64  `avro:"value"`
	Active      bool     `avro:"active"`
	Description *string  `avro:"description"`
	Tags        []string `avro:"tags"`
}

func (b *AvroBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	msg := mapToAvro(data)
	return avro.Marshal(b.schema, msg)
}

func (b *AvroBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	var msg avroMessage
	if err := avro.Unmarshal(b.schema, payload, &msg); err != nil {
		return nil, err
	}
	return avroToMap(&msg), nil
}

func mapToAvro(data map[string]interface{}) avroMessage {
	msg := avroMessage{
		Tags:     []string{},
		Metadata: map[string]string{},
		Items:    []avroItem{},
	}

	if v, ok := data["id"]; ok {
		msg.ID = toInt64(v)
	}
	if v, ok := data["timestamp"].(string); ok {
		msg.Timestamp = v
	}
	if v, ok := data["username"].(string); ok {
		msg.Username = v
	}
	if v, ok := data["email"].(string); ok {
		msg.Email = v
	}
	if v, ok := data["content"].(string); ok {
		msg.Content = v
	}
	if v, ok := data["score"]; ok {
		msg.Score = toFloat64(v)
	}
	if v, ok := data["is_active"].(bool); ok {
		msg.IsActive = v
	}
	if tags, ok := data["tags"].([]string); ok {
		msg.Tags = tags
	}
	if meta, ok := data["metadata"].(map[string]string); ok {
		msg.Metadata = meta
	}

	if nd, ok := data["nested_data"].(map[string]interface{}); ok {
		nestedData := &avroNestedData{
			Values: []float64{},
		}
		if v, ok := nd["field1"].(string); ok {
			nestedData.Field1 = v
		}
		if v, ok := nd["field2"]; ok {
			nestedData.Field2 = toInt64(v)
		}
		if vals, ok := nd["values"].([]float64); ok {
			nestedData.Values = vals
		}
		msg.NestedData = nestedData
	}

	if items, ok := data["items"].([]interface{}); ok {
		msg.Items = make([]avroItem, len(items))
		for i, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				ai := avroItem{
					Tags: []string{},
				}
				if v, ok := itemMap["name"].(string); ok {
					ai.Name = v
				}
				if v, ok := itemMap["value"]; ok {
					ai.Value = toFloat64(v)
				}
				if v, ok := itemMap["active"].(bool); ok {
					ai.Active = v
				}
				if v, ok := itemMap["description"].(string); ok {
					if v != "" {
						ai.Description = &v
					}
				}
				if tags, ok := itemMap["tags"].([]string); ok {
					ai.Tags = tags
				}
				msg.Items[i] = ai
			}
		}
	}

	return msg
}

func avroToMap(msg *avroMessage) map[string]interface{} {
	result := map[string]interface{}{
		"id":        msg.ID,
		"timestamp": msg.Timestamp,
		"username":  msg.Username,
		"email":     msg.Email,
		"content":   msg.Content,
		"tags":      msg.Tags,
		"metadata":  msg.Metadata,
		"score":     msg.Score,
		"is_active": msg.IsActive,
	}

	if msg.NestedData != nil {
		result["nested_data"] = map[string]interface{}{
			"field1": msg.NestedData.Field1,
			"field2": msg.NestedData.Field2,
			"values": msg.NestedData.Values,
		}
	}

	items := make([]interface{}, len(msg.Items))
	for i, item := range msg.Items {
		desc := ""
		if item.Description != nil {
			desc = *item.Description
		}
		items[i] = map[string]interface{}{
			"name":        item.Name,
			"value":       item.Value,
			"active":      item.Active,
			"description": desc,
			"tags":        item.Tags,
		}
	}
	result["items"] = items

	return result
}

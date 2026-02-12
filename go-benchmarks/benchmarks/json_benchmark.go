package benchmarks

import (
	"encoding/json"
)

// JSONBenchmark benchmarks the standard JSON format.
type JSONBenchmark struct{}

func (b *JSONBenchmark) FormatName() string {
	return "JSON"
}

func (b *JSONBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	return json.Marshal(data)
}

func (b *JSONBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := json.Unmarshal(payload, &result)
	return result, err
}

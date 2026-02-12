package benchmarks

import (
	"go.mongodb.org/mongo-driver/bson"
)

// BSONBenchmark benchmarks the BSON (Binary JSON) format.
// BSON is the binary format used internally by MongoDB.
type BSONBenchmark struct{}

func (b *BSONBenchmark) FormatName() string {
	return "BSON"
}

func (b *BSONBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	return bson.Marshal(data)
}

func (b *BSONBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := bson.Unmarshal(payload, &result)
	return result, err
}

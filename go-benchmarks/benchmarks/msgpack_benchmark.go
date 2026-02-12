package benchmarks

import (
	"github.com/vmihailenco/msgpack/v5"
)

// MsgpackBenchmark benchmarks the MessagePack format.
// MessagePack is "like JSON but fast and small" — a schema-less
// binary format that can directly serialize Go maps.
type MsgpackBenchmark struct{}

func (b *MsgpackBenchmark) FormatName() string {
	return "MessagePack"
}

func (b *MsgpackBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	return msgpack.Marshal(data)
}

func (b *MsgpackBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := msgpack.Unmarshal(payload, &result)
	return result, err
}

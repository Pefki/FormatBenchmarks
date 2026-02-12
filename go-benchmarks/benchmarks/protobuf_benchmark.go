package benchmarks

import (
	"google.golang.org/protobuf/proto"

	pb "example.com/benchmarks/schemas/protobuf"
)

// ProtobufBenchmark benchmarks Google Protocol Buffers.
// Protobuf is a schema-based binary format with strong typing
// and compact wire-format encoding.
type ProtobufBenchmark struct{}

func (b *ProtobufBenchmark) FormatName() string {
	return "Protobuf"
}

func (b *ProtobufBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	msg := mapToProto(data)
	return proto.Marshal(msg)
}

func (b *ProtobufBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	msg := &pb.BenchmarkMessage{}
	if err := proto.Unmarshal(payload, msg); err != nil {
		return nil, err
	}
	return protoToMap(msg), nil
}

// mapToProto converts a generic map to a protobuf BenchmarkMessage.
func mapToProto(data map[string]interface{}) *pb.BenchmarkMessage {
	msg := &pb.BenchmarkMessage{}

	if v, ok := data["id"]; ok {
		msg.Id = toInt64(v)
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

	// Tags
	if tags, ok := data["tags"].([]string); ok {
		msg.Tags = tags
	}

	// Metadata
	if meta, ok := data["metadata"].(map[string]string); ok {
		msg.Metadata = meta
	}

	// Nested data
	if nd, ok := data["nested_data"].(map[string]interface{}); ok {
		msg.NestedData = &pb.NestedData{}
		if v, ok := nd["field1"].(string); ok {
			msg.NestedData.Field1 = v
		}
		if v, ok := nd["field2"]; ok {
			msg.NestedData.Field2 = toInt64(v)
		}
		if vals, ok := nd["values"].([]float64); ok {
			msg.NestedData.Values = vals
		}
	}

	// Items
	if items, ok := data["items"].([]interface{}); ok {
		msg.Items = make([]*pb.Item, len(items))
		for i, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				pbItem := &pb.Item{}
				if v, ok := itemMap["name"].(string); ok {
					pbItem.Name = v
				}
				if v, ok := itemMap["value"]; ok {
					pbItem.Value = toFloat64(v)
				}
				if v, ok := itemMap["active"].(bool); ok {
					pbItem.Active = v
				}
				if v, ok := itemMap["description"].(string); ok {
					pbItem.Description = v
				}
				if tags, ok := itemMap["tags"].([]string); ok {
					pbItem.Tags = tags
				}
				msg.Items[i] = pbItem
			}
		}
	}

	return msg
}

// protoToMap converts a protobuf message back to a generic map.
func protoToMap(msg *pb.BenchmarkMessage) map[string]interface{} {
	result := map[string]interface{}{
		"id":        msg.Id,
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

	if msg.Items != nil {
		items := make([]interface{}, len(msg.Items))
		for i, item := range msg.Items {
			items[i] = map[string]interface{}{
				"name":        item.Name,
				"value":       item.Value,
				"active":      item.Active,
				"description": item.Description,
				"tags":        item.Tags,
			}
		}
		result["items"] = items
	}

	return result
}

func toInt64(v interface{}) int64 {
	switch val := v.(type) {
	case int64:
		return val
	case int:
		return int64(val)
	case float64:
		return int64(val)
	default:
		return 0
	}
}

func toFloat64(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case int64:
		return float64(val)
	case int:
		return float64(val)
	default:
		return 0
	}
}

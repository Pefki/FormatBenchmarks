package benchmarks

import (
	flatbuffers "github.com/google/flatbuffers/go"

	fb "example.com/benchmarks/schemas/flatbuf"
)

// FlatBuffersBenchmark benchmarks Google FlatBuffers, a zero-copy serialization format.
// Data can be read directly without a full deserialization step.
type FlatBuffersBenchmark struct{}

func (b *FlatBuffersBenchmark) FormatName() string {
	return "FlatBuffers"
}

func (b *FlatBuffersBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	builder := flatbuffers.NewBuilder(4096)

	// Strings must be created before building tables (bottom-up)
	timestampOff := builder.CreateString(getStr(data, "timestamp"))
	usernameOff := builder.CreateString(getStr(data, "username"))
	emailOff := builder.CreateString(getStr(data, "email"))
	contentOff := builder.CreateString(getStr(data, "content"))

	// Tags
	var tagsOff flatbuffers.UOffsetT
	if tags, ok := data["tags"].([]string); ok && len(tags) > 0 {
		tagOffsets := make([]flatbuffers.UOffsetT, len(tags))
		for i, t := range tags {
			tagOffsets[i] = builder.CreateString(t)
		}
		fb.BenchmarkMessageStartTagsVector(builder, len(tags))
		for i := len(tagOffsets) - 1; i >= 0; i-- {
			builder.PrependUOffsetT(tagOffsets[i])
		}
		tagsOff = builder.EndVector(len(tags))
	}

	// Metadata (as KeyValue vector)
	var metadataOff flatbuffers.UOffsetT
	if meta, ok := data["metadata"].(map[string]string); ok && len(meta) > 0 {
		kvOffsets := make([]flatbuffers.UOffsetT, 0, len(meta))
		for k, v := range meta {
			keyOff := builder.CreateString(k)
			valOff := builder.CreateString(v)
			fb.KeyValueStart(builder)
			fb.KeyValueAddKey(builder, keyOff)
			fb.KeyValueAddValue(builder, valOff)
			kvOffsets = append(kvOffsets, fb.KeyValueEnd(builder))
		}
		fb.BenchmarkMessageStartMetadataVector(builder, len(kvOffsets))
		for i := len(kvOffsets) - 1; i >= 0; i-- {
			builder.PrependUOffsetT(kvOffsets[i])
		}
		metadataOff = builder.EndVector(len(kvOffsets))
	}

	// Nested data
	var nestedDataOff flatbuffers.UOffsetT
	if nd, ok := data["nested_data"].(map[string]interface{}); ok {
		field1Off := builder.CreateString(getStr(nd, "field1"))

		var valuesOff flatbuffers.UOffsetT
		if vals, ok := nd["values"].([]float64); ok && len(vals) > 0 {
			fb.NestedDataStartValuesVector(builder, len(vals))
			for i := len(vals) - 1; i >= 0; i-- {
				builder.PrependFloat64(vals[i])
			}
			valuesOff = builder.EndVector(len(vals))
		}

		fb.NestedDataStart(builder)
		fb.NestedDataAddField1(builder, field1Off)
		fb.NestedDataAddField2(builder, toInt64(nd["field2"]))
		if valuesOff != 0 {
			fb.NestedDataAddValues(builder, valuesOff)
		}
		nestedDataOff = fb.NestedDataEnd(builder)
	}

	// Items
	var itemsOff flatbuffers.UOffsetT
	if items, ok := data["items"].([]interface{}); ok && len(items) > 0 {
		itemOffsets := make([]flatbuffers.UOffsetT, len(items))
		for i, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				nameOff := builder.CreateString(getStr(itemMap, "name"))
				descOff := builder.CreateString(getStr(itemMap, "description"))

				var itemTagsOff flatbuffers.UOffsetT
				if tags, ok := itemMap["tags"].([]string); ok && len(tags) > 0 {
					tagOffs := make([]flatbuffers.UOffsetT, len(tags))
					for j, t := range tags {
						tagOffs[j] = builder.CreateString(t)
					}
					fb.ItemStartTagsVector(builder, len(tags))
					for j := len(tagOffs) - 1; j >= 0; j-- {
						builder.PrependUOffsetT(tagOffs[j])
					}
					itemTagsOff = builder.EndVector(len(tags))
				}

				fb.ItemStart(builder)
				fb.ItemAddName(builder, nameOff)
				fb.ItemAddValue(builder, toFloat64(itemMap["value"]))
				if v, ok := itemMap["active"].(bool); ok {
					fb.ItemAddActive(builder, v)
				}
				fb.ItemAddDescription(builder, descOff)
				if itemTagsOff != 0 {
					fb.ItemAddTags(builder, itemTagsOff)
				}
				itemOffsets[i] = fb.ItemEnd(builder)
			}
		}
		fb.BenchmarkMessageStartItemsVector(builder, len(itemOffsets))
		for i := len(itemOffsets) - 1; i >= 0; i-- {
			builder.PrependUOffsetT(itemOffsets[i])
		}
		itemsOff = builder.EndVector(len(itemOffsets))
	}

	// Root BenchmarkMessage
	fb.BenchmarkMessageStart(builder)
	fb.BenchmarkMessageAddId(builder, toInt64(data["id"]))
	fb.BenchmarkMessageAddTimestamp(builder, timestampOff)
	fb.BenchmarkMessageAddUsername(builder, usernameOff)
	fb.BenchmarkMessageAddEmail(builder, emailOff)
	fb.BenchmarkMessageAddContent(builder, contentOff)
	if tagsOff != 0 {
		fb.BenchmarkMessageAddTags(builder, tagsOff)
	}
	if metadataOff != 0 {
		fb.BenchmarkMessageAddMetadata(builder, metadataOff)
	}
	fb.BenchmarkMessageAddScore(builder, toFloat64(data["score"]))
	if v, ok := data["is_active"].(bool); ok {
		fb.BenchmarkMessageAddIsActive(builder, v)
	}
	if nestedDataOff != 0 {
		fb.BenchmarkMessageAddNestedData(builder, nestedDataOff)
	}
	if itemsOff != 0 {
		fb.BenchmarkMessageAddItems(builder, itemsOff)
	}

	msg := fb.BenchmarkMessageEnd(builder)
	builder.Finish(msg)

	return builder.FinishedBytes(), nil
}

func (b *FlatBuffersBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	msg := fb.GetRootAsBenchmarkMessage(payload, 0)

	result := map[string]interface{}{
		"id":        msg.Id(),
		"timestamp": string(msg.Timestamp()),
		"username":  string(msg.Username()),
		"email":     string(msg.Email()),
		"content":   string(msg.Content()),
		"score":     msg.Score(),
		"is_active": msg.IsActive(),
	}

	// Tags
	tags := make([]string, msg.TagsLength())
	for i := 0; i < msg.TagsLength(); i++ {
		tags[i] = string(msg.Tags(i))
	}
	result["tags"] = tags

	// Metadata
	metadata := make(map[string]string)
	for i := 0; i < msg.MetadataLength(); i++ {
		kv := new(fb.KeyValue)
		if msg.Metadata(kv, i) {
			metadata[string(kv.Key())] = string(kv.Value())
		}
	}
	result["metadata"] = metadata

	// Nested data
	nd := new(fb.NestedData)
	if msg.NestedData(nd) != nil {
		vals := make([]float64, nd.ValuesLength())
		for i := 0; i < nd.ValuesLength(); i++ {
			vals[i] = nd.Values(i)
		}
		result["nested_data"] = map[string]interface{}{
			"field1": string(nd.Field1()),
			"field2": nd.Field2(),
			"values": vals,
		}
	}

	// Items
	items := make([]interface{}, msg.ItemsLength())
	for i := 0; i < msg.ItemsLength(); i++ {
		item := new(fb.Item)
		if msg.Items(item, i) {
			itemTags := make([]string, item.TagsLength())
			for j := 0; j < item.TagsLength(); j++ {
				itemTags[j] = string(item.Tags(j))
			}
			items[i] = map[string]interface{}{
				"name":        string(item.Name()),
				"value":       item.Value(),
				"active":      item.Active(),
				"description": string(item.Description()),
				"tags":        itemTags,
			}
		}
	}
	result["items"] = items

	return result, nil
}

func getStr(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

package benchmarks

import (
	"example.com/benchmarks/schemas/capnp"

	capnproto "zombiezen.com/go/capnproto2"
)

// CapnProtoBenchmark benchmarks Cap'n Proto, a zero-copy message format.
// Cap'n Proto is unique in that the wire format IS the in-memory format,
// making it extremely fast for read-intensive workloads.
type CapnProtoBenchmark struct{}

func (b *CapnProtoBenchmark) FormatName() string {
	return "Cap'n Proto"
}

func (b *CapnProtoBenchmark) Serialize(data map[string]interface{}) ([]byte, error) {
	msg, seg, err := capnproto.NewMessage(capnproto.SingleSegment(nil))
	if err != nil {
		return nil, err
	}

	bmsg, err := capnp.NewRootBenchmarkMessage(seg)
	if err != nil {
		return nil, err
	}

	if err := fillCapnpMessage(bmsg, data, seg); err != nil {
		return nil, err
	}

	return msg.Marshal()
}

func (b *CapnProtoBenchmark) Deserialize(payload []byte) (map[string]interface{}, error) {
	msg, err := capnproto.Unmarshal(payload)
	if err != nil {
		return nil, err
	}

	bmsg, err := capnp.ReadRootBenchmarkMessage(msg)
	if err != nil {
		return nil, err
	}

	return capnpToMap(bmsg)
}

func fillCapnpMessage(bmsg capnp.BenchmarkMessage, data map[string]interface{}, seg *capnproto.Segment) error {
	if v, ok := data["id"]; ok {
		bmsg.SetId(toInt64(v))
	}
	if v, ok := data["timestamp"].(string); ok {
		bmsg.SetTimestamp(v)
	}
	if v, ok := data["username"].(string); ok {
		bmsg.SetUsername(v)
	}
	if v, ok := data["email"].(string); ok {
		bmsg.SetEmail(v)
	}
	if v, ok := data["content"].(string); ok {
		bmsg.SetContent(v)
	}
	if v, ok := data["score"]; ok {
		bmsg.SetScore(toFloat64(v))
	}
	if v, ok := data["is_active"].(bool); ok {
		bmsg.SetIsActive(v)
	}

	// Tags
	if tags, ok := data["tags"].([]string); ok {
		tl, err := capnproto.NewTextList(seg, int32(len(tags)))
		if err != nil {
			return err
		}
		for i, t := range tags {
			tl.Set(i, t)
		}
		bmsg.SetTags(tl)
	}

	// Metadata
	if meta, ok := data["metadata"].(map[string]string); ok {
		kvList, err := capnp.NewKeyValue_List(seg, int32(len(meta)))
		if err != nil {
			return err
		}
		i := 0
		for k, v := range meta {
			kv := kvList.At(i)
			kv.SetKey(k)
			kv.SetValue(v)
			i++
		}
		bmsg.SetMetadata(kvList)
	}

	// Nested data
	if nd, ok := data["nested_data"].(map[string]interface{}); ok {
		nestedData, err := capnp.NewNestedData(seg)
		if err != nil {
			return err
		}
		if v, ok := nd["field1"].(string); ok {
			nestedData.SetField1(v)
		}
		if v, ok := nd["field2"]; ok {
			nestedData.SetField2(toInt64(v))
		}
		if vals, ok := nd["values"].([]float64); ok {
			vl, err := capnproto.NewFloat64List(seg, int32(len(vals)))
			if err != nil {
				return err
			}
			for i, v := range vals {
				vl.Set(i, v)
			}
			nestedData.SetValues(vl)
		}
		bmsg.SetNestedData(nestedData)
	}

	// Items
	if items, ok := data["items"].([]interface{}); ok {
		il, err := capnp.NewItem_List(seg, int32(len(items)))
		if err != nil {
			return err
		}
		for i, item := range items {
			if itemMap, ok := item.(map[string]interface{}); ok {
				it := il.At(i)
				if v, ok := itemMap["name"].(string); ok {
					it.SetName(v)
				}
				if v, ok := itemMap["value"]; ok {
					it.SetValue(toFloat64(v))
				}
				if v, ok := itemMap["active"].(bool); ok {
					it.SetActive(v)
				}
				if v, ok := itemMap["description"].(string); ok {
					it.SetDescription(v)
				}
				if tags, ok := itemMap["tags"].([]string); ok {
					tl, err := capnproto.NewTextList(seg, int32(len(tags)))
					if err != nil {
						return err
					}
					for j, t := range tags {
						tl.Set(j, t)
					}
					it.SetTags(tl)
				}
			}
		}
		bmsg.SetItems(il)
	}

	return nil
}

func capnpToMap(bmsg capnp.BenchmarkMessage) (map[string]interface{}, error) {
	result := map[string]interface{}{
		"id":        bmsg.Id(),
		"score":     bmsg.Score(),
		"is_active": bmsg.IsActive(),
	}

	if v, err := bmsg.Timestamp(); err == nil {
		result["timestamp"] = v
	}
	if v, err := bmsg.Username(); err == nil {
		result["username"] = v
	}
	if v, err := bmsg.Email(); err == nil {
		result["email"] = v
	}
	if v, err := bmsg.Content(); err == nil {
		result["content"] = v
	}

	// Tags
	if tl, err := bmsg.Tags(); err == nil {
		tags := make([]string, tl.Len())
		for i := 0; i < tl.Len(); i++ {
			t, _ := tl.At(i)
			tags[i] = t
		}
		result["tags"] = tags
	}

	// Metadata
	if kvl, err := bmsg.Metadata(); err == nil {
		meta := make(map[string]string, kvl.Len())
		for i := 0; i < kvl.Len(); i++ {
			kv := kvl.At(i)
			k, _ := kv.Key()
			v, _ := kv.Value()
			meta[k] = v
		}
		result["metadata"] = meta
	}

	// Nested data
	if nd, err := bmsg.NestedData(); err == nil {
		ndMap := map[string]interface{}{
			"field2": nd.Field2(),
		}
		if v, err := nd.Field1(); err == nil {
			ndMap["field1"] = v
		}
		if vl, err := nd.Values(); err == nil {
			vals := make([]float64, vl.Len())
			for i := 0; i < vl.Len(); i++ {
				vals[i] = vl.At(i)
			}
			ndMap["values"] = vals
		}
		result["nested_data"] = ndMap
	}

	// Items
	if il, err := bmsg.Items(); err == nil {
		items := make([]interface{}, il.Len())
		for i := 0; i < il.Len(); i++ {
			it := il.At(i)
			itemMap := map[string]interface{}{
				"value":  it.Value(),
				"active": it.Active(),
			}
			if v, err := it.Name(); err == nil {
				itemMap["name"] = v
			}
			if v, err := it.Description(); err == nil {
				itemMap["description"] = v
			}
			if tl, err := it.Tags(); err == nil {
				tags := make([]string, tl.Len())
				for j := 0; j < tl.Len(); j++ {
					t, _ := tl.At(j)
					tags[j] = t
				}
				itemMap["tags"] = tags
			}
			items[i] = itemMap
		}
		result["items"] = items
	}

	return result, nil
}

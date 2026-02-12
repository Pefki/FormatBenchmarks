using Go = import "/go.capnp";
@0xb8e5f7c2d4a3e1f6;
$Go.package("capnp");
$Go.import("example.com/benchmarks/schemas/capnp");

# Cap'n Proto schema for benchmark messages.
# The wire format is identical to the in-memory format (zero-copy).

struct BenchmarkMessage {
  id @0 :Int64;
  timestamp @1 :Text;
  username @2 :Text;
  email @3 :Text;
  content @4 :Text;
  tags @5 :List(Text);
  metadata @6 :List(KeyValue);
  score @7 :Float64;
  isActive @8 :Bool;
  nestedData @9 :NestedData;
  items @10 :List(Item);
}

struct KeyValue {
  key @0 :Text;
  value @1 :Text;
}

struct NestedData {
  field1 @0 :Text;
  field2 @1 :Int64;
  values @2 :List(Float64);
}

struct Item {
  name @0 :Text;
  value @1 :Float64;
  active @2 :Bool;
  description @3 :Text;
  tags @4 :List(Text);
}

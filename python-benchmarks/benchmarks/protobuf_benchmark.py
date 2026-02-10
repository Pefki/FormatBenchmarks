"""
Protocol Buffers Benchmark
===========================
Benchmark voor Google Protocol Buffers (Protobuf).
Vereist een gecompileerd .proto schema (message_pb2.py).

Protobuf is een schema-gebaseerd binary format met sterke typing
en compacte wire-format encoding.

Voer `python compile_schemas.py` uit als message_pb2.py niet bestaat.
"""

import sys
import os
import importlib

from .base_benchmark import BaseBenchmark

_SCHEMAS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "schemas")
)


def _get_message_module():
    """Probeer het gecompileerde protobuf module te importeren of compileren."""
    # Voeg schemas directory toe aan sys.path
    if _SCHEMAS_DIR not in sys.path:
        sys.path.insert(0, _SCHEMAS_DIR)

    # Probeer eerst direct te importeren
    try:
        return importlib.import_module("message_pb2")
    except ImportError:
        pass

    # Probeer automatisch te compileren met grpc_tools
    try:
        from grpc_tools import protoc

        proto_file = os.path.join(_SCHEMAS_DIR, "message.proto")
        result = protoc.main([
            "grpc_tools.protoc",
            f"--proto_path={_SCHEMAS_DIR}",
            f"--python_out={_SCHEMAS_DIR}",
            proto_file,
        ])
        if result == 0:
            print("  [Protobuf schema automatisch gecompileerd]")
            return importlib.import_module("message_pb2")
    except ImportError:
        pass

    raise ImportError(
        "Kon protobuf schema niet laden. "
        "Voer uit: python compile_schemas.py"
    )


class ProtobufBenchmark(BaseBenchmark):
    """Benchmark voor Protocol Buffers serialisatie/deserialisatie."""

    def __init__(self):
        self._pb2 = _get_message_module()
        self._message_class = self._pb2.BenchmarkMessage
        # Importeer json_format helpers
        from google.protobuf.json_format import ParseDict, MessageToDict
        self._parse_dict = ParseDict
        self._to_dict = MessageToDict

    @property
    def format_name(self) -> str:
        return "Protobuf"

    def _prepare_data(self, data: dict) -> dict:
        """Converteer dict naar protobuf-compatibel formaat."""
        prepared = dict(data)

        # nested_data: direct compatibel als dict
        # items: direct compatibel als list of dicts

        # Verwijder velden die niet in het proto schema zitten
        # (het schema heeft specifieke velden, onbekende velden worden genegeerd)
        return prepared

    def serialize(self, data: dict) -> bytes:
        """Serialiseer dict naar Protobuf binary."""
        prepared = self._prepare_data(data)
        msg = self._parse_dict(
            prepared,
            self._message_class(),
            ignore_unknown_fields=True,
        )
        return msg.SerializeToString()

    def deserialize(self, payload: bytes) -> dict:
        """Deserialiseer Protobuf binary naar dict."""
        msg = self._message_class()
        msg.ParseFromString(payload)
        try:
            # protobuf < 5.x
            return self._to_dict(
                msg,
                preserving_proto_field_name=True,
                including_default_value_fields=False,
            )
        except TypeError:
            # protobuf >= 6.x: parameter hernoemd
            return self._to_dict(
                msg,
                preserving_proto_field_name=True,
                always_print_fields_with_no_presence=False,
            )

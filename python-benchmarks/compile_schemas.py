#!/usr/bin/env python3
"""
Compileer schema bestanden voor Protobuf.
Voer dit script uit voordat je de Protobuf benchmark runt.

Gebruik:
    python compile_schemas.py
"""

import subprocess
import sys
import os

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")


def compile_protobuf():
    """Compileer het .proto bestand naar Python code."""
    proto_file = os.path.join(SCHEMAS_DIR, "message.proto")

    if not os.path.exists(proto_file):
        print(f"FOUT: {proto_file} niet gevonden")
        return False

    # Probeer grpc_tools eerst
    try:
        from grpc_tools import protoc

        result = protoc.main([
            "grpc_tools.protoc",
            f"--proto_path={SCHEMAS_DIR}",
            f"--python_out={SCHEMAS_DIR}",
            proto_file,
        ])
        if result == 0:
            print("✓ Protobuf schema gecompileerd (grpc_tools)")
            return True
        else:
            print(f"✗ grpc_tools compilatie mislukt (code {result})")
    except ImportError:
        print("  grpc_tools niet beschikbaar, probeer protoc...")

    # Probeer standalone protoc
    try:
        subprocess.run(
            [
                "protoc",
                f"--proto_path={SCHEMAS_DIR}",
                f"--python_out={SCHEMAS_DIR}",
                proto_file,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Protobuf schema gecompileerd (protoc)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"✗ protoc compilatie mislukt: {e}")
        return False


if __name__ == "__main__":
    print("Compileren van schema bestanden...")
    print("-" * 40)

    success = compile_protobuf()

    print("-" * 40)
    if success:
        print("Schema compilatie voltooid!")
    else:
        print("Schema compilatie mislukt!")
        print("Installeer grpc_tools: pip install grpcio-tools")
        print("Of installeer protoc: https://protobuf.dev/downloads/")

    sys.exit(0 if success else 1)

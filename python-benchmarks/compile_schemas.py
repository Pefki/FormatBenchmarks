#!/usr/bin/env python3
"""
Compile schema files for Protobuf.
Run this script before running the Protobuf benchmark.

Usage:
    python compile_schemas.py
"""

import subprocess
import sys
import os

SCHEMAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")


def compile_protobuf():
    """Compile the .proto file to Python code."""
    proto_file = os.path.join(SCHEMAS_DIR, "message.proto")

    if not os.path.exists(proto_file):
        print(f"ERROR: {proto_file} not found")
        return False

    # Try grpc_tools first
    try:
        from grpc_tools import protoc

        result = protoc.main([
            "grpc_tools.protoc",
            f"--proto_path={SCHEMAS_DIR}",
            f"--python_out={SCHEMAS_DIR}",
            proto_file,
        ])
        if result == 0:
            print("✓ Protobuf schema compiled (grpc_tools)")
            return True
        else:
            print(f"✗ grpc_tools compilation failed (code {result})")
    except ImportError:
        print("  grpc_tools not available, trying protoc...")

    # Try standalone protoc
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
        print("✓ Protobuf schema compiled (protoc)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"✗ protoc compilation failed: {e}")
        return False


if __name__ == "__main__":
    print("Compiling schema files...")
    print("-" * 40)

    success = compile_protobuf()

    print("-" * 40)
    if success:
        print("Schema compilation completed!")
    else:
        print("Schema compilation failed!")
        print("Install grpc_tools: pip install grpcio-tools")
        print("Or install protoc: https://protobuf.dev/downloads/")

    sys.exit(0 if success else 1)

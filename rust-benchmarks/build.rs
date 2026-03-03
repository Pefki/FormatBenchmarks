use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=schemas/message.capnp");
    println!("cargo:rerun-if-changed=schemas/message.fbs");

    export_rust_version();
    compile_capnp();
    compile_flatbuffers();
}

fn export_rust_version() {
    let version = Command::new("rustc")
        .arg("--version")
        .output()
        .ok()
        .filter(|output| output.status.success())
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| "unknown".to_string());

    println!("cargo:rustc-env=BENCHMARK_RUST_VERSION={version}");
}

fn compile_capnp() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR not set"));

    capnpc::CompilerCommand::new()
        .output_path(&out_dir)
        .src_prefix("schemas")
        .file("schemas/message.capnp")
        .run()
        .expect("failed to compile Cap'n Proto schema");
}

fn compile_flatbuffers() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR not set"));

    let status = Command::new("flatc")
        .args([
            "--rust",
            "--filename-suffix",
            "",
            "-o",
            out_dir
                .to_str()
                .expect("OUT_DIR contains invalid UTF-8"),
            "schemas/message.fbs",
        ])
        .status()
        .expect("failed to run flatc; install flatbuffers-compiler");

    if !status.success() {
        panic!("flatc failed while compiling schemas/message.fbs");
    }

    let generated_file = find_generated_flatbuffer_file(&out_dir)
        .expect("could not locate generated FlatBuffers Rust file in OUT_DIR");
    let target = out_dir.join("flatbuffers_generated.rs");

    if generated_file != target {
        fs::copy(&generated_file, &target)
            .expect("failed to copy generated FlatBuffers file to flatbuffers_generated.rs");
    }
}

fn find_generated_flatbuffer_file(out_dir: &Path) -> Option<PathBuf> {
    let direct = out_dir.join("message.rs");
    if direct.exists() {
        return Some(direct);
    }

    let entries = fs::read_dir(out_dir).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().is_some_and(|ext| ext == "rs") {
            let name = path.file_name()?.to_string_lossy();
            if name.contains("message") || name.contains("benchmark") {
                return Some(path);
            }
        }
    }

    None
}

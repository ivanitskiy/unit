use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {

    let out_dir_env = std::env::var("OUT_DIR").expect("The required environment variable OUT_DIR was not set");
    let out_path = std::path::PathBuf::from(out_dir_env);

    // Set the path to the libunit-wasm.o and unit-wasm.o files

    // TODO: build these .o files here and don't rely on make to compile these...
    // run those `make unit-wasm.o  && make libunit-wasm.o`. this build.rs doesn't deal with this now
    // for now just lazy step
    let libunit_wasm_path = "../../src/libunit-wasm.o";
    let unit_wasm_path = "../../src/unit-wasm.o";

    println!("cargo:rustc-link-search=native={}", libunit_wasm_path);
    println!("cargo:rustc-link-search=native={}", unit_wasm_path);


    // Tell cargo to invalidate the build.rs changes of
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-changed=wrapper.h");

    let bindings = bindgen::Builder::default()
        .allowlist_function("^luw_.*")
        .allowlist_var("^luw_.*")
        .allowlist_type("^luw_.*")
        .clang_arg(format!("-L{}", out_path.display()))
        .header("../../src/libunit-wasm.h")
        .layout_tests(false)
        .generate()
        .expect("Unable to generate bindings");
    // Write the bindings to the $OUT_DIR/bindings.rs file.

    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
    Ok(())
}

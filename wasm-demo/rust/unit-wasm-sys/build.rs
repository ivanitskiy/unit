use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {


    // println!("cargo:rustc-link-search=native=../../wasm-demo/src");
    // Tell cargo to look for shared libraries in the specified directory
    println!("cargo:rustc-link-search=../../wasm-demo/src");

    println!("cargo:rustc-link-search=native=../../src/");
    println!("cargo:rustc-link-lib=static=unit-wasm");

    // Tell cargo to invalidate the build.rs changes
    println!("cargo:rerun-if-changed=build.rs");

    // Tell cargo to invalidate the built crate whenever the wrapper changes
    println!("cargo:rerun-if-changed=wrapper.h");
    let bindings = bindgen::Builder::default()
        .allowlist_function("^luw_.*")
        .allowlist_var("^luw_.*")
        .allowlist_type("^luw_.*")
        .header("wrapper.h")
        .layout_tests(false)
        .generate()
        .expect("Unable to generate bindings");
    // Write the bindings to the $OUT_DIR/bindings.rs file.
    let out_dir_env =
        std::env::var("OUT_DIR").expect("The required environment variable OUT_DIR was not set");
    let out_path = std::path::PathBuf::from(out_dir_env);
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
    Ok(())
}

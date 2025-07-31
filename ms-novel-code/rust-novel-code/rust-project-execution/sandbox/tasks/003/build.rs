// build.rs  – generic stub, safe for every task

fn main() {

    // Re‑run only if these files change (keeps incremental builds quick)

    println!("cargo:rerun-if-changed=build.rs");

    println!("cargo:rerun-if-changed=Cargo.toml");



    // Emit a cfg flag that downstream code may (or may not) use

    println!("cargo:rustc-cfg=build_script_generated");

}



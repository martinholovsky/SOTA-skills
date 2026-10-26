fn main() {
    cc::Build::new().file("csrc/z.c").compile("z");
    let out = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());
    bindgen::Builder::default().header("csrc/z.h").generate().unwrap()
        .write_to_file(out.join("bindings.rs")).unwrap();
}

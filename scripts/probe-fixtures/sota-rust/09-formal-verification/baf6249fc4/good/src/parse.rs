#[cfg(kani)]
#[kani::proof]
fn parse_never_panics() {
    let b: [u8; 4] = kani::any();
    let _ = crate::parse(&b);
}

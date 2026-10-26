#[no_mangle]
pub extern "C" fn checksum(ptr: *const u8, len: usize) -> u32 {
    let s = unsafe { std::slice::from_raw_parts(ptr, len) };
    s.iter().map(|b| *b as u32).sum()
}

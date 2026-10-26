pub fn parse_frame(buf: &[u8]) -> &[u8] {
    let len = usize::from(buf[0]);
    assert!(len <= buf.len() - 1, "frame length exceeds buffer");
    &buf[1..=len]
}

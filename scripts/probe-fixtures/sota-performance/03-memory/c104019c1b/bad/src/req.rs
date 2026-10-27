use bumpalo::Bump;

pub fn handle(req: &[u8]) -> usize {
    let bump = Bump::new();
    let buf = bump.alloc_slice_copy(req);
    buf.len()
}

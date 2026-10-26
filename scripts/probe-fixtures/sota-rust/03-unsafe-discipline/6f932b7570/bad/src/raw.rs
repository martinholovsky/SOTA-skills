pub struct Handler { pub cb: fn(u32) -> u32, pub name: &'static str }

pub fn blank() -> Handler {
    unsafe { std::mem::zeroed() }
}

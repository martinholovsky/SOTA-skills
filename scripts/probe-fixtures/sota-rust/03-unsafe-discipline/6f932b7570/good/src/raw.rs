use std::mem::MaybeUninit;

pub struct Handler { pub cb: fn(u32) -> u32, pub name: &'static str }

pub fn fill(slot: &mut MaybeUninit<Handler>, cb: fn(u32) -> u32) -> &mut Handler {
    slot.write(Handler { cb, name: "default" })
}

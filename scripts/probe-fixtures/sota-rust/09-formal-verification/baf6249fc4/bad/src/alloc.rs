#[cfg(kani)]
#[kani::requires(kani::mem::can_dereference(p))]
#[kani::modifies(p)]
unsafe fn bump(p: *mut u32) {
    *p += 1;
}

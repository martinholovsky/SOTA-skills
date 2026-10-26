use std::os::raw::c_int;

#[repr(C)]
pub struct Widget { _private: [u8; 0] }

extern "C" {
    pub fn widget_is_ready(w: *const Widget) -> u8;
    pub fn widget_count() -> c_int;
}

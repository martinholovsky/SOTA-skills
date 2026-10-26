use std::os::raw::{c_char, c_void};

extern "C" {
    pub fn db_open(path: *const c_char) -> *mut c_void;
    pub fn db_close(db: *mut c_void);
}

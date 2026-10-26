use std::marker::{PhantomData, PhantomPinned};
use std::os::raw::c_char;

#[repr(C)]
pub struct Db { _data: (), _marker: PhantomData<(*mut u8, PhantomPinned)> }

extern "C" {
    pub fn db_open(path: *const c_char) -> *mut Db;
    pub fn db_close(db: *mut Db);
}

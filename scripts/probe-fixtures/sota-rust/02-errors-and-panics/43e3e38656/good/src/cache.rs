use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};

pub struct Cache { inner: Mutex<HashMap<String, String>> }

impl Cache {
    pub fn get(&self, k: &str) -> Option<String> {
        // Poison policy: the map has no cross-entry invariant, so recover.
        self.inner.lock().unwrap_or_else(PoisonError::into_inner).get(k).cloned()
    }
}

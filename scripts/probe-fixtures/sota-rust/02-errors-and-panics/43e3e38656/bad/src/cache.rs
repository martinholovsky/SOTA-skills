use std::collections::HashMap;
use std::sync::Mutex;

pub struct Cache { inner: Mutex<HashMap<String, String>> }

impl Cache {
    pub fn get(&self, k: &str) -> Option<String> {
        self.inner.lock().unwrap().get(k).cloned()
    }
}

pub struct ServerBuilder { addr: Option<String>, workers: usize }

impl ServerBuilder {
    pub fn addr(mut self, a: impl Into<String>) -> Self { self.addr = Some(a.into()); self }
    pub fn build(self) -> Server {
        Server { addr: self.addr.expect("addr is required"), workers: self.workers }
    }
}

pub struct Server { addr: String, workers: usize }

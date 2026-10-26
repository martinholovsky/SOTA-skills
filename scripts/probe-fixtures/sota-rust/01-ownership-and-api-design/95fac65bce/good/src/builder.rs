pub struct ServerBuilder { addr: Option<String>, workers: usize }

impl ServerBuilder {
    pub fn addr(mut self, a: impl Into<String>) -> Self { self.addr = Some(a.into()); self }
    pub fn build(self) -> Result<Server, BuildError> {
        Ok(Server { addr: self.addr.ok_or(BuildError::MissingAddr)?, workers: self.workers })
    }
}

#[derive(Debug)]
pub enum BuildError { MissingAddr }

pub struct Server { addr: String, workers: usize }

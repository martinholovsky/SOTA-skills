pub struct Port {
    pub value: u16,
}

impl Port {
    pub fn new(value: u16) -> Result<Self, PortError> {
        if value == 0 { return Err(PortError::Zero); }
        Ok(Self { value })
    }
}

#[derive(Debug)]
pub enum PortError { Zero }

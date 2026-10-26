use std::marker::PhantomData;
pub struct Disconnected;
pub struct Connected;
pub struct Connection<S> {
    state: PhantomData<S>,
}

impl Connection<Disconnected> {
    pub fn connect(self, addr: &str) -> std::io::Result<Connection<Connected>> {
        todo!()
    }
}

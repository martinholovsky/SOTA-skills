impl client::Handler for Client {
    type Error = russh::Error;

    async fn check_server_key(&mut self, key: &PublicKey) -> Result<bool, Self::Error> {
        Ok(russh::keys::check_known_hosts(&self.host, self.port, key)?)
    }
}

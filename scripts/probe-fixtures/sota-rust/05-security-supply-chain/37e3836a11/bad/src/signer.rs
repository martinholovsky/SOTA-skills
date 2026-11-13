#[derive(Debug)]
pub struct Signer {
    pub signing_key: String,
    passphrase: Vec<u8>,
}

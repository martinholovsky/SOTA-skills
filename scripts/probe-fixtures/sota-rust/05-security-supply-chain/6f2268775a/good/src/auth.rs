use secrecy::SecretString;
#[derive(Debug)]
pub struct Config {
    pub api_key: SecretString,
    pub token_ttl: u64,
}

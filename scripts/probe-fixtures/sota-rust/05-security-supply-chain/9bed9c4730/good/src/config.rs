use secrecy::SecretString;
#[derive(Debug, Clone)]
pub struct DbConfig {
    pub url: String,
    pub password: SecretString,
}
